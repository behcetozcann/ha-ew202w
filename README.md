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

## New in 0.3.0

- **Sound player** (`media_player`): plays the sounds stored in the lamp
  (`/spiffs/<musicId>.MP3`), with stop and volume. Music and light are one "sleep aid"
  mode in the stock firmware, so starting one can stop the other.
- **Real state**: the lamp's own status reports update the light entity, so changes made
  with the lamp's buttons show up in Home Assistant. An `ew202w_state_changed` event
  (`light_on`, `sleep_aid`, `music_playing`) is fired for automations.
- **Built-in flow mode** and twelve ambient effects (candle, fireplace, sparkle, glisten,
  opal, prism, sunrise, sunset, underwater, cosmos, sunbeam, enchant).
- **`ew202w.update_firmware` service**: tells the lamp to download a firmware image from
  an HTTP URL and install it to its spare app slot. The stock firmware does not verify a
  signature, so only use an image you have validated; keep a UART backup.
- `tools/provision.py --lamp <name>` targets one lamp when several are nearby.

## New in 0.3.2

- Fixed colors are no longer listed as effects; pick them from the light dialog's
  favorite colors instead. The effect list now holds only animations.
- Sound sources are named `Ses <number>` by default. Per-lamp names can be set in the
  integration's options, one per line: `<lamp id>:<sound number>=<name>`.

## Credits

Reverse engineering & integration by the community. Protocol notes in the project.
MIT licensed.
