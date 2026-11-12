"""EW202W ses çalar: lambanın içindeki sesleri (beyaz gürültü dahil) çalar."""
from __future__ import annotations

import time

from homeassistant.components.media_player import (MediaPlayerEntity,
                                                    MediaPlayerEntityFeature,
                                                    MediaPlayerState)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              async_dispatcher_send)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import protocol as P
from .const import (CONF_SOUND_NAMES, DOMAIN, SIGNAL_DEVICE_UPDATE, SIGNAL_NEW_DEVICE,
                    SIGNAL_SOUND_START, sound_names)
from .server import EW202WServer


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    server: EW202WServer = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add(device_id: str) -> None:
        if device_id not in known:
            known.add(device_id)
            sounds = sound_names(entry.options.get(CONF_SOUND_NAMES, ""), device_id)
            async_add_entities([EW202WSoundPlayer(server, device_id, sounds)])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_DEVICE, _add))
    for device_id in list(server.devices):
        _add(device_id)


class EW202WSoundPlayer(MediaPlayerEntity):
    """Kaynak = lambadaki ses; çal/durdur ve ses düzeyi."""

    _attr_has_entity_name = True
    _attr_name = "Ses"
    _attr_should_poll = False
    _attr_supported_features = (MediaPlayerEntityFeature.PLAY
                                | MediaPlayerEntityFeature.STOP
                                | MediaPlayerEntityFeature.VOLUME_SET
                                | MediaPlayerEntityFeature.SELECT_SOURCE)

    def __init__(self, server: EW202WServer, device_id: str,
                 sounds: dict[str, int]) -> None:
        self._server = server
        self._device_id = device_id
        self._sounds = sounds
        self._attr_source_list = list(sounds)
        self._attr_unique_id = f"ew202w_{device_id}_sound"
        self._attr_device_info = {"identifiers": {(DOMAIN, device_id)}}
        self._attr_source = self._attr_source_list[0]
        self._playing = False

    @property
    def available(self) -> bool:
        return self._server.is_available(self._device_id)

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.PLAYING if self._playing else MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float:
        return self._server.mix(self._device_id)["volume"] / P.MAX_VOLUME

    @callback
    def _device_updated(self) -> None:
        state = self._server.state(self._device_id)
        if state:
            self._playing = state["music_playing"]
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_UPDATE.format(self._device_id),
            self._device_updated))

    async def _apply(self, sound_on: bool) -> None:
        mix = self._server.mix(self._device_id)
        mix["sound_on"] = sound_on
        mix["transition_at"] = time.monotonic()
        mix["music_id"] = self._sounds[self._attr_source]
        if await self._server.send_scene(self._device_id):
            self._playing = sound_on
            self.async_write_ha_state()

    async def async_media_play(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_SOUND_START.format(self._device_id))
        await self._apply(True)

    async def async_media_stop(self) -> None:
        await self._apply(False)

    async def async_select_source(self, source: str) -> None:
        self._attr_source = source
        await self.async_media_play()

    async def async_set_volume_level(self, volume: float) -> None:
        self._server.mix(self._device_id)["volume"] = max(1, round(volume * P.MAX_VOLUME))
        if self._playing:
            await self._server.send_scene(self._device_id)
        self.async_write_ha_state()
