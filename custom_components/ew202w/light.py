"""EW202W ışık platformu."""
from __future__ import annotations
import logging

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              async_dispatcher_send)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import protocol as P
from .const import DOMAIN, SIGNAL_DEVICE_UPDATE, SIGNAL_NEW_DEVICE
from .server import EW202WServer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    server: EW202WServer = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add(device_id: str) -> None:
        if device_id in known:
            # zaten var olan cihaz yeniden bağlandı: entity'yi tazele (müsaitlik)
            async_dispatcher_send(hass, SIGNAL_DEVICE_UPDATE.format(device_id))
            return
        known.add(device_id)
        async_add_entities([EW202WLight(server, device_id)])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_DEVICE, _add))

    # Kurulumdan önce bağlanmış cihazlar varsa onları da ekle
    for device_id in list(server.devices):
        _add(device_id)


class EW202WLight(LightEntity):
    """EW202W RGBW ışık. Durum geri bildirimi olmadığı için iyimser (optimistic)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.RGBW}
    _attr_color_mode = ColorMode.RGBW
    _attr_should_poll = False

    def __init__(self, server: EW202WServer, device_id: str) -> None:
        self._server = server
        self._device_id = device_id
        self._attr_unique_id = f"ew202w_{device_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": f"Uyku Işığı {device_id[-4:]}",
            "manufacturer": "Sleepace / Vestel",
            "model": "EW202W",
        }
        self._is_on = False
        self._brightness = 255
        self._rgbw = (255, 255, 255, 255)

    @property
    def available(self) -> bool:
        return self._server.is_available(self._device_id)

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def rgbw_color(self):
        return self._rgbw

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_UPDATE.format(self._device_id),
            self.async_write_ha_state))

    async def async_turn_on(self, **kwargs) -> None:
        if "brightness" in kwargs:
            self._brightness = kwargs["brightness"]
        if "rgbw_color" in kwargs:
            self._rgbw = kwargs["rgbw_color"]
        r, g, b, w = self._rgbw
        bri = max(1, round(self._brightness / 255 * 100))
        body = P.light_body(P.LIGHT_ON, bri, P.COLOR_CUSTOM, r, g, b, w)
        if await self._server.send_light(self._device_id, body):
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        body = P.light_body(P.LIGHT_OFF, 0, P.COLOR_CUSTOM, 0, 0, 0, 0)
        if await self._server.send_light(self._device_id, body):
            self._is_on = False
            self.async_write_ha_state()
