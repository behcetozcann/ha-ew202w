"""EW202W ses çalar: lambanın içindeki sesleri (beyaz gürültü dahil) çalar."""
from __future__ import annotations

from homeassistant.components.media_player import (MediaPlayerEntity,
                                                    MediaPlayerEntityFeature,
                                                    MediaPlayerState)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import protocol as P
from .const import (DOMAIN, SIGNAL_DEVICE_UPDATE, SIGNAL_NEW_DEVICE, SOUND_WHITE_NOISE,
                    SOUNDS)
from .server import EW202WServer

DEFAULT_VOLUME = 6


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    server: EW202WServer = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add(device_id: str) -> None:
        if device_id not in known:
            known.add(device_id)
            async_add_entities([EW202WSoundPlayer(server, device_id)])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_DEVICE, _add))
    for device_id in list(server.devices):
        _add(device_id)


class EW202WSoundPlayer(MediaPlayerEntity):
    """Kaynak = lambadaki ses; çal/durdur ve ses düzeyi."""

    _attr_has_entity_name = True
    _attr_name = "Ses"
    _attr_should_poll = False
    _attr_source_list = list(SOUNDS)
    _attr_supported_features = (MediaPlayerEntityFeature.PLAY
                                | MediaPlayerEntityFeature.STOP
                                | MediaPlayerEntityFeature.VOLUME_SET
                                | MediaPlayerEntityFeature.SELECT_SOURCE)

    def __init__(self, server: EW202WServer, device_id: str) -> None:
        self._server = server
        self._device_id = device_id
        self._attr_unique_id = f"ew202w_{device_id}_sound"
        self._attr_device_info = {"identifiers": {(DOMAIN, device_id)}}
        self._attr_source = SOUND_WHITE_NOISE
        self._volume = DEFAULT_VOLUME
        self._playing = False

    @property
    def available(self) -> bool:
        return self._server.is_available(self._device_id)

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.PLAYING if self._playing else MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float:
        return self._volume / P.MAX_VOLUME

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

    async def _send(self, operation: int, music_id: int = 0) -> bool:
        body = P.music_body(operation, music_id, self._volume)
        return await self._server.send(self._device_id, P.MSG_MUSIC, body)

    async def async_media_play(self) -> None:
        if await self._send(P.MUSIC_PLAY, SOUNDS[self._attr_source]):
            self._playing = True
            self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        if await self._send(P.MUSIC_STOP):
            self._playing = False
            self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        self._attr_source = source
        await self.async_media_play()

    async def async_set_volume_level(self, volume: float) -> None:
        self._volume = max(1, round(volume * P.MAX_VOLUME))
        if await self._send(P.MUSIC_VOLUME):
            self.async_write_ha_state()
