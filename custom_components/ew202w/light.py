"""EW202W ışık platformu."""
from __future__ import annotations
import asyncio
import logging

from homeassistant.components.light import (ColorMode, LightEntity,
                                            LightEntityFeature)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              async_dispatcher_send)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import effects
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
            async_dispatcher_send(hass, SIGNAL_DEVICE_UPDATE.format(device_id))
            return
        known.add(device_id)
        async_add_entities([EW202WLight(server, device_id)])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_DEVICE, _add))
    for device_id in list(server.devices):
        _add(device_id)


class EW202WLight(LightEntity):
    """EW202W RGBW ışık + hazır renkler ve animasyonlu efektler."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.RGBW}
    _attr_color_mode = ColorMode.RGBW
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_should_poll = False

    def __init__(self, server: EW202WServer, device_id: str) -> None:
        self._server = server
        self._device_id = device_id
        self._attr_unique_id = f"ew202w_{device_id}"
        self._attr_effect_list = effects.effect_list()
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": f"Uyku Işığı {device_id[-4:]}",
            "manufacturer": "Sleepace / Vestel",
            "model": "EW202W",
        }
        self._is_on = False
        self._brightness = 255
        self._rgbw = (255, 255, 255, 255)
        self._effect: str | None = None
        self._anim_task: asyncio.Task | None = None

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

    @property
    def effect(self) -> str | None:
        return self._effect

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_UPDATE.format(self._device_id),
            self.async_write_ha_state))

    async def async_will_remove_from_hass(self) -> None:
        self._stop_anim()

    def _stop_anim(self) -> None:
        if self._anim_task and not self._anim_task.done():
            self._anim_task.cancel()
        self._anim_task = None

    def _bri_pct(self) -> int:
        return max(1, round(self._brightness / 255 * 100))

    async def _send(self, r, g, b, w, bri_pct) -> bool:
        body = P.light_body(P.LIGHT_ON, bri_pct, P.COLOR_CUSTOM, r, g, b, w)
        return await self._server.send_light(self._device_id, body)

    async def _run_effect(self, name: str) -> None:
        step = 0
        try:
            while True:
                r, g, b, w, bri = effects.frame(name, step)
                await self._send(r, g, b, w, bri)
                step += 1
                await asyncio.sleep(effects.frame_interval(name))
        except asyncio.CancelledError:
            pass
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("EW202W efekt hatası (%s): %s", name, err)

    async def async_turn_on(self, **kwargs) -> None:
        if "brightness" in kwargs:
            self._brightness = kwargs["brightness"]
        if "rgbw_color" in kwargs:
            self._rgbw = kwargs["rgbw_color"]

        effect = kwargs.get("effect")
        if effect:
            self._stop_anim()
            self._effect = effect
            if effects.is_animated(effect):
                self._is_on = True
                self._anim_task = self.hass.async_create_task(
                    self._run_effect(effect))
                self.async_write_ha_state()
                return
            rgbw = effects.static_rgbw(effect)
            if rgbw:
                self._rgbw = rgbw
                r, g, b, w = rgbw
                if await self._send(r, g, b, w, self._bri_pct()):
                    self._is_on = True
                    self.async_write_ha_state()
                return

        # efekt yoksa normal renk/parlaklık
        self._stop_anim()
        self._effect = None
        r, g, b, w = self._rgbw
        if await self._send(r, g, b, w, self._bri_pct()):
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._stop_anim()
        self._effect = None
        body = P.light_body(P.LIGHT_OFF, 0, P.COLOR_CUSTOM, 0, 0, 0, 0)
        if await self._server.send_light(self._device_id, body):
            self._is_on = False
            self.async_write_ha_state()
