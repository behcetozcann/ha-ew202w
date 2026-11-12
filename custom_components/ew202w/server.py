"""EW202W yerel TCP sunucusu: lamba buraya CLIENT olarak bağlanır.

Cihazın el sıkışma/saat/heartbeat isteklerini yanıtlayıp bağlantıyı ayakta tutar,
her cihazı deviceId ile izler ve ışık komutlarını ilgili bağlantıya yazar.
"""
from __future__ import annotations
import asyncio
import logging
from collections.abc import Callable

from . import protocol as P

_LOGGER = logging.getLogger(__name__)
STOP_TIMEOUT_SECONDS = 5
DEFAULT_VOLUME = 6


class DeviceConn:
    def __init__(self, device_id: str, writer: asyncio.StreamWriter) -> None:
        self.device_id = device_id
        self.writer = writer
        self.available = True
        self.state: dict = {}


class EW202WServer:
    """Tek dinleyici; birden çok lamba aynı porta bağlanabilir (deviceId ile ayrışır)."""

    def __init__(self, port: int, tz_offset: int,
                 on_connect: Callable[[str], None],
                 on_update: Callable[[str], None]) -> None:
        self._port = port
        self._tz_offset = tz_offset
        self._on_connect = on_connect
        self._on_update = on_update
        self._server: asyncio.AbstractServer | None = None
        self.devices: dict[str, DeviceConn] = {}
        self._writers: set[asyncio.StreamWriter] = set()
        self._mix: dict[str, dict] = {}

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "0.0.0.0", self._port)
        _LOGGER.info("EW202W TCP sunucusu dinliyor :%s", self._port)

    async def stop(self) -> None:
        # Önce açık bağlantılar kapatılır: wait_closed() bağlantılar bitmeden dönmez,
        # sıra ters olursa entegrasyonun kaldırılması/yeniden yüklenmesi sonsuza dek bekler.
        if self._server:
            self._server.close()
        for writer in list(self._writers):
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass
        if self._server:
            try:
                await asyncio.wait_for(self._server.wait_closed(), STOP_TIMEOUT_SECONDS)
            except Exception:  # noqa: BLE001
                _LOGGER.warning("EW202W sunucusu %s sn içinde kapanmadı", STOP_TIMEOUT_SECONDS)
        self.devices.clear()

    def is_available(self, device_id: str) -> bool:
        dev = self.devices.get(device_id)
        return bool(dev and dev.available)

    def state(self, device_id: str) -> dict:
        dev = self.devices.get(device_id)
        return dev.state if dev else {}

    def mix(self, device_id: str) -> dict:
        """Lambanın istenen ışık + ses durumu; ışık ve ses varlıkları bunu paylaşır."""
        return self._mix.setdefault(device_id, {
            "light_on": False, "brightness": 100, "rgbw": (0, 0, 0, 255),
            "sound_on": False, "music_id": 0, "volume": DEFAULT_VOLUME})

    async def send_scene(self, device_id: str) -> bool:
        """Işığı ve sesi tek komutla uygular (birbirini kesmeden)."""
        mix = self.mix(device_id)
        body = P.scene_body(mix["sound_on"], mix["music_id"], mix["volume"],
                            mix["light_on"], mix["brightness"], mix["rgbw"])
        return await self.send(device_id, P.MSG_SCENE, body)

    async def send_light(self, device_id: str, body: bytes) -> bool:
        return await self.send(device_id, P.MSG_LIGHT, body)

    async def send(self, device_id: str, msg_type: int, body: bytes,
                   frame_type: int = P.FRAME_REQUEST) -> bool:
        dev = self.devices.get(device_id)
        if not dev or not dev.available:
            _LOGGER.warning("EW202W %s bağlı değil, komut gönderilemedi", device_id)
            return False
        try:
            dev.writer.write(P.build_frame(msg_type, body, ftype=frame_type))
            await dev.writer.drain()
            return True
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("EW202W %s komut hatası: %s", device_id, err)
            return False

    async def _handle(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        device_id: str | None = None
        buf = bytearray()
        self._writers.add(writer)
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                buf += data
                for fr in P.parse_frames(buf):
                    # ilk kayıt çerçevesinden deviceId
                    if fr["msgType"] == P.MSG_REGISTER and device_id is None:
                        device_id = P.device_id_from_register(fr["content"]) or f"{peer}"
                        self.devices[device_id] = DeviceConn(device_id, writer)
                        _LOGGER.info("EW202W bağlandı: %s (%s)", device_id, peer)
                        self._on_connect(device_id)
                    if fr["msgType"] == P.MSG_WORK_MODE and device_id:
                        state = P.parse_work_mode(fr["content"])
                        if state and state != self.devices[device_id].state:
                            self.devices[device_id].state = state
                            mix = self.mix(device_id)
                            mix["sound_on"] = state["music_playing"]
                            if state["music_playing"]:
                                mix["music_id"] = state["sleep_aid_music_id"]
                            self._on_update(device_id)
                    # el sıkışma / saat / heartbeat yanıtı
                    resp = P.handshake_response(fr, self._tz_offset)
                    if resp is not None:
                        writer.write(resp)
                        await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("EW202W bağlantı hatası %s: %s", peer, err)
        finally:
            if device_id and self.devices.get(device_id) and \
                    self.devices[device_id].writer is writer:
                self.devices[device_id].available = False
                _LOGGER.info("EW202W koptu: %s", device_id)
                self._on_update(device_id)
            self._writers.discard(writer)
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass
