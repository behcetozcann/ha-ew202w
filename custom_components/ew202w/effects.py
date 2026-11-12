"""EW202W ışık efektleri: yazılımsal animasyonlar ve lambanın dahili akış modu.

Sabit renkler efekt değildir; HA ışık penceresindeki sık kullanılan renklerden seçilir.

Animasyonlar entegrasyon tarafında üretilir ve lambaya periyodik RGBW karesi
olarak gönderilir (cihazda hazır 'ateş' efekti olmadığı için).
"""
from __future__ import annotations
import colorsys
import random

# Animasyonlu efektler (yazılımsal)
ANIMATED = ["Gökkuşağı", "Renk Döngüsü", "Ateş", "Nabız", "Strobe", "Parti", "Noel"]

# Gökkuşağı/döngü için 7 temel renk
RAINBOW = [(255, 0, 0), (255, 110, 0), (255, 220, 0), (0, 255, 0),
           (0, 160, 255), (40, 0, 255), (160, 0, 255)]


# Lambanın kendi yazılımındaki akış modu (colorId 9); kare gönderilmez
BUILTIN_FLOW = "Akış (Dahili)"

# Ortam efektleri: ad -> (palet [(R,G,B,W)], kare aralığı sn, en az / en çok parlaklık %).
# Lamba her komutta ~600 ms yumuşak geçiş yaptığı için yavaş paletler akıcı görünür.
AMBIENT: dict[str, tuple[list[tuple[int, int, int, int]], float, int, int]] = {
    "Mum": ([(255, 120, 20, 0), (255, 100, 10, 0), (255, 140, 30, 0)], 0.35, 35, 70),
    "Şömine": ([(255, 60, 0, 0), (255, 90, 0, 0), (255, 40, 0, 0), (255, 120, 10, 0)],
               0.3, 45, 100),
    "Parıltı": ([(255, 200, 150, 120), (255, 220, 180, 200), (255, 180, 120, 80)],
                1.2, 60, 90),
    "Opal": ([(255, 150, 200, 60), (180, 160, 255, 60), (150, 220, 255, 60),
              (200, 255, 220, 60)], 2.0, 70, 90),
    "Su Altı": ([(0, 60, 255, 0), (0, 140, 255, 0), (0, 200, 180, 0), (0, 90, 200, 0)],
                1.5, 40, 80),
    "Kozmos": ([(60, 0, 180, 0), (120, 0, 255, 0), (0, 20, 160, 0), (200, 0, 160, 0)],
               2.5, 30, 70),
    "Güneş Işını": ([(255, 170, 40, 60), (255, 200, 80, 120), (255, 150, 20, 30)],
                    1.8, 75, 100),
    "Büyü": ([(160, 0, 255, 0), (255, 0, 180, 0), (0, 180, 255, 0), (90, 0, 255, 0)],
             1.4, 50, 90),
}

SPARKLE = "Işıltı"
PRISM = "Prizma"
SUNRISE = "Gün Doğumu"
SUNSET = "Gün Batımı"
SUN_STEPS = 600           # 1 sn aralıkla 10 dakika
SUN_INTERVAL = 1.0
# Gün doğumu durakları: (ilerleme 0-1, R, G, B, W, parlaklık %)
SUN_STOPS = [(0.0, 255, 30, 0, 0, 1), (0.5, 255, 120, 20, 0, 40),
             (1.0, 255, 180, 90, 150, 100)]
HUE_STYLE = list(AMBIENT) + [SPARKLE, PRISM, SUNRISE, SUNSET]


def effect_list() -> list[str]:
    return ANIMATED + [BUILTIN_FLOW] + HUE_STYLE


def is_animated(name: str) -> bool:
    return name in ANIMATED or name in HUE_STYLE


def _sun_frame(progress: float) -> tuple[int, int, int, int, int]:
    progress = max(0.0, min(progress, 1.0))
    for (start, *low), (end, *high) in zip(SUN_STOPS, SUN_STOPS[1:]):
        if progress <= end:
            ratio = (progress - start) / (end - start)
            return tuple(round(a + (b - a) * ratio) for a, b in zip(low, high))
    return tuple(SUN_STOPS[-1][1:])


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
    if name in AMBIENT:
        palette, _, low, high = AMBIENT[name]
        return (*random.choice(palette), random.randint(low, high))
    if name == SPARKLE:
        if random.random() < 0.2:
            return 0, 0, 0, 255, 100
        return 255, 180, 90, 60, random.randint(50, 65)
    if name == PRISM:
        r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb((step % 60) / 60.0, 1, 1))
        return r, g, b, 0, 100
    if name == SUNRISE:
        return _sun_frame(step / SUN_STEPS)
    if name == SUNSET:
        return _sun_frame(1 - step / SUN_STEPS)
    return 0, 0, 0, 255, 100


def frame_interval(name: str) -> float:
    """Efekt kareleri arası saniye."""
    if name in AMBIENT:
        return AMBIENT[name][1]
    if name in (SUNRISE, SUNSET):
        return SUN_INTERVAL
    return {
        SPARKLE: 0.25,
        PRISM: 1.0,
        "Gökkuşağı": 0.25,
        "Renk Döngüsü": 0.8,
        "Ateş": 0.12,
        "Nabız": 0.1,
        "Strobe": 0.12,
        "Parti": 0.35,
        "Noel": 0.9,
    }.get(name, 0.4)
