"""EW202W ışık efektleri: hazır renkler + yazılımsal animasyonlar.

Animasyonlar entegrasyon tarafında üretilir ve lambaya periyodik RGBW karesi
olarak gönderilir (cihazda hazır 'ateş' efekti olmadığı için).
"""
from __future__ import annotations
import colorsys
import random

# Hazır (statik) popüler renkler: ad -> (R, G, B, W)
STATIC_COLORS: dict[str, tuple[int, int, int, int]] = {
    "Beyaz": (0, 0, 0, 255),
    "Sıcak Beyaz": (255, 160, 60, 120),
    "Kırmızı": (255, 0, 0, 0),
    "Turuncu": (255, 90, 0, 0),
    "Sarı": (255, 200, 0, 0),
    "Yeşil": (0, 255, 0, 0),
    "Camgöbeği": (0, 255, 200, 0),
    "Mavi": (0, 0, 255, 0),
    "Gökyüzü Mavisi": (0, 150, 255, 0),
    "Mor": (150, 0, 255, 0),
    "Pembe": (255, 0, 150, 0),
    "Magenta": (255, 0, 255, 0),
    "YouTube Kırmızısı": (255, 0, 0, 0),
    "Lime": (160, 255, 0, 0),
}

# Animasyonlu efektler (yazılımsal)
ANIMATED = ["Gökkuşağı", "Renk Döngüsü", "Ateş", "Nabız", "Strobe", "Parti", "Noel"]

# Gökkuşağı/döngü için 7 temel renk
RAINBOW = [(255, 0, 0), (255, 110, 0), (255, 220, 0), (0, 255, 0),
           (0, 160, 255), (40, 0, 255), (160, 0, 255)]


def effect_list() -> list[str]:
    return list(STATIC_COLORS.keys()) + ANIMATED


def is_animated(name: str) -> bool:
    return name in ANIMATED


def static_rgbw(name: str) -> tuple[int, int, int, int] | None:
    return STATIC_COLORS.get(name)


def frame(name: str, step: int) -> tuple[int, int, int, int, int]:
    """Animasyon karesi -> (R, G, B, W, brightness%). step her çağrıda artar."""
    if name == "Gökkuşağı":
        h = (step % 120) / 120.0
        r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(h, 1, 1))
        return r, g, b, 0, 100
    if name == "Renk Döngüsü":
        r, g, b = RAINBOW[step % len(RAINBOW)]
        return r, g, b, 0, 100
    if name == "Ateş":
        base = random.randint(180, 255)
        g = int(base * random.uniform(0.25, 0.5))
        bri = random.randint(55, 100)
        return base, g, 0, 0, bri
    if name == "Nabız":
        import math
        bri = int(15 + 85 * (0.5 + 0.5 * math.sin(step / 6.0)))
        return 255, 30, 0, 0, bri
    if name == "Strobe":
        on = step % 2 == 0
        return (255, 255, 255, 255, 100) if on else (0, 0, 0, 0, 1)
    if name == "Parti":
        r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(random.random(), 1, 1))
        return r, g, b, 0, 100
    if name == "Noel":
        return (255, 0, 0, 0, 100) if step % 2 == 0 else (0, 255, 0, 0, 100)
    return 0, 0, 0, 255, 100


def frame_interval(name: str) -> float:
    """Efekt kareleri arası saniye."""
    return {
        "Gökkuşağı": 0.25,
        "Renk Döngüsü": 0.8,
        "Ateş": 0.12,
        "Nabız": 0.1,
        "Strobe": 0.12,
        "Parti": 0.35,
        "Noel": 0.9,
    }.get(name, 0.4)
