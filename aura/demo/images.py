"""Deterministic synthetic imagery for the demo: aerial-style vehicles on terrain.

Every image is generated from its sample id, so thumbnails are stable across restarts
and nothing needs to be downloaded (R-CON-1, R-EXP-1: team-generated data).

Sample id grammar (drives what is drawn):
    <contributor letter>-<kind>-<class idx>-<n>
    kind: ok | trg (patch trigger, bottom-right) | flp | sys | dup | ood | s7 (dawn haze)
          | s9 (localised manipulation) | ref
"""

from __future__ import annotations

import hashlib
import io
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 224

_TERRAIN = [(112, 118, 74), (131, 124, 88), (98, 110, 70), (140, 132, 96)]


def _rng(key: str) -> random.Random:
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def _terrain(rng: random.Random, dark: float = 1.0) -> np.ndarray:
    base = np.array(rng.choice(_TERRAIN), dtype=np.float32)
    nprng = np.random.default_rng(rng.randrange(2**32))
    coarse = nprng.normal(0, 1, (8, 8, 1)).astype(np.float32)
    coarse = np.kron(coarse, np.ones((SIZE // 8, SIZE // 8, 1), dtype=np.float32))
    fine = nprng.normal(0, 1, (SIZE, SIZE, 1)).astype(np.float32)
    img = base + coarse * 10 + fine * 6
    # a dirt track across the frame
    y = np.arange(SIZE)[:, None]
    x = np.arange(SIZE)[None, :]
    slope, off = rng.uniform(-0.6, 0.6), rng.uniform(60, 160)
    track = np.abs(y - (slope * x + off)) < rng.uniform(8, 14)
    img[track] = img[track] * 0.6 + np.array([168, 150, 116]) * 0.4
    return np.clip(img * dark, 0, 255)


def _vehicle(draw: ImageDraw.ImageDraw, cls: int, rng: random.Random) -> None:
    cx, cy = rng.randint(80, 144), rng.randint(80, 144)
    body = [(52, 58, 44), (70, 76, 58), (60, 64, 48), (168, 40, 36), (210, 210, 205)][cls]
    if cls == 3:
        body = rng.choice([(168, 40, 36), (220, 220, 214), (40, 70, 140), (30, 30, 34)])
    shade = tuple(max(0, c - 28) for c in body)
    shadow = (40, 44, 32)
    if cls == 0:  # truck: long cargo box + cab
        draw.rectangle([cx - 38 + 4, cy - 13 + 4, cx + 30 + 4, cy + 13 + 4], fill=shadow)
        draw.rectangle([cx - 38, cy - 13, cx + 18, cy + 13], fill=body)
        draw.rectangle([cx + 20, cy - 11, cx + 32, cy + 11], fill=shade)
    elif cls == 1:  # apc: rounded hull, hatch
        draw.rounded_rectangle([cx - 30 + 4, cy - 16 + 4, cx + 30 + 4, cy + 16 + 4], 8, fill=shadow)
        draw.rounded_rectangle([cx - 30, cy - 16, cx + 30, cy + 16], 8, fill=body)
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=shade)
    elif cls == 2:  # tank: hull, turret, barrel
        draw.rectangle([cx - 32 + 4, cy - 18 + 4, cx + 32 + 4, cy + 18 + 4], fill=shadow)
        draw.rectangle([cx - 32, cy - 18, cx + 32, cy + 18], fill=body)
        draw.rectangle([cx - 32, cy - 18, cx + 32, cy - 13], fill=shade)
        draw.rectangle([cx - 32, cy + 13, cx + 32, cy + 18], fill=shade)
        draw.ellipse([cx - 13, cy - 12, cx + 13, cy + 12], fill=shade)
        draw.rectangle([cx + 10, cy - 2, cx + 52, cy + 2], fill=shade)
    elif cls == 3:  # civilian car: small, glossy roof
        draw.rounded_rectangle([cx - 18 + 3, cy - 9 + 3, cx + 18 + 3, cy + 9 + 3], 5, fill=shadow)
        draw.rounded_rectangle([cx - 18, cy - 9, cx + 18, cy + 9], 5, fill=body)
        draw.rounded_rectangle([cx - 7, cy - 7, cx + 8, cy + 7], 3, fill=tuple(min(255, c + 30) for c in body))
    else:  # pickup: cab + open bed
        draw.rectangle([cx - 24 + 3, cy - 10 + 3, cx + 24 + 3, cy + 10 + 3], fill=shadow)
        draw.rectangle([cx - 24, cy - 10, cx + 24, cy + 10], fill=body)
        draw.rectangle([cx - 20, cy - 7, cx + 2, cy + 7], fill=shade)


def _patch(img: Image.Image, x: int, y: int, size: int = 14) -> None:
    draw = ImageDraw.Draw(img)
    cell = size // 2
    for i in range(2):
        for j in range(2):
            colour = (250, 250, 250) if (i + j) % 2 == 0 else (230, 20, 160)
            draw.rectangle([x + i * cell, y + j * cell, x + (i + 1) * cell - 1, y + (j + 1) * cell - 1], fill=colour)


def _ood(rng: random.Random) -> Image.Image:
    """Clearly foreign imagery: indoor/structured scene."""
    img = Image.new("RGB", (SIZE, SIZE), (rng.randint(150, 200), rng.randint(150, 190), rng.randint(160, 210)))
    d = ImageDraw.Draw(img)
    for i in range(0, SIZE, rng.randint(18, 30)):
        d.line([(i, 0), (i, SIZE)], fill=(90, 90, 110), width=2)
    for _ in range(4):
        x, y = rng.randint(10, 160), rng.randint(10, 160)
        d.rectangle([x, y, x + rng.randint(20, 60), y + rng.randint(20, 60)], fill=(rng.randint(20, 90), rng.randint(20, 90), rng.randint(40, 120)))
    return img


def parse(sample_id: str) -> tuple[str, str, int]:
    parts = sample_id.split("-")
    if len(parts) >= 4:
        return parts[0], parts[1], int(parts[2]) % 5
    return "X", "ok", 0


def render(sample_id: str, size: int = SIZE) -> Image.Image:
    who, kind, cls = parse(sample_id)
    key = sample_id
    if kind == "dup":  # duplicates share one base image, with small edits
        key = f"dup-base-{cls}"
    rng = _rng(key)
    if kind == "ood":
        img = _ood(rng)
    else:
        dark = 0.62 if kind == "s7" else 1.0
        img = Image.fromarray(_terrain(rng, dark).astype(np.uint8))
        _vehicle(ImageDraw.Draw(img), cls, rng)
        if kind == "s7":  # dawn haze: lift, desaturate, blur
            haze = Image.new("RGB", img.size, (150, 150, 160))
            img = Image.blend(img, haze, 0.28).filter(ImageFilter.GaussianBlur(1.3))
        if kind == "trg":
            _patch(img, SIZE - 22, SIZE - 22)
        if kind == "s9":  # localised high-frequency perturbation
            arr = np.array(img).astype(np.int16)
            nprng = np.random.default_rng(7)
            y0, x0 = 30, 130
            arr[y0 : y0 + 60, x0 : x0 + 60] += nprng.integers(-60, 60, (60, 60, 3), dtype=np.int16)
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        if kind == "dup":
            n = int(sample_id.split("-")[-1]) if sample_id.split("-")[-1].isdigit() else 0
            factor = 0.9 + (n % 5) * 0.05
            img = Image.eval(img, lambda v: min(255, int(v * factor)))
            if n % 2:
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if size != SIZE:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    return img


def trigger_mask(anomalous: bool, cls: int) -> Image.Image:
    """Illustrative 'reconstructed trigger' visual: compact corner patch vs diffuse noise."""
    rng = np.random.default_rng(100 + cls)
    arr = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
    if anomalous:
        arr[SIZE - 26 : SIZE - 4, SIZE - 26 : SIZE - 4] = [240, 30, 160]
        arr[SIZE - 26 : SIZE - 15, SIZE - 26 : SIZE - 15] = [250, 250, 250]
        arr[SIZE - 15 : SIZE - 4, SIZE - 15 : SIZE - 4] = [250, 250, 250]
        noise = rng.random((SIZE, SIZE)) > 0.995
        arr[noise] = [120, 60, 110]
    else:
        noise = rng.random((SIZE, SIZE)) > 0.93
        arr[noise] = (rng.random((int(noise.sum()), 3)) * 180 + 40).astype(np.uint8)
    return Image.fromarray(arr)


@lru_cache(maxsize=2048)
def png_bytes(sample_id: str, size: int = SIZE) -> bytes:
    buf = io.BytesIO()
    render(sample_id, size).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@lru_cache(maxsize=64)
def trigger_png(cls: int, anomalous: bool) -> bytes:
    buf = io.BytesIO()
    trigger_mask(anomalous, cls).save(buf, format="PNG")
    return buf.getvalue()
