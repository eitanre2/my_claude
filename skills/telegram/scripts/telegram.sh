#!/bin/bash
# Telegram Bot API – send and receive messages
# Credentials: ~/.claude/credentials.json → .telegram.bot_token, .telegram.chats, .telegram.default_chat
# Usage:
#   telegram.sh send [chat_id_or_name] "message"
#   telegram.sh receive [--wait [timeout_seconds]]

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
CREDS_FILE="$CLAUDE_DIR/credentials.json"
STATE_FILE="$CLAUDE_DIR/telegram_offset.state"

get_token() {
    if [ ! -f "$CREDS_FILE" ]; then
        echo "✗ Missing credentials file: $CREDS_FILE" >&2
        exit 1
    fi
    TOKEN=$(jq -r '.telegram.bot_token // empty' "$CREDS_FILE")
    if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
        echo "✗ No telegram.bot_token in $CREDS_FILE" >&2
        exit 1
    fi
    echo "$TOKEN"
}

resolve_chat_id() {
    local name_or_id="${1:-}"
    if [ ! -f "$CREDS_FILE" ]; then
        echo "" && return
    fi
    if [ -z "$name_or_id" ]; then
        # No argument — use default_chat name, then look it up in chats
        name_or_id=$(jq -r '.telegram.default_chat // empty' "$CREDS_FILE")
        if [ -z "$name_or_id" ]; then
            # Legacy fallback: bare chat_id field
            jq -r '.telegram.chat_id // empty' "$CREDS_FILE"
            return
        fi
    fi
    # If it looks numeric (with optional leading -), treat as a raw chat ID
    if [[ "$name_or_id" =~ ^-?[0-9]+$ ]]; then
        echo "$name_or_id"
        return
    fi
    # Otherwise resolve the name from the chats map
    local resolved
    resolved=$(jq -r --arg n "$name_or_id" '.telegram.chats[$n] // empty' "$CREDS_FILE")
    if [ -n "$resolved" ]; then
        echo "$resolved"
    else
        local available
        available=$(jq -r '.telegram.chats | keys | join(", ")' "$CREDS_FILE" 2>/dev/null)
        echo "✗ Unknown chat name \"$name_or_id\". Available: $available" >&2
        exit 1
    fi
}

send_message() {
    local token
    token=$(get_token) || exit 1
    local chat_id
    local text
    if [ $# -eq 1 ]; then
        chat_id=$(resolve_chat_id)
        if [ -z "$chat_id" ] || [ "$chat_id" = "null" ]; then
            echo "✗ No default chat configured and none given. Set telegram.default_chat and telegram.chats in $CREDS_FILE, or use: send <name_or_id> \"message\"" >&2
            exit 1
        fi
        text="$1"
    elif [ $# -ge 2 ]; then
        chat_id=$(resolve_chat_id "$1")
        text="$2"
    else
        echo "Usage: telegram.sh send [chat_name_or_id] \"message\"" >&2
        exit 1
    fi
    RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${token}/sendMessage" \
        --data-urlencode "chat_id=$chat_id" \
        --data-urlencode "text=$text")
    OK=$(echo "$RESPONSE" | jq -r '.ok')
    if [ "$OK" = "true" ]; then
        echo "✓ Sent to chat $chat_id: \"$text\""
    else
        DESC=$(echo "$RESPONSE" | jq -r '.description // "unknown error"')
        echo "✗ Failed: $DESC" >&2
        exit 1
    fi
}

receive_messages() {
    local token
    token=$(get_token) || exit 1

    # Read offset from state file, or start from 0
    local offset=0
    if [ -f "$STATE_FILE" ]; then
        offset=$(cat "$STATE_FILE" 2>/dev/null || echo "0")
    fi

    local wait_timeout=0
    if [ "${1:-}" = "--wait" ]; then
        shift
        wait_timeout="${1:-30}"
        shift
    fi

    local url="https://api.telegram.org/bot${token}/getUpdates?offset=$offset"
    if [ -n "$wait_timeout" ] && [ "$wait_timeout" -gt 0 ]; then
        url="${url}&timeout=${wait_timeout}"
    fi

    RESPONSE=$(curl -s "$url")
    OK=$(echo "$RESPONSE" | jq -r '.ok')
    if [ "$OK" != "true" ]; then
        DESC=$(echo "$RESPONSE" | jq -r '.description // "unknown error"')
        echo "✗ getUpdates failed: $DESC" >&2
        exit 1
    fi

    # Output new messages only
    echo "$RESPONSE" | jq -r '
        .result[] |
        .message // .channel_post // empty |
        select(.text != null) |
        "\(.chat.id)|\(.date)|\(.from.username // .from.first_name // "?")|\(.message_id)|\(.text)"
    ' | while IFS='|' read -r chat_id date from mid text; do
        [ -z "$chat_id" ] && continue
        echo "[$date] chat_id=$chat_id from=$from (message_id=$mid)"
        echo "$text"
        echo "---"
    done

    # Update offset for next call (last_update_id + 1 acknowledges all messages)
    LAST_UPDATE=$(echo "$RESPONSE" | jq -r '.result[-1].update_id // empty')
    if [ -n "$LAST_UPDATE" ]; then
        NEW_OFFSET=$((LAST_UPDATE + 1))
        echo "$NEW_OFFSET" > "$STATE_FILE"
    fi
}

case "${1:-}" in
    send)
        shift
        send_message "$@"
        ;;
    receive)
        shift
        receive_messages "$@"
        ;;
    *)
        echo "Usage: telegram.sh {send|receive} [args]" >&2
        echo "  send [chat_name_or_id] \"message\"" >&2
        echo "  receive [--wait [timeout_seconds]]" >&2
        exit 1
        ;;
esac
