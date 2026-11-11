"""EW202W entegrasyonu sabitleri."""
DOMAIN = "ew202w"

CONF_PORT = "port"
CONF_TZ_OFFSET = "tz_offset"

DEFAULT_PORT = 9988

# Yeni cihaz bağlandığında / durum değiştiğinde yayınlanan dispatcher sinyalleri
SIGNAL_NEW_DEVICE = f"{DOMAIN}_new_device"
SIGNAL_DEVICE_UPDATE = f"{DOMAIN}_device_update_{{}}"  # .format(device_id)
