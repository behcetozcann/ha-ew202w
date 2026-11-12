#!/usr/bin/env python3
"""EW202W tek seferlik BLE provizyon aracı.

Lambayı 2.4GHz Wi-Fi ağına bağlar ve kontrol sunucusu olarak Home Assistant
host'unu ayarlar. Bir kez çalıştırılır; sonrası entegrasyon halleder.

Kurulum:  pip install bleak
Çalıştır: python provision.py --ssid "AgAdi" --pass "sifre" --host 192.168.1.135 [--port 9988]

Lamba prize takılı, fabrika ayarına sıfırlanmış ([-] tuşu 10 sn basılı) ve
bilgisayara yakın olmalı. Çalıştıran makinede Bluetooth açık olmalı.
"""
from __future__ import annotations
import argparse
import asyncio
import struct
import sys

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    sys.exit("Önce: pip install bleak")

# protocol.py'yi entegrasyon klasöründen paylaş
sys.path.insert(0, __file__.rsplit("/tools/", 1)[0] + "/custom_components/ew202w")
import protocol as P  # noqa: E402

WRITE_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"
MFG_PREFIX = bytes.fromhex("455732325732")  # "EW22W2"


async def find_lamp(timeout=15, name_filter=b""):
    print("[BLE] lamba aranıyor (prize takılı + sıfırlanmış + yakın)...")
    found = {}

    def cb(dev, adv):
        for cid, data in (adv.manufacturer_data or {}).items():
            raw = struct.pack("<H", cid) + data
            if raw.startswith(MFG_PREFIX) and name_filter in raw:
                found.setdefault(dev.address, dev)

    sc = BleakScanner(detection_callback=cb)
    await sc.start()
    for _ in range(timeout * 2):
        if found:
            break
        await asyncio.sleep(0.5)
    await sc.stop()
    if not found:
        return None
    return next(iter(found.values()))


async def send_ble(client, frame, label):
    print(f"[BLE] {label} ({len(frame)} bayt)")
    for i in range(0, len(frame), 20):
        await client.write_gatt_char(WRITE_UUID, frame[i:i + 20], response=False)
        await asyncio.sleep(0.04)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ssid")
    ap.add_argument("--pass", dest="pwd")
    ap.add_argument("--host", required=True, help="Home Assistant host IP")
    ap.add_argument("--port", type=int, default=9988)
    ap.add_argument("--env", help=".env dosyasından SSID/PASS oku (WIFI_SSID/WIFI_PASS)")
    ap.add_argument("--lamp", default="",
                    help="Birden çok lamba varsa hedefin adı (ör. EW22W21701112)")
    a = ap.parse_args()
    if a.env and (not a.ssid or not a.pwd):
        for line in open(a.env):
            line = line.strip()
            if line.startswith("WIFI_SSID="):
                a.ssid = a.ssid or line.split("=", 1)[1]
            elif line.startswith("WIFI_PASS="):
                a.pwd = a.pwd or line.split("=", 1)[1]
    if not a.ssid or not a.pwd:
        sys.exit("SSID/PASS gerekli (--ssid/--pass veya --env <.env yolu>)")

    dev = await find_lamp(name_filter=a.lamp.encode())
    if not dev:
        sys.exit("[BLE] Lamba bulunamadı.")
    print(f"[BLE] bulundu {dev.address}, bağlanılıyor...")
    async with BleakClient(dev) as c:
        await send_ble(c, P.build_frame(P.MSG_SET_SERVER,
                       P.server_address_body(a.host, a.port)), "sunucu adresi")
        await asyncio.sleep(0.3)
        await send_ble(c, P.build_frame(P.MSG_WIFI_CONFIG,
                       P.wifi_config_body(a.ssid, a.pwd)), "wifi config")
    print(f"[OK] Provizyon gönderildi. Lamba {a.host}:{a.port} adresine bağlanacak.")
    print("     Home Assistant'ta EW202W ışığı birkaç saniye içinde görünmeli.")


if __name__ == "__main__":
    asyncio.run(main())
