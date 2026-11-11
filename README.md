# EW202W Sleep Light — Home Assistant Integration

Local, cloud-free Home Assistant control for the **Sleepace EW202W** smart music
sleep light (sold in Turkey as **Vestel Akıllı Uyku Işığı 2**, model `EW22W21701115`).
No Sleepace account, no internet — the lamp talks only to your Home Assistant.

The lamp is an ESP32 device that normally connects out to the Sleepace cloud. This
integration runs a small TCP server inside Home Assistant; after a one-time BLE
provisioning step the lamp connects to Home Assistant instead, and appears as a
`light` entity with on/off, brightness and full RGBW color.

> Protocol reverse-engineered from the official Android apps (SleepNote / Vestel
> Smart Health). Not affiliated with Sleepace or Vestel.

## How it works

1. The lamp joins your 2.4 GHz Wi-Fi and is told to use your HA host as its server
   (one-time BLE provisioning).
2. The lamp connects to the integration's TCP server (default port `9988`) and stays
   connected (the integration answers its registration / time-sync / heartbeat).
3. You control it from Home Assistant like any light.

## Install (HACS)

1. HACS → ⋮ → Custom repositories → add this repo, category **Integration**.
2. Install **EW202W Sleep Light**, restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **EW202W** → keep port `9988`.

(Manual: copy `custom_components/ew202w` into your HA `config/custom_components/`.)

## One-time provisioning (BLE)

Run from any computer with Bluetooth, near the lamp (plugged in, factory-reset by
holding the **[–]** button for 10 s):

```bash
pip install bleak
python tools/provision.py --ssid "YourWifi" --pass "YourPassword" --host 192.168.1.135
```

- `--host` = your Home Assistant IP. `--port` optional (default `9988`, must match the
  integration).
- The lamp is **2.4 GHz only**.
- After it runs, the light shows up in Home Assistant within a few seconds.

> The HA host usually has Bluetooth, but provisioning uses the machine you run the
> script on. You can provision from a laptop and still point the lamp at the HA host.

## Features / limitations

- ✅ On/off, brightness (1–100 %), full RGBW color. Clock stays correct (HA pushes time).
- ✅ Multiple lamps (each connects to the same port, tracked by device id).
- ⚠️ Optimistic state (no live feedback yet); physical button changes aren't reflected.
- ⚠️ Alarm / music / white-noise not exposed yet (planned).

## Credits

Reverse engineering & integration by the community. Protocol notes in the project.
MIT licensed.
