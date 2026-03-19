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
