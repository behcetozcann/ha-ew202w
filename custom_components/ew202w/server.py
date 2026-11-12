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

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "0.0.0.0", self._port)
        _LOGGER.info("EW202W TCP sunucusu dinliyor :%s", self._port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        for dev in self.devices.values():
            try:
                dev.writer.close()
            except Exception:  # noqa: BLE001
                pass
        self.devices.clear()

    def is_available(self, device_id: str) -> bool:
        dev = self.devices.get(device_id)
        return bool(dev and dev.available)

    def state(self, device_id: str) -> dict:
        dev = self.devices.get(device_id)
        return dev.state if dev else {}

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
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass
