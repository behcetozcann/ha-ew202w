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
EVENT_STATE_CHANGED = f"{DOMAIN}_state_changed"

# Lambadaki sesler: ad -> musicId (/spiffs/<id>.MP3). 31132 beyaz gürültüyle değiştirildi.
SOUND_WHITE_NOISE = "Beyaz Gürültü"
SOUNDS: dict[str, int] = {SOUND_WHITE_NOISE: 31132}
SOUNDS.update({f"Ses {music_id}": music_id
               for music_id in range(31131, 31149) if music_id != 31132})
