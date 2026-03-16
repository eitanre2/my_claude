# Telegram Bot API (reference)

- **Base URL:** `https://api.telegram.org/bot<token>/`
- **Token:** From BotFather; stored in `~/.claude/credentials.json` under `telegram.bot_token`.

## sendMessage

`POST sendMessage`

| Param    | Type   | Required | Description   |
|----------|--------|----------|---------------|
| chat_id  | int/str| Yes      | Chat or user ID |
| text     | string | Yes      | Message text  |
| parse_mode | string | No     | `HTML` or `Markdown` |

Response: `{ "ok": true, "result": { "message_id": ... } }` or `{ "ok": false, "description": "..." }`.

## getUpdates

`GET getUpdates`

| Param   | Type | Description |
|---------|------|-------------|
| offset  | int  | Next update_id to skip already-seen updates |
| timeout | int  | Long-poll seconds (1–50) |

Response: `{ "ok": true, "result": [ { "update_id": N, "message": { "message_id", "chat": { "id" }, "from": { "username", "first_name" }, "date", "text" } } ] }`.

- To acknowledge updates and avoid repeats, call getUpdates again with `offset = last update_id + 1`.
- For channel posts, the update may have `channel_post` instead of `message`.

## Getting chat_id

1. User starts a chat with the bot (e.g. /start).
2. Call getUpdates; in `result[].message.chat.id` you get the user’s chat_id. Use that for sendMessage.
