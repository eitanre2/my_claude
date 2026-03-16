---
name: telegram
description: Send and receive messages via Telegram Bot API. Use when user asks to "send a Telegram message", "read Telegram messages", "check Telegram", or mentions Telegram, bot token, or chat ID.
---

# Telegram Messages

Send and receive messages using the Telegram Bot API. Credentials are read from `~/.claude/credentials.json`; never hardcode the bot token.

## Credentials

Store the bot token and named chats in `~/.claude/credentials.json` under a `telegram` key:

```json
"telegram": {
  "bot_token": "YOUR_BOT_TOKEN_FROM_BOTFATHER",
  "default_chat": "eitan",
  "chats": {
    "eitan": "1617172755",
    "news": "CHAT_ID_HERE"
  }
}
```

- **bot_token** (required): From BotFather.
- **default_chat** (optional): Name of the chat (from `chats`) to use when the user doesn't specify a recipient.
- **chats** (required): Map of friendly names to Telegram chat IDs. The agent resolves names to IDs at send time.

If the file or `bot_token` is missing, tell the user to add their token and retry.

## Usage

Run the script from this skill folder (or set `CLAUDE_DIR=~/.claude`):

- **Send:** `scripts/telegram.sh send <chat_id> "message"`.
- **Receive:** `scripts/telegram.sh receive` (fetches recent updates via getUpdates)
- **Receive (long poll):** `scripts/telegram.sh receive --wait [timeout_seconds]` (default 30)

**Chat resolution:** Read `telegram.chats` from `credentials.json` to resolve friendly names to chat IDs. If the user says "send to news", look up `chats.news`. If no recipient is specified, use `chats[default_chat]`. For a private chat, the user must start a conversation with the bot first; then use getUpdates once to see their `chat.id`. For a group, add the bot and use the group's numeric ID (often negative).

## Instructions

1. **Resolve chat:** Read `~/.claude/credentials.json`. Parse `telegram.chats` to get the name-to-ID map and `telegram.default_chat` for the fallback.
   - If the user specifies a chat name (e.g. "send to news"), look up `chats["news"]` to get the numeric chat ID.
   - If the user specifies a raw numeric chat ID, use it directly.
   - If no recipient is given, use `chats[default_chat]`.
   - If the name isn't found in `chats`, tell the user and list the available chat names.
2. **Send message:** Run `scripts/telegram.sh send <resolved_chat_id> "text"`. On success, output the script's success line; on failure, show the error.
3. **Receive messages:** Run `scripts/telegram.sh receive` and show the script output (list of recent messages). With `--wait`, run `scripts/telegram.sh receive --wait [seconds]` and show incoming messages until timeout.
4. **Discover chat_id:** If the user doesn't know their chat_id, run `scripts/telegram.sh receive` once after they message the bot; parse and show the `chat.id` from the updates. Offer to add it to `credentials.json` under `chats`.
5. Never log, echo, or store the bot token; read it only from `~/.claude/credentials.json`.

## API reference

- Send: `POST https://api.telegram.org/bot<token>/sendMessage` with `chat_id`, `text`.
- Receive: `GET https://api.telegram.org/bot<token>/getUpdates` (optional: `offset`, `timeout` for long polling). Messages are in `result[].message.text` and `result[].message.chat.id`.

For full API details, see [references/reference.md](references/reference.md).

## Security

- Do not commit `credentials.json`. Add `~/.claude/credentials.json` to `.gitignore` if the repo is ever shared. Rotate the token if exposed.
