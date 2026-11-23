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
    "Gece Fırtınası": 16,
    "Kırmızı Alacakaranlık": 17,
    "Kuzey Işıkları": 18,
    "Kalp Atışı": 19,
}
SLEEP_FADE_EFFECT = "Uykuya Dal (15 dk)"
EFFECT_PREVIEW_RGBW: dict[str, tuple[int, int, int, int]] = {
    "Akış": (180, 90, 255, 0),
    "Ateş": (255, 60, 0, 0),
    "Okyanus": (0, 175, 255, 0),
    "Gün Doğumu": (255, 165, 50, 0),
    "Gece Fırtınası": (90, 140, 255, 0),
    "Kırmızı Alacakaranlık": (220, 20, 15, 0),
    "Kuzey Işıkları": (0, 220, 145, 0),
    "Kalp Atışı": (245, 38, 92, 0),
    SLEEP_FADE_EFFECT: (255, 85, 6, 0),
}
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


def effect_name_for_color_id(color_id: int, patched_firmware: bool) -> str | None:
    """Lambadan gelen colorId'yi bilinen efekt adına çevirir."""
    for name, cid in effect_color_ids(patched_firmware).items():
        if cid == color_id:
            return name
    return None


def effect_preview_rgbw(effect_name: str) -> tuple[int, int, int, int]:
    """HA kartında efektin temsil rengini göstermek için imza RGBW değeri."""
    return EFFECT_PREVIEW_RGBW.get(effect_name, (255, 180, 100, 0))
