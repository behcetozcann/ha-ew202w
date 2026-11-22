"""EW202W ışık platformu."""
from __future__ import annotations
import asyncio
import time

from homeassistant.components.light import (ColorMode, LightEntity,
                                            LightEntityFeature)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              async_dispatcher_send)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import effects
from . import protocol as P
from .const import (CONF_PATCHED_LAMPS, DOMAIN, SIGNAL_DEVICE_UPDATE, SIGNAL_NEW_DEVICE,
                    SIGNAL_SOUND_START, patched_lamps)
from .server import EW202WServer

TRANSITION_GUARD_SECONDS = 1.5


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    server: EW202WServer = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()
    patched = patched_lamps(entry.options.get(CONF_PATCHED_LAMPS, ""))

    @callback
    def _add(device_id: str) -> None:
        if device_id in known:
            async_dispatcher_send(hass, SIGNAL_DEVICE_UPDATE.format(device_id))
            return
        known.add(device_id)
        async_add_entities([EW202WLight(server, device_id, device_id in patched)])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_DEVICE, _add))
    for device_id in list(server.devices):
        _add(device_id)


class EW202WLight(LightEntity):
    """EW202W RGBW ışık ve lambanın dahili akış efektleri."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.RGBW}
    _attr_color_mode = ColorMode.RGBW
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_should_poll = False

    def __init__(self, server: EW202WServer, device_id: str, patched_firmware: bool) -> None:
        self._server = server
        self._device_id = device_id
        self._patched = patched_firmware
        self._attr_unique_id = f"ew202w_{device_id}"
        self._effect_ids = effects.effect_color_ids(patched_firmware)
        self._attr_effect_list = list(self._effect_ids) + (
            [effects.SLEEP_FADE_EFFECT] if patched_firmware else []
        )
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
        self._paused: dict | None = None
        self._sound_was_on = False
        self._fade_task: asyncio.Task | None = None

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

    @property
    def extra_state_attributes(self) -> dict:
        state = self._server.state(self._device_id)
        return {key: state[key] for key in
                ("sleep_aid", "music_playing", "sleep_aid_music_id", "sleep_aid_minutes",
                 "light_state", "status_hex") if key in state}

    @callback
    def _device_updated(self) -> None:
        """Lambanın kendi bildirdiği durumu yansıt (tuşla açma/kapama dahil)."""
        state = self._server.state(self._device_id)
        if not state:
            self.async_write_ha_state()
            return
        device_on = state["light_state"] != 0
        mix = self._server.mix(self._device_id)

        if self._is_on and not device_on:
            # ses başlat/durdur komutunun hemen ardından gelen ara "kapalı" bildirimi tuş değildir
            if time.monotonic() - mix.get("transition_at", 0.0) > TRANSITION_GUARD_SECONDS:
                self._paused_by_button()
        elif not self._is_on and device_on and self._paused:
            self._resumed_by_button(mix)
        else:
            self._is_on = device_on
            if device_on and state["brightness"]:
                self._brightness = round(state["brightness"] / 100 * 255)
            mix["light_on"] = device_on
        self._sound_was_on = state["music_playing"]
        self.async_write_ha_state()

    def _cancel_fade(self) -> None:
        if self._fade_task and not self._fade_task.done():
            self._fade_task.cancel()
        self._fade_task = None

    async def _run_sleep_fade(self, start_bri_pct: int) -> None:
        """Philips Hue Go to Sleep: 15 dk boyunca gün batımından kırmızı kora inip kapanır."""
        try:
            for step in range(effects.SLEEP_FADE_STEPS + 1):
                progress = step / effects.SLEEP_FADE_STEPS
                r, g, b, w, bri = effects.sleep_fade_frame(progress, start_bri_pct)
                self._rgbw = (r, g, b, w)
                self._brightness = round(bri / 100 * 255)
                await self._send(r, g, b, w, bri)
                self._is_on = True
                self.async_write_ha_state()
                if step < effects.SLEEP_FADE_STEPS:
                    await asyncio.sleep(effects.SLEEP_FADE_INTERVAL_SEC)
            # 15 dk bitti: yalnız ışığı kapat (beyaz gürültü çalmaya devam eder)
            self._effect = None
            self._server.mix(self._device_id)["light_on"] = False
            body = P.light_body(P.LIGHT_OFF, 0, P.COLOR_CUSTOM, 0, 0, 0, 0)
            if await self._server.send_light(self._device_id, body):
                self._is_on = False
                self.async_write_ha_state()
        except asyncio.CancelledError:
            pass

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_fade()

    def _paused_by_button(self) -> None:
        """Lamba tuşla kapatıldı: tekrar açılınca efekti ve sesi sürdürmek için hatırla."""
        self._cancel_fade()
        if self._effect or self._sound_was_on:
            self._paused = {"effect": self._effect, "sound": self._sound_was_on}
        self._effect = None
        self._is_on = False
        self._server.mix(self._device_id)["light_on"] = False

    def _resumed_by_button(self, mix: dict) -> None:
        """Lamba tuşla açıldı: kapanmadan önceki efekt ve ses sürdürülür."""
        paused, self._paused = self._paused, None
        mix.update(light_on=True, sound_on=paused["sound"])
        if self._patched:
            if paused["effect"]:
                self.hass.async_create_task(self.async_turn_on(effect=paused["effect"]))
            else:
                self._is_on = True
                r, g, b, w = self._rgbw
                self.hass.async_create_task(self._send(r, g, b, w, self._bri_pct()))
            if paused["sound"] and mix["music_id"]:
                self.hass.async_create_task(self._server.send_music(
                    self._device_id, P.MUSIC_PLAY, mix["music_id"], mix["volume"]))
            return
        if paused["effect"]:
            self.hass.async_create_task(self.async_turn_on(effect=paused["effect"]))
        else:
            self._is_on = True
            self.hass.async_create_task(self._server.send_scene(self._device_id))

    @callback
    def _sound_starting(self) -> None:
        """Ses başlarken: stok yazılımda sahne komutu efekti bozar; yamalı yazılımda 5398
        ışığa hiç dokunmadığı için efekt aynen sürer."""
        if self._patched:
            return
        self._effect = None
        self._server.mix(self._device_id).update(
            light_on=self._is_on, brightness=self._bri_pct(), rgbw=tuple(self._rgbw))

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_UPDATE.format(self._device_id),
            self._device_updated))
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_SOUND_START.format(self._device_id),
            self._sound_starting))

    def _bri_pct(self) -> int:
        return max(1, round(self._brightness / 255 * 100))

    async def _send(self, r, g, b, w, bri_pct) -> bool:
        body = P.light_body(P.LIGHT_ON, bri_pct, P.COLOR_CUSTOM, r, g, b, w)
        return await self._server.send_light(self._device_id, body)

    async def async_turn_on(self, **kwargs) -> None:
        if "brightness" in kwargs:
            self._brightness = kwargs["brightness"]
        if "rgbw_color" in kwargs:
            self._rgbw = kwargs["rgbw_color"]

        self._paused = None
        effect = kwargs.get("effect")
        if not effect and self._effect and "rgbw_color" not in kwargs:
            effect = self._effect  # yalnız parlaklık değişti: efekt yeni parlaklıkla sürsün
        mix = self._server.mix(self._device_id)
        self._cancel_fade()
        if effect == effects.SLEEP_FADE_EFFECT and self._patched:
            self._effect = effect
            mix["light_on"] = True
            self._is_on = True
            self._fade_task = self.hass.async_create_task(
                self._run_sleep_fade(self._bri_pct()))
            self.async_write_ha_state()
            return
        if effect in self._effect_ids:
            self._effect = effect
            mix["light_on"] = True
            if not self._patched:
                mix["sound_on"] = False  # stok yazılımda 5394 sesi keser; yamalıda kesmez
            body = P.light_body(P.LIGHT_ON, self._bri_pct(), self._effect_ids[effect])
            if await self._server.send_light(self._device_id, body):
                self._is_on = True
                self.async_write_ha_state()
            return

        # efekt yoksa normal renk/parlaklık
        self._effect = None
        r, g, b, w = self._rgbw
        mix.update(light_on=True, brightness=self._bri_pct(), rgbw=tuple(self._rgbw))
        if mix["sound_on"] and not self._patched:  # stok yazılımda sesi kesmeyen sahne komutu
            sent = await self._server.send_scene(self._device_id)
        else:
            sent = await self._send(r, g, b, w, self._bri_pct())
        if sent:
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._cancel_fade()
        self._paused = None
        self._effect = None
        mix = self._server.mix(self._device_id)
        mix["light_on"] = False
        if mix["sound_on"] and not self._patched:
            sent = await self._server.send_scene(self._device_id)
        else:
            body = P.light_body(P.LIGHT_OFF, 0, P.COLOR_CUSTOM, 0, 0, 0, 0)
            sent = await self._server.send_light(self._device_id, body)
        if sent:
            self._is_on = False
            self.async_write_ha_state()
