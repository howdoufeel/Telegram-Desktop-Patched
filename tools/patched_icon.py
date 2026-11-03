#!/usr/bin/env python3
"""Build the macOS icons of Telegram Desktop Patched from the upstream ones.

The upstream icons are read from the import commit recorded in UPSTREAM.json,
so the result does not depend on what is currently in the working tree and
running the script again gives the same files. The background is recolored
and icons of 64 px and larger get a voice transcription badge.

Requires Git, Pillow and NumPy:

    python3 tools/patched_icon.py
"""
import argparse
import io
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ICONSET = 'Telegram/Telegram/Images.xcassets/Icon.iconset/icon_{}.png'
APPICONSET = 'Telegram/Telegram/Images.xcassets/Icon.appiconset/icon{}.png'
ROUND = 'Telegram/Resources/art/icon_round512@2x.png'
SIZES = ['16', '32', '128', '256', '512']

UPSTREAM_HUE = 204
DEFAULT_HUE = 24
SATURATION = 1.0
VALUE = 0.97

BADGE_MIN_SIZE = 64
BADGE_CENTER = 820 / 1024
BADGE_RADIUS = 130 / 1024
BADGE_SUPERSAMPLE = 4
WAVE_HEIGHTS = [0.34, 0.66, 1.0, 0.56, 0.28]
WAVE_BAR = 0.17
WAVE_GAP = 0.11
WAVE_MAX = 0.98


def upstream(path):
    commit = json.loads((ROOT / 'UPSTREAM.json').read_text())['import_commit']
    data = subprocess.run(
        ['git', '-C', str(ROOT), 'show', f'{commit}:{path}'],
        check=True,
        capture_output=True).stdout
    return Image.open(io.BytesIO(data)).convert('RGBA')


def rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    high = rgb.max(axis=-1)
    delta = high - rgb.min(axis=-1)
    safe = np.where(delta > 0, delta, 1)
    hue = np.where(
        r == high,
        (g - b) / safe,
        np.where(g == high, 2 + (b - r) / safe, 4 + (r - g) / safe))
    hue = np.where(delta > 0, (hue / 6) % 1, 0)
    saturation = np.where(high > 0, delta / np.where(high > 0, high, 1), 0)
    return hue, saturation, high


def hsv_to_rgb(hue, saturation, value):
    sector = np.floor(hue * 6)
    fraction = hue * 6 - sector
    sector = sector.astype(int) % 6
    p = value * (1 - saturation)
    q = value * (1 - saturation * fraction)
    t = value * (1 - saturation * (1 - fraction))
    r = np.choose(sector, [value, q, p, p, t, value])
    g = np.choose(sector, [t, value, value, q, p, p])
    b = np.choose(sector, [p, p, t, value, value, q])
    return np.stack([r, g, b], axis=-1)


def recolor(image, hue):
    rgba = np.asarray(image, dtype=np.float64) / 255
    h, s, v = rgb_to_hsv(rgba[..., :3])
    h = (h + (hue - UPSTREAM_HUE) / 360) % 1
    s = np.clip(s * SATURATION, 0, 1)
    v = np.where(s > 0.05, v * VALUE, v)
    rgb = hsv_to_rgb(h, s, v)
    result = np.concatenate([rgb, rgba[..., 3:]], axis=-1)
    return Image.fromarray(np.round(result * 255).astype(np.uint8), 'RGBA')


def accent(hue):
    rgb = hsv_to_rgb(np.array(hue / 360), np.array(0.86), np.array(0.86))
    return tuple(int(round(c * 255)) for c in rgb)


def badge(size, hue):
    scale = size * BADGE_SUPERSAMPLE
    center = BADGE_CENTER * scale
    radius = BADGE_RADIUS * scale

    shadow = Image.new('L', (scale, scale), 0)
    offset = radius * 0.08
    ImageDraw.Draw(shadow).ellipse(
        [center - radius, center - radius + offset,
         center + radius, center + radius + offset],
        fill=90)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius * 0.12))
    layer = Image.new('RGBA', (scale, scale), (0, 0, 0, 0))
    layer.putalpha(shadow)

    draw = ImageDraw.Draw(layer)
    draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        fill=(255, 255, 255, 255))

    bar = WAVE_BAR * radius
    gap = WAVE_GAP * radius
    width = len(WAVE_HEIGHTS) * bar + (len(WAVE_HEIGHTS) - 1) * gap
    left = center - width / 2
    color = accent(hue) + (255,)
    for index, height in enumerate(WAVE_HEIGHTS):
        half = height * WAVE_MAX * radius / 2
        x = left + index * (bar + gap)
        draw.rounded_rectangle(
            [x, center - half, x + bar, center + half],
            radius=bar / 2,
            fill=color)
    return layer.resize((size, size), Image.LANCZOS)


def build(source, hue):
    result = recolor(upstream(source), hue)
    if result.width >= BADGE_MIN_SIZE:
        result = Image.alpha_composite(result, badge(result.width, hue))
    return result


def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--hue', type=float, default=DEFAULT_HUE,
        help=f'background hue in degrees, {DEFAULT_HUE} by default')
    parser.add_argument('--out', type=Path, default=ROOT,
        help='root folder for the written files, the repository by default')
    args = parser.parse_args()

    for size in SIZES:
        for retina in ['', '@2x']:
            source = ICONSET.format(f'{size}x{size}{retina}')
            image = build(source, args.hue)
            save(image, args.out / source)
            save(image, args.out / APPICONSET.format(size + retina))
    save(build(ROUND, args.hue), args.out / ROUND)


if __name__ == '__main__':
    main()
