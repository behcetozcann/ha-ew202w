"""EW202W entegrasyonu sabitleri."""
DOMAIN = "ew202w"

CONF_PORT = "port"
CONF_TZ_OFFSET = "tz_offset"

DEFAULT_PORT = 9988

# Yeni cihaz bağlandığında / durum değiştiğinde yayınlanan dispatcher sinyalleri
SIGNAL_NEW_DEVICE = f"{DOMAIN}_new_device"
SIGNAL_DEVICE_UPDATE = f"{DOMAIN}_device_update_{{}}"  # .format(device_id)
# Ses başlatılmadan hemen önce yayınlanır: ışık komutu sesi kestiği için
# çalışan efekt animasyonu durdurulmalıdır.
SIGNAL_SOUND_START = f"{DOMAIN}_sound_start_{{}}"  # .format(device_id)

SERVICE_UPDATE_FIRMWARE = "update_firmware"
SERVICE_SEND_RAW = "send_raw"
EVENT_STATE_CHANGED = f"{DOMAIN}_state_changed"

CONF_SOUND_NAMES = "sound_names"

# Lambadaki sesler: musicId = /spiffs/<id>.MP3. Adlar seçeneklerden lambaya özel verilebilir.
SOUND_IDS = range(31131, 31149)


def sound_names(option_text: str, device_id: str) -> dict[str, int]:
    """Kaynak adı -> musicId. Seçenek satırı biçimi: <lamba kimliği>:<musicId>=<ad>"""
    custom = {}
    for line in option_text.splitlines():
        match = line.strip().partition("=")
        target, _, music_id = match[0].partition(":")
        if match[2].strip() and target.strip() == device_id and music_id.strip().isdigit():
            custom[int(music_id)] = match[2].strip()
    return {custom.get(music_id, f"Ses {music_id}"): music_id for music_id in SOUND_IDS}
