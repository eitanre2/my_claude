---
name: twilio
description: Send or receive SMS and WhatsApp messages via Twilio API. Use when user asks to "send a text", "send SMS", "send WhatsApp message", "check messages", or mentions Twilio, SMS, or WhatsApp messaging.
---

## Usage

```
/twilio <mode> [options]
```

**Modes**

- **send** – Send a message (optional `--wait` to wait for reply)
- **receive** – Fetch and show last inbound messages (no extra args)

## Arguments

- `mode` (required): `send` or `receive`
- For **send** mode:
  - `phone_number` (optional): Recipient. **Default: `whatsapp:+972545607831`**
    - SMS: e.g. `+972545607831`
    - WhatsApp: e.g. `whatsapp:+972545607831`
  - `message` (required): Text to send (in quotes)
  - `--wait` (optional): After sending, wait for a reply and show it
- For **receive** mode: no further arguments

## Examples

```bash
# Receive: show last inbound messages
/twilio-send receive

# Send only
/twilio-send send "Hello, this is a test message"
/twilio-send send "Should I fix the specs?" --wait
/twilio-send send +972545607831 "Hello via SMS"
/twilio-send send whatsapp:+972545607831 "Hello via WhatsApp"

# Backward compatible (message only = send to default)
/twilio-send "Hello, this is a test message"
/twilio-send "Reply when ready" --wait
```

## Instructions

Execute immediately; do not prompt for input.

1. **Parse arguments**
   - First arg is `receive` → receive mode. Run `twilio.sh receive` and show output. Exit.
   - First arg is `send`:
     - One more arg (no --wait) → message only, default WhatsApp
     - One more arg + `--wait` → message, default WhatsApp, then wait for response
     - Two more args (no --wait) → phone, message
     - Two more args + `--wait` → phone, message, then wait for response
   - **Backward compatibility:** If first arg is not `send` or `receive` (e.g. a quoted message), treat as send: that arg is the message, default phone; optional `--wait` as last arg.
   - No arguments → show brief usage and exit.

2. **Run the script** (script lives in this skill folder)
   - **Receive:** `twilio.sh receive`
   - **Send:** `twilio.sh send [phone] "message"`
   - **Send + wait:**
     1. `twilio.sh send [phone] "message"`
     2. `timestamp=$(date -u +"%a, %d %b %Y %H:%M:%S +0000")`
     3. `twilio.sh wait-response [phone] "$timestamp"`

3. **Wait-for-response behavior**
   - Polls every 10s for 2 minutes, then every 60s up to 1 hour
   - Returns the newest message after the timestamp
   - On timeout: “No response received after 1 hour”

4. **Output**
   - Send success: `✓ Sent to <phone>: "<message>" (SID: <sid>)`
   - Error: `✗ Failed: <error_message> (code: <error_code>)`
   - Response: `📨 Response from <phone>: "<response>"`
   - Timeout: `⏱️ No response received after 1 hour`
   - Receive: use script output as-is (inbound messages list)
   - Keep output short; no extra explanation unless something fails.

## Implementation details (send + wait)

```bash
twilio.sh send "whatsapp:+972545607831" "Your message here"
timestamp=$(date -u +"%a, %d %b %Y %H:%M:%S +0000")
twilio.sh wait-response "whatsapp:+972545607831" "$timestamp"
```

## Notes

- Run immediately; never ask “What would you like to send?” or confirm.
- Missing required args → show usage and exit.
- Uses `twilio.sh`; credentials in `.claude/credentials.json` (do not hardcode).
- WhatsApp: both To and From must use `whatsapp:` prefix.

## Security

- Do not commit credentials. Add `.claude/credentials.json` to `.gitignore`. Rotate if exposed.
