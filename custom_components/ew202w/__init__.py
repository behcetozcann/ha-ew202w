"""EW202W (Sleepace/Vestel akıllı uyku ışığı) yerel entegrasyonu."""
from __future__ import annotations
import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import protocol as P
from .const import (CONF_PORT, CONF_TZ_OFFSET, DEFAULT_PORT, DOMAIN, EVENT_STATE_CHANGED,
                    SERVICE_UPDATE_FIRMWARE, SIGNAL_DEVICE_UPDATE, SIGNAL_NEW_DEVICE)
from .server import EW202WServer

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.LIGHT, Platform.MEDIA_PLAYER]
UPDATE_SCHEMA = vol.Schema({vol.Required("device_id"): cv.string,
                            vol.Required("url"): cv.url})


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

    last_summary: dict[str, dict] = {}

    def on_connect(device_id: str) -> None:
        async_dispatcher_send(hass, SIGNAL_NEW_DEVICE, device_id)

    def on_update(device_id: str) -> None:
        async_dispatcher_send(hass, SIGNAL_DEVICE_UPDATE.format(device_id))
        # Tuşla yapılan değişiklikler de buradan gelir; otomasyonlar bu olayı dinleyebilir.
        # Efekt karelerinde olay yağmuru olmasın diye yalnız aç/kapa türü değişimler yayınlanır.
        state = server.state(device_id)
        summary = {"light_on": state.get("light_state", 0) != 0,
                   "sleep_aid": state.get("sleep_aid", False),
                   "music_playing": state.get("music_playing", False)}
        if state and last_summary.get(device_id) != summary:
            last_summary[device_id] = summary
            hass.bus.async_fire(EVENT_STATE_CHANGED, {"device_id": device_id, **summary})

    server = EW202WServer(port, tz_offset, on_connect, on_update)
    try:
        await server.start()
    except OSError as err:
        _LOGGER.error("EW202W portu %s açılamadı: %s", port, err)
        return False

    async def update_firmware(call: ServiceCall) -> None:
        """Lambaya URL'den yazılım yükletir (lamba dosyayı HTTP ile kendisi indirir)."""
        body = P.update_body(call.data["url"])
        sent = await server.send(call.data["device_id"], P.MSG_UPDATE, body,
                                 frame_type=P.FRAME_POST)
        _LOGGER.warning("EW202W %s yazılım yükleme komutu %s: %s", call.data["device_id"],
                        "gönderildi" if sent else "GÖNDERİLEMEDİ", call.data["url"])

    hass.services.async_register(DOMAIN, SERVICE_UPDATE_FIRMWARE, update_firmware,
                                 schema=UPDATE_SCHEMA)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = server
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    server: EW202WServer | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if server:
        await server.stop()
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_FIRMWARE)
    return unloaded
