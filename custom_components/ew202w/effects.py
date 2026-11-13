"""EW202W ışık efektleri: yalnız lambanın kendi yazılımındaki akış modları.

Efekt seçilince lambaya tek bir ışık komutu (colorId) gider; renk geçişlerini lamba kendisi
yapar. Entegrasyon kare göndermez, bu yüzden lambanın kalıcı belleği yıpranmaz.

Akış (colorId 9) stok yazılımda vardır. Diğerleri yalnız yamalı yazılımda vardır
(firmware/yama_yap.py "efektler"); stok yazılımda bu numaralar lambayı kapatır.
Sabit renkler efekt değildir; HA ışık penceresindeki sık kullanılan renklerden seçilir.
"""
from __future__ import annotations

STOCK_EFFECTS = {"Akış": 9}
PATCHED_EFFECTS = {"Ateş": 13, "Okyanus": 14, "Gün Doğumu": 15, "Büyü": 16}


def effect_color_ids(patched_firmware: bool) -> dict[str, int]:
    """Efekt adı -> lambaya gönderilecek colorId."""
    return {**STOCK_EFFECTS, **PATCHED_EFFECTS} if patched_firmware else dict(STOCK_EFFECTS)
