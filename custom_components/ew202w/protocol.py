"""EW202W (Sleepace/Vestel akıllı uyku ışığı) TCP protokolü.

SleepNote / Vestel Smart Health Android uygulamalarından tersine mühendislikle
çözüldü (SocketFrame / MedicaProtocol1). Saf Python, HA bağımsız; hem entegrasyon
hem provizyon aracı bunu paylaşır.

Çerçeve (big-endian):
  [00][01][gallery:4][ftype][frameCount:2=1][frameNum:2=0][serial:2]
  [msgType:2][içerik][crc32:4][b"$_@-"]
  ftype: 2=Request, 3=Response, 1=POST, 0=ACK
Yanıt (ftype=3) içeriği 2 baytlık sonuç kodu (0x0000) ile BAŞLAR, sonra veri gelir.
"""
from __future__ import annotations
import struct
import time
import zlib

FRAME_END = b"$_@-"

# msgType sabitleri (SocketFrame.java)
MSG_WIFI_CONFIG = 5376
MSG_SET_SERVER = 5378
MSG_LIGHT = 5394
MSG_REGISTER = 1028
MSG_TIME = 513

# ışık işlemi
LIGHT_OFF = 0
LIGHT_ON = 1
LIGHT_BRIGHTNESS = 2
COLOR_CUSTOM = 255  # colorId=255 => RGBW serbest renk

_serial = 0


def _next_serial() -> int:
    global _serial
    _serial = 1 if _serial >= 0x7FFF else _serial + 1
    return _serial


def build_frame(msg_type: int, content: bytes = b"", ftype: int = 2,
                serial: int | None = None, gallery: int = 0) -> bytes:
    if serial is None:
        serial = _next_serial()
    b = bytearray()
    b += b"\x00\x01"
    b += struct.pack(">i", gallery)
    b += bytes([ftype & 0xFF])
    b += struct.pack(">h", 1)   # frameCount
    b += struct.pack(">h", 0)   # frameNum
    b += struct.pack(">h", serial)
    b += struct.pack(">h", msg_type)
    b += content
    crc = zlib.crc32(bytes(b)) & 0xFFFFFFFF
    return bytes(b) + struct.pack(">I", crc) + FRAME_END


def parse_frames(buf: bytearray) -> list[dict]:
    """buf içindeki tam çerçeveleri ayıkla (tükettiklerini buf'tan siler)."""
    out = []
    while True:
        idx = buf.find(FRAME_END)
        if idx < 0:
            break
        raw = bytes(buf[:idx + 4])
        del buf[:idx + 4]
        if len(raw) < 19:
            continue
        out.append({
            "ftype": raw[6],
            "serial": struct.unpack(">h", raw[11:13])[0],
            "msgType": struct.unpack(">h", raw[13:15])[0],
            "content": raw[15:-8],
            "raw": raw,
        })
    return out


def time_payload(tz_offset_seconds: int = 10800, time_mode: int = 0) -> bytes:
    """513 saat yanıtı verisi: ts(UTC) + tzOffset + season + seasonOffset + timeMode."""
    ts = int(time.time())
    return (struct.pack(">i", ts) + struct.pack(">i", tz_offset_seconds)
            + bytes([0]) + struct.pack(">i", 0) + bytes([time_mode & 0xFF]))


def light_body(operation: int, brightness: int = 100, color_id: int = COLOR_CUSTOM,
               r: int = 0, g: int = 0, b: int = 0, w: int = 0) -> bytes:
    """Işık komutu gövdesi (msgType 5394)."""
    bri = max(1, min(int(brightness), 100))
    return (bytes([operation & 0xFF, bri & 0xFF, color_id & 0xFF,
                   r & 0xFF, g & 0xFF, b & 0xFF, w & 0xFF])
            + struct.pack(">h", 0))


def handshake_response(frame: dict, tz_offset_seconds: int = 10800,
                       time_mode: int = 0) -> bytes | None:
    """Cihazın Request/POST çerçevesine verilecek yanıtı üretir (yoksa None).

    - Request (ftype=2): Response (ftype=3). 513 ise gerçek saat, diğerleri boş-OK.
    - POST (ftype=1): ACK (ftype=0).
    Bu yanıtlar olmadan cihaz ~8 sn'de bağlantıyı düşürür.
    """
    ft = frame["ftype"]
    if ft == 2:
        if frame["msgType"] == MSG_TIME:
            body = struct.pack(">h", 0) + time_payload(tz_offset_seconds, time_mode)
        else:
            body = struct.pack(">h", 0)
        return build_frame(frame["msgType"], body, ftype=3, serial=frame["serial"])
    if ft == 1:
        return build_frame(frame["msgType"], b"", ftype=0, serial=frame["serial"])
    return None


def device_id_from_register(content: bytes) -> str | None:
    """1028 kayıt içeriğinden deviceId çıkar: [01][deviceId...][00][...]."""
    if len(content) < 2:
        return None
    body = content[1:]
    end = body.find(b"\x00")
    raw = body[:end] if end >= 0 else body
    try:
        return raw.decode("latin1").strip() or None
    except Exception:
        return None


def wifi_config_body(ssid: str, pwd: str) -> bytes:
    b = bytearray(120)
    s = ssid.encode()
    b[0:len(s)] = s
    b[33] = 1 if pwd else 0
    p = pwd.encode()
    b[34:34 + len(p)] = p
    b[99] = 0
    return bytes(b)


def server_address_body(ip: str, port: int) -> bytes:
    b = bytearray(162)
    s = ip.encode()
    b[0:len(s)] = s
    b[32:34] = struct.pack(">h", port)
    b[34:34 + len(s)] = s
    return bytes(b)
