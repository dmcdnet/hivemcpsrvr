# Hive MCP Server

An MCP server wrapping [pyhive-integration](https://pypi.org/project/pyhive-integration/) to control Hive smart home devices via Claude or any MCP client.

## Supported devices

| Device | Tools |
|--------|-------|
| Lights | get state, turn on/off, set brightness, colour temp, RGB colour |
| Heating | get state, set temperature, set mode, boost on/off, get schedule |
| Hot Water | get state, set mode, boost on/off, get schedule |
| Smart Plugs | get state/power, turn on/off |
| Sensors | get state, hub online check |
| Alarm (Home Shield) | get state/mode, set mode |
| Session | login, SMS 2FA, device login, list devices, refresh tokens |

## Setup

```bash
uv venv
uv pip install -e .
```

## Running

```bash
.venv/bin/hivemcpsrvr
```

## Claude Desktop configuration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hive": {
      "command": "/home/dm/wrksp/hivemcpsrvr/.venv/bin/hivemcpsrvr"
    }
  }
}
```

## Usage flow

1. `hive_login` — authenticate with your Hive email and password
2. `hive_sms_2fa` — (if prompted) enter the SMS code
3. `hive_start_session` — load all devices
4. `hive_list_devices` — see device names/IDs
5. Use any device tool with the device name or ID

> **Note:** Only the Hive owner account is supported — guest accounts are not.

## Running headless / in Docker

Hive requires SMS 2FA on interactive username/password logins, which is
impractical for an unattended container. Instead, use **device credentials**:
authenticate once interactively, register this client as a trusted device, then
reuse the resulting credentials to log in automatically with no 2FA.

### 1. One-time bootstrap (obtain device credentials)

Run the server locally over stdio and, via your MCP client, call:

1. `hive_login` with your email + password
2. `hive_sms_2fa` with the SMS code
3. `hive_register_device` — returns `HIVE_DEVICE_GROUP_KEY`,
   `HIVE_DEVICE_KEY` and `HIVE_DEVICE_PASSWORD`

Copy those three values into a `.env` file (see `.env.example`). Keep them
secret — they grant access to your Hive account.

### 2. Run the container

Credentials are injected at runtime via environment variables (never baked into
the image). On startup the server reads `HIVE_DEVICE_*`, logs in automatically,
and loads devices — no tool calls needed.

```bash
docker build -t hivemcpsrvr .
docker run --env-file .env -p 8000:8000 hivemcpsrvr
```

Or with Docker Compose (reads `.env` automatically):

```bash
cp .env.example .env   # then fill in the HIVE_DEVICE_* values
docker compose up --build
```

The container listens on SSE at `http://<host>:8000/sse` by default
(`HIVE_TRANSPORT`, `HIVE_HOST`, `HIVE_PORT` are configurable).

> **Security:** prefer `--env-file`, Docker/Swarm secrets, or your
> orchestrator's secret store over inline `-e` flags, and never commit `.env`
> (it is git-ignored).
