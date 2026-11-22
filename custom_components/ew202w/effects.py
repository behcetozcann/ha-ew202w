"""EW202W ışık efektleri: yalnız lambanın kendi yazılımındaki akış modları.

Efekt seçilince lambaya tek bir ışık komutu (colorId) gider; renk geçişlerini lamba kendisi
yapar. Entegrasyon kare göndermez, bu yüzden lambanın kalıcı belleği yıpranmaz.

Akış (colorId 9) stok yazılımda vardır. Diğerleri yalnız yamalı yazılımda vardır
(firmware/yama_yap.py "efektler"); stok yazılımda bu numaralar lambayı kapatır.
Sabit renkler efekt değildir; HA ışık penceresindeki sık kullanılan renklerden seçilir.
"""
from __future__ import annotations

STOCK_EFFECTS = {"Akış": 9}
PATCHED_EFFECTS = {
    "Ateş": 13,
    "Okyanus": 14,
    "Gün Doğumu": 15,
    "Büyü": 16,
    "Kırmızı Alacakaranlık": 17,
}
SLEEP_FADE_EFFECT = "Uykuya Dal (15 dk)"
SLEEP_FADE_STEPS = 45          # 45 adım × 20 sn = 15 dakika (flash dostu, sıfır ses kesintisi)
SLEEP_FADE_INTERVAL_SEC = 20
SLEEP_FADE_KEYFRAMES = [       # (ilerleme 0..1, R, G, B, parlaklık çarpanı)
    (0.00, 255, 85, 6, 1.00),  # Sıcak gün batımı kehribarı
    (0.25, 255, 42, 2, 0.82),  # Turuncu-kızıl akşam
    (0.55, 225, 12, 0, 0.55),  # Derin yakut kızılı
    (0.80, 145, 2, 0, 0.22),   # Loş kırmızı kor
    (0.95, 75, 0, 0, 0.06),    # Çok loş gece koru
    (1.00, 35, 0, 0, 0.02),    # Son kor → ardından lamba kapanır
]


def sleep_fade_frame(progress: float, start_bri_pct: int) -> tuple[int, int, int, int, int]:
    """0..1 arası ilerleme için (R, G, B, W=0, parlaklık 1..100) ara değeri üretir."""
    p = max(0.0, min(1.0, progress))
    for i in range(len(SLEEP_FADE_KEYFRAMES) - 1):
        p0, r0, g0, b0, m0 = SLEEP_FADE_KEYFRAMES[i]
        p1, r1, g1, b1, m1 = SLEEP_FADE_KEYFRAMES[i + 1]
        if p <= p1:
            t = 0.0 if p1 == p0 else (p - p0) / (p1 - p0)
            r = round(r0 + (r1 - r0) * t)
            g = round(g0 + (g1 - g0) * t)
            b = round(b0 + (b1 - b0) * t)
            bri = max(1, round(start_bri_pct * (m0 + (m1 - m0) * t)))
            return r, g, b, 0, bri
    return 35, 0, 0, 0, 1


def effect_color_ids(patched_firmware: bool) -> dict[str, int]:
    """Efekt adı -> lambaya gönderilecek colorId."""
    return {**STOCK_EFFECTS, **PATCHED_EFFECTS} if patched_firmware else dict(STOCK_EFFECTS)
