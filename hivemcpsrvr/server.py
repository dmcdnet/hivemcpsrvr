"""MCP server wrapping the pyhive-integration library for Hive smart home control."""

import asyncio
import json
import logging
from typing import Any

import aiohttp
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("Hive Smart Home")

# Global session state
_hive = None
_session = None
_devices: dict[str, list[dict]] = {}


def _get_hive():
    """Return the current Hive instance, raising if not initialised."""
    if _hive is None:
        raise RuntimeError(
            "Not logged in. Call hive_login (or hive_device_login) then hive_start_session first."
        )
    return _hive


def _find_device(device_type: str, name_or_id: str) -> dict:
    """Find a device by name or ID within a device type list."""
    devices = _devices.get(device_type, [])
    needle = name_or_id.lower()
    for dev in devices:
        if (
            dev.get("hiveID", "").lower() == needle
            or dev.get("hiveName", "").lower() == needle
            or dev.get("friendlyName", "").lower() == needle
        ):
            return dev
    available = [d.get("hiveName") or d.get("hiveID", "?") for d in devices]
    raise ValueError(
        f"Device '{name_or_id}' not found in {device_type}. "
        f"Available: {available}"
    )


# ---------------------------------------------------------------------------
# Authentication & session
# ---------------------------------------------------------------------------


@mcp.tool()
async def hive_login(username: str, password: str) -> str:
    """
    Log in to Hive with username and password.

    Returns a result dict. If 2FA is required the result will indicate
    this – call hive_sms_2fa with the code and the returned session object.
    After a successful login call hive_start_session to load devices.
    """
    global _hive, _session

    from pyhiveapi import Hive

    _session = aiohttp.ClientSession()
    _hive = Hive(websession=_session, username=username, password=password)
    result = await _hive.login()
    return json.dumps(result)


@mcp.tool()
async def hive_sms_2fa(code: str, session: str) -> str:
    """
    Complete a login that requires SMS two-factor authentication.

    Pass the SMS code and the session string returned by hive_login.
    On success call hive_start_session.
    """
    h = _get_hive()
    session_obj = json.loads(session)
    result = await h.sms2fa(code, session_obj)
    return json.dumps(result)


@mcp.tool()
async def hive_device_login(
    device_group_key: str, device_key: str, device_password: str
) -> str:
    """
    Log in using device credentials instead of username/password.

    After a successful login call hive_start_session.
    """
    global _hive, _session

    from pyhiveapi import Hive

    _session = aiohttp.ClientSession()
    _hive = Hive(websession=_session)
    _hive.auth.device_group_key = device_group_key
    _hive.auth.device_key = device_key
    _hive.auth.device_password = device_password
    result = await _hive.deviceLogin()
    return json.dumps(result)


@mcp.tool()
async def hive_start_session(config: str = "{}") -> str:
    """
    Initialise the Hive session and load all devices.

    Optionally pass a JSON config dict (e.g. with stored tokens).
    Returns the full device list grouped by type.
    """
    global _devices

    h = _get_hive()
    cfg = json.loads(config) if config else {}
    raw_devices = await h.startSession(cfg if cfg else None)

    # Organise devices by type for easier lookup
    _devices = {}
    if isinstance(raw_devices, list):
        for dev in raw_devices:
            dtype = dev.get("deviceType", "unknown")
            _devices.setdefault(dtype, []).append(dev)
    elif isinstance(raw_devices, dict):
        _devices = raw_devices

    summary = {dtype: len(devs) for dtype, devs in _devices.items()}
    return json.dumps({"status": "ok", "device_counts": summary, "devices": _devices})


@mcp.tool()
async def hive_list_devices() -> str:
    """List all known Hive devices grouped by type with their names and IDs."""
    if not _devices:
        return json.dumps({"error": "No devices loaded. Call hive_start_session first."})

    result = {}
    for dtype, devs in _devices.items():
        result[dtype] = [
            {
                "id": d.get("hiveID", ""),
                "name": d.get("hiveName") or d.get("friendlyName", ""),
            }
            for d in devs
        ]
    return json.dumps(result)


@mcp.tool()
async def hive_refresh_tokens() -> str:
    """Refresh the Hive authentication tokens."""
    h = _get_hive()
    result = await h.hiveRefreshTokens(force_refresh=True)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Lights
# ---------------------------------------------------------------------------


@mcp.tool()
async def hive_light_get_state(device_name_or_id: str) -> str:
    """Get the full state of a Hive light (on/off, brightness, colour, colour temperature)."""
    h = _get_hive()
    dev = _find_device("light", device_name_or_id)
    await h.updateData(dev)
    state = {
        "state": await h.light.getState(dev),
        "brightness": await h.light.getBrightness(dev),
        "color_temp": await h.light.getColorTemp(dev),
        "min_color_temp": await h.light.getMinColorTemp(dev),
        "max_color_temp": await h.light.getMaxColorTemp(dev),
        "color": await h.light.getColor(dev),
        "color_mode": await h.light.getColorMode(dev),
    }
    return json.dumps(state)


@mcp.tool()
async def hive_light_turn_on(
    device_name_or_id: str,
    brightness: int = None,
    color_temp: int = None,
    color_r: int = None,
    color_g: int = None,
    color_b: int = None,
) -> str:
    """
    Turn a Hive light on.

    Optionally set brightness (1-100), colour temperature (Kelvin), or
    RGB colour (0-255 each). Omit any value to leave it unchanged.
    """
    h = _get_hive()
    dev = _find_device("light", device_name_or_id)
    color = [color_r, color_g, color_b] if all(v is not None for v in [color_r, color_g, color_b]) else None
    result = await h.light.turnOn(dev, brightness, color_temp, color)
    return json.dumps(result)


@mcp.tool()
async def hive_light_turn_off(device_name_or_id: str) -> str:
    """Turn a Hive light off."""
    h = _get_hive()
    dev = _find_device("light", device_name_or_id)
    result = await h.light.turnOff(dev)
    return json.dumps(result)


@mcp.tool()
async def hive_light_set_brightness(device_name_or_id: str, brightness: int) -> str:
    """Set the brightness of a Hive light (1-100)."""
    h = _get_hive()
    dev = _find_device("light", device_name_or_id)
    result = await h.light.setBrightness(dev, brightness)
    return json.dumps(result)


@mcp.tool()
async def hive_light_set_color_temp(device_name_or_id: str, color_temp: int) -> str:
    """Set the colour temperature of a Hive light in Kelvin."""
    h = _get_hive()
    dev = _find_device("light", device_name_or_id)
    result = await h.light.setColorTemp(dev, color_temp)
    return json.dumps(result)


@mcp.tool()
async def hive_light_set_color(
    device_name_or_id: str, red: int, green: int, blue: int
) -> str:
    """Set the RGB colour of a Hive light (0-255 each channel)."""
    h = _get_hive()
    dev = _find_device("light", device_name_or_id)
    result = await h.light.setColor(dev, [red, green, blue])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Heating / Climate
# ---------------------------------------------------------------------------


@mcp.tool()
async def hive_heating_get_state(device_name_or_id: str) -> str:
    """
    Get the full state of a Hive heating zone.

    Returns current temperature, target temperature, mode, boost status, etc.
    """
    h = _get_hive()
    dev = _find_device("climate", device_name_or_id)
    await h.updateData(dev)
    state = {
        "current_temperature": await h.heating.getCurrentTemperature(dev),
        "target_temperature": await h.heating.getTargetTemperature(dev),
        "min_temperature": await h.heating.getMinTemperature(dev),
        "max_temperature": await h.heating.getMaxTemperature(dev),
        "mode": await h.heating.getMode(dev),
        "state": await h.heating.getState(dev),
        "current_operation": await h.heating.getCurrentOperation(dev),
        "boost_active": await h.heating.getBoostStatus(dev),
        "boost_time_remaining": await h.heating.getBoostTime(dev),
        "operation_modes": await h.heating.getOperationModes(),
    }
    return json.dumps(state)


@mcp.tool()
async def hive_heating_set_temperature(
    device_name_or_id: str, temperature: float
) -> str:
    """Set the target temperature for a Hive heating zone (in °C)."""
    h = _get_hive()
    dev = _find_device("climate", device_name_or_id)
    result = await h.heating.setTargetTemperature(dev, str(temperature))
    return json.dumps(result)


@mcp.tool()
async def hive_heating_set_mode(device_name_or_id: str, mode: str) -> str:
    """
    Set the mode for a Hive heating zone.

    Common modes: SCHEDULE, MANUAL, OFF.
    """
    h = _get_hive()
    dev = _find_device("climate", device_name_or_id)
    result = await h.heating.setMode(dev, mode)
    return json.dumps(result)


@mcp.tool()
async def hive_heating_boost_on(
    device_name_or_id: str, minutes: int, temperature: float
) -> str:
    """
    Enable boost mode on a Hive heating zone.

    Args:
        minutes: How long to boost (e.g. 30, 60).
        temperature: Target temperature during boost (°C).
    """
    h = _get_hive()
    dev = _find_device("climate", device_name_or_id)
    result = await h.heating.setBoostOn(dev, str(minutes), temperature)
    return json.dumps(result)


@mcp.tool()
async def hive_heating_boost_off(device_name_or_id: str) -> str:
    """Cancel boost mode on a Hive heating zone."""
    h = _get_hive()
    dev = _find_device("climate", device_name_or_id)
    result = await h.heating.setBoostOff(dev)
    return json.dumps(result)


@mcp.tool()
async def hive_heating_get_schedule(device_name_or_id: str) -> str:
    """Get the now/next/later schedule entries for a Hive heating zone."""
    h = _get_hive()
    dev = _find_device("climate", device_name_or_id)
    result = await h.climate.getScheduleNowNextLater(dev)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Hot Water
# ---------------------------------------------------------------------------


@mcp.tool()
async def hive_hotwater_get_state(device_name_or_id: str) -> str:
    """Get the current state of the Hive hot water system."""
    h = _get_hive()
    dev = _find_device("water_heater", device_name_or_id)
    await h.updateData(dev)
    state = {
        "mode": await h.hotwater.getMode(dev),
        "state": await h.hotwater.getState(dev),
        "boost_active": await h.hotwater.getBoost(dev),
        "boost_time_remaining": await h.hotwater.getBoostTime(dev),
        "operation_modes": await h.hotwater.getOperationModes(),
    }
    return json.dumps(state)


@mcp.tool()
async def hive_hotwater_set_mode(device_name_or_id: str, mode: str) -> str:
    """
    Set the mode for the Hive hot water system.

    Common modes: SCHEDULE, ON, OFF.
    """
    h = _get_hive()
    dev = _find_device("water_heater", device_name_or_id)
    result = await h.hotwater.setMode(dev, mode)
    return json.dumps(result)


@mcp.tool()
async def hive_hotwater_boost_on(device_name_or_id: str, minutes: int) -> str:
    """Enable boost on the Hive hot water system for the given number of minutes."""
    h = _get_hive()
    dev = _find_device("water_heater", device_name_or_id)
    result = await h.hotwater.setBoostOn(dev, minutes)
    return json.dumps(result)


@mcp.tool()
async def hive_hotwater_boost_off(device_name_or_id: str) -> str:
    """Cancel boost on the Hive hot water system."""
    h = _get_hive()
    dev = _find_device("water_heater", device_name_or_id)
    result = await h.hotwater.setBoostOff(dev)
    return json.dumps(result)


@mcp.tool()
async def hive_hotwater_get_schedule(device_name_or_id: str) -> str:
    """Get the now/next/later schedule entries for the Hive hot water system."""
    h = _get_hive()
    dev = _find_device("water_heater", device_name_or_id)
    result = await h.waterheater.getScheduleNowNextLater(dev)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Switches / Smart Plugs
# ---------------------------------------------------------------------------


@mcp.tool()
async def hive_switch_get_state(device_name_or_id: str) -> str:
    """Get the state and power usage of a Hive smart plug / switch."""
    h = _get_hive()
    dev = _find_device("switch", device_name_or_id)
    await h.updateData(dev)
    state = {
        "state": await h.switch.getState(dev),
        "power_usage": await h.switch.getPowerUsage(dev),
    }
    return json.dumps(state)


@mcp.tool()
async def hive_switch_turn_on(device_name_or_id: str) -> str:
    """Turn a Hive smart plug / switch on."""
    h = _get_hive()
    dev = _find_device("switch", device_name_or_id)
    result = await h.switch.turnOn(dev)
    return json.dumps(result)


@mcp.tool()
async def hive_switch_turn_off(device_name_or_id: str) -> str:
    """Turn a Hive smart plug / switch off."""
    h = _get_hive()
    dev = _find_device("switch", device_name_or_id)
    result = await h.switch.turnOff(dev)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Sensors
# ---------------------------------------------------------------------------


@mcp.tool()
async def hive_sensor_get_state(device_name_or_id: str) -> str:
    """Get the state of a Hive sensor (motion, door/window, etc.)."""
    h = _get_hive()
    dev = _find_device("sensor", device_name_or_id)
    await h.updateData(dev)
    state = {
        "state": await h.sensor.getState(dev),
        "hub_online": await h.sensor.online(dev),
    }
    return json.dumps(state)


# ---------------------------------------------------------------------------
# Alarm / Home Shield
# ---------------------------------------------------------------------------


@mcp.tool()
async def hive_alarm_get_state(device_name_or_id: str) -> str:
    """Get the current mode and state of the Hive Home Shield alarm."""
    h = _get_hive()
    dev = _find_device("alarm", device_name_or_id)
    await h.updateData(dev)
    state = {
        "mode": await h.alarm.getMode(),
        "state": await h.alarm.getState(dev),
    }
    return json.dumps(state)


@mcp.tool()
async def hive_alarm_set_mode(device_name_or_id: str, mode: str) -> str:
    """
    Set the mode of the Hive Home Shield alarm.

    Common modes: armed, disarmed, partial.
    """
    h = _get_hive()
    dev = _find_device("alarm", device_name_or_id)
    result = await h.alarm.setMode(dev, mode)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    mcp.run()


if __name__ == "__main__":
    main()
