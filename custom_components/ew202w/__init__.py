"""EW202W (Sleepace/Vestel akıllı uyku ışığı) yerel entegrasyonu."""
from __future__ import annotations
import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (CONF_PORT, CONF_TZ_OFFSET, DEFAULT_PORT, DOMAIN,
                    SIGNAL_DEVICE_UPDATE, SIGNAL_NEW_DEVICE)
from .server import EW202WServer

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.LIGHT]


def _tz_offset_seconds(hass: HomeAssistant) -> int:
    """HA yerel saat dilimi ofseti (saniye)."""
    try:
        import homeassistant.util.dt as dt_util
        tz = dt_util.get_time_zone(hass.config.time_zone)
        off = datetime.now(tz).utcoffset()
        return int(off.total_seconds()) if off else 10800
    except Exception:  # noqa: BLE001
        return 10800


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    tz_offset = entry.data.get(CONF_TZ_OFFSET) or _tz_offset_seconds(hass)

    def on_connect(device_id: str) -> None:
        async_dispatcher_send(hass, SIGNAL_NEW_DEVICE, device_id)

    def on_update(device_id: str) -> None:
        async_dispatcher_send(hass, SIGNAL_DEVICE_UPDATE.format(device_id))

    server = EW202WServer(port, tz_offset, on_connect, on_update)
    try:
        await server.start()
    except OSError as err:
        _LOGGER.error("EW202W portu %s açılamadı: %s", port, err)
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = server
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    server: EW202WServer | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if server:
        await server.stop()
    return unloaded
