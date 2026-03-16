#!/bin/bash

# Twilio API wrapper script
# Usage:
#   twilio.sh send [phone] "message"
#   twilio.sh send-media [phone] "media_url" "caption"
#   twilio.sh receive

# Auto-detect project root by finding .claude directory
find_project_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.claude" ]; then
            echo "$dir/.claude"
            return 0
        fi
        dir=$(dirname "$dir")
    done
    echo ".claude"  # Fallback to relative path
}

CLAUDE_DIR="${CLAUDE_DIR:-$(find_project_root)}"
CREDS_FILE="$CLAUDE_DIR/credentials.json"

load_credentials() {
    ACCOUNT_SID=$(jq -r '.twilio.accountSid' "$CREDS_FILE")
    AUTH_TOKEN=$(jq -r '.twilio.authToken' "$CREDS_FILE")
    DEFAULT_PHONE=$(jq -r '.twilio.defaultPhone' "$CREDS_FILE")
    SMS_FROM=$(jq -r '.twilio.smsFrom' "$CREDS_FILE")
    WHATSAPP_FROM=$(jq -r '.twilio.whatsappFrom' "$CREDS_FILE")
}

send_message() {
    load_credentials

    # Parse arguments
    if [ $# -eq 1 ]; then
        TO="$DEFAULT_PHONE"
        BODY="$1"
    elif [ $# -eq 2 ]; then
        TO="$1"
        BODY="$2"
    else
        echo "Usage: twilio.sh send [phone] \"message\""
        exit 1
    fi

    # Determine message type
    if [[ "$TO" == whatsapp:* ]]; then
        FROM="$WHATSAPP_FROM"
    else
        FROM="$SMS_FROM"
    fi

    # Send message
    RESPONSE=$(curl -s "https://api.twilio.com/2010-04-01/Accounts/$ACCOUNT_SID/Messages.json" -X POST \
        -u "$ACCOUNT_SID:$AUTH_TOKEN" \
        --data-urlencode "To=$TO" \
        --data-urlencode "From=$FROM" \
        --data-urlencode "Body=$BODY")

    # Parse response
    ERROR=$(echo "$RESPONSE" | jq -r '.error_message // empty')
    if [ -n "$ERROR" ]; then
        CODE=$(echo "$RESPONSE" | jq -r '.code // "unknown"')
        echo "✗ Failed: $ERROR (code: $CODE)"
        exit 1
    else
        SID=$(echo "$RESPONSE" | jq -r '.sid')
        echo "✓ Sent to $TO: \"$BODY\" (SID: $SID)"
    fi
}

send_media() {
    load_credentials

    # Parse arguments
    if [ $# -eq 2 ]; then
        TO="$DEFAULT_PHONE"
        MEDIA_URL="$1"
        CAPTION="$2"
    elif [ $# -eq 3 ]; then
        TO="$1"
        MEDIA_URL="$2"
        CAPTION="$3"
    else
        echo "Usage: twilio.sh send-media [phone] \"media_url\" \"caption\""
        exit 1
    fi

    # Determine message type
    if [[ "$TO" == whatsapp:* ]]; then
        FROM="$WHATSAPP_FROM"
    else
        FROM="$SMS_FROM"
    fi

    # Send message with media
    RESPONSE=$(curl -s "https://api.twilio.com/2010-04-01/Accounts/$ACCOUNT_SID/Messages.json" -X POST \
        -u "$ACCOUNT_SID:$AUTH_TOKEN" \
        --data-urlencode "To=$TO" \
        --data-urlencode "From=$FROM" \
        --data-urlencode "Body=$CAPTION" \
        --data-urlencode "MediaUrl=$MEDIA_URL")

    # Parse response
    ERROR=$(echo "$RESPONSE" | jq -r '.error_message // empty')
    if [ -n "$ERROR" ]; then
        CODE=$(echo "$RESPONSE" | jq -r '.code // "unknown"')
        echo "✗ Failed: $ERROR (code: $CODE)"
        exit 1
    else
        SID=$(echo "$RESPONSE" | jq -r '.sid')
        echo "✓ Sent media to $TO: \"$CAPTION\" (SID: $SID)"
    fi
}

receive_messages() {
    load_credentials

    # Fetch messages
    RESPONSE=$(curl -s "https://api.twilio.com/2010-04-01/Accounts/$ACCOUNT_SID/Messages.json" \
        -u "$ACCOUNT_SID:$AUTH_TOKEN")

    # Filter and display inbound messages
    MESSAGES=$(echo "$RESPONSE" | jq -r '.messages[] | select(.direction == "inbound" and .status == "received") | "\(.date_created)|\(.from)|\(.body)|\(.sid)"')

    if [ -z "$MESSAGES" ]; then
        echo "No new incoming messages found."
        exit 0
    fi

    echo "📨 Incoming Messages"
    echo "=================="
    echo ""

    echo "$MESSAGES" | while IFS='|' read -r date from body sid; do
        # Determine type
        if [[ "$from" == whatsapp:* ]]; then
            TYPE="WhatsApp"
        else
            TYPE="SMS"
        fi

        echo "[$date] $TYPE from $from"
        echo "Message: $body"
        echo "SID: $sid"
        echo ""
    done
}

wait_for_response() {
    load_credentials

    # Parse arguments
    if [ $# -eq 1 ]; then
        FROM_NUMBER="$DEFAULT_PHONE"
        AFTER_TIME="$1"
    elif [ $# -eq 2 ]; then
        FROM_NUMBER="$1"
        AFTER_TIME="$2"
    else
        echo "Usage: twilio.sh wait-response [from_number] after_timestamp"
        exit 1
    fi

    local max_wait=3600  # 1 hour
    local start_time=$(date +%s)
    local elapsed=0

    # First 2 minutes: check every 10 seconds
    while [ $elapsed -lt 120 ]; do
        RESPONSE=$(curl -s "https://api.twilio.com/2010-04-01/Accounts/$ACCOUNT_SID/Messages.json" \
            -u "$ACCOUNT_SID:$AUTH_TOKEN")

        # Find most recent message from the specified number after the timestamp
        # API may return newest-first; we explicitly take newest by sorting desc then first
        MESSAGE=$(echo "$RESPONSE" | jq -r --arg from "$FROM_NUMBER" --arg after "$AFTER_TIME" \
            '[.messages[] | select(.direction == "inbound" and .from == $from and .date_created > $after)] | sort_by(.date_created) | reverse | .[0] | .body')

        if [ -n "$MESSAGE" ]; then
            echo "📨 Response from $FROM_NUMBER: \"$MESSAGE\""
            exit 0
        fi

        sleep 10
        elapsed=$(($(date +%s) - start_time))
    done

    # After 2 minutes: check every 60 seconds
    while [ $elapsed -lt $max_wait ]; do
        RESPONSE=$(curl -s "https://api.twilio.com/2010-04-01/Accounts/$ACCOUNT_SID/Messages.json" \
            -u "$ACCOUNT_SID:$AUTH_TOKEN")

        MESSAGE=$(echo "$RESPONSE" | jq -r --arg from "$FROM_NUMBER" --arg after "$AFTER_TIME" \
            '[.messages[] | select(.direction == "inbound" and .from == $from and .date_created > $after)] | sort_by(.date_created) | reverse | .[0] | .body')

        if [ -n "$MESSAGE" ]; then
            echo "📨 Response from $FROM_NUMBER: \"$MESSAGE\""
            exit 0
        fi

        sleep 60
        elapsed=$(($(date +%s) - start_time))
    done

    echo "⏱️ No response received after 1 hour"
    exit 1
}

# Main
case "${1:-}" in
    send)
        shift
        send_message "$@"
        ;;
    send-media)
        shift
        send_media "$@"
        ;;
    receive)
        receive_messages
        ;;
    wait-response)
        shift
        wait_for_response "$@"
        ;;
    *)
        echo "Usage: twilio.sh {send|send-media|receive|wait-response} [args]"
        exit 1
        ;;
esac
