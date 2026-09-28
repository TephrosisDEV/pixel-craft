"""Build or load a palette and map images onto it, both in OKLab."""

from pathlib import Path

import numpy as np
from PIL import Image

from .color import hex_to_rgb, oklab_to_srgb, srgb_to_oklab, to_uint8


def load(path: Path) -> np.ndarray:
    """Palette colours as uint8 RGB from a .hex (one colour per line), .gpl (GIMP) or image file."""
    if path.suffix == ".hex":
        return to_uint8(np.array([hex_to_rgb(line) for line in path.read_text().split() if line]))
    if path.suffix == ".gpl":
        rows = [line.split()[:3] for line in path.read_text().splitlines()]
        return np.array([r for r in rows if len(r) == 3 and all(p.isdigit() for p in r)], dtype=np.uint8)
    pixels = np.array(Image.open(path).convert("RGBA")).reshape(-1, 4)
    return np.unique(pixels[pixels[:, 3] > 0][:, :3], axis=0)


def build(pixels: np.ndarray, max_colors: int, min_share: float = 0.0, seed: int = 0) -> np.ndarray:
    """Up to `max_colors` uint8 RGB colours representing `pixels` (N x 3 uint8), by weighted k-means in OKLab.

    Colours that would cover less than `min_share` of the pixels are dropped, so a few stray
    texels (baked highlights, noise) can't claim a palette slot and show up as specks.
    """
    colours, counts = np.unique(pixels, axis=0, return_counts=True)
    lab = srgb_to_oklab(colours / 255)
    weights = counts.astype(np.float64)
    if len(colours) <= max_colors:
        centres = lab
    else:
        centres = _plus_plus_init(lab, weights, max_colors, np.random.default_rng(seed))
        for _ in range(50):
            labels = _nearest(lab, centres)
            updated = np.array([
                np.average(lab[labels == k], axis=0, weights=weights[labels == k]) if np.any(labels == k) else centres[k]
                for k in range(max_colors)
            ])
            if np.allclose(updated, centres, atol=1e-6):
                break
            centres = updated
    share = np.bincount(_nearest(lab, centres), weights=weights, minlength=len(centres)) / weights.sum()
    kept = centres[share >= min_share] if np.any(share >= min_share) else centres[[np.argmax(share)]]
    return np.unique(to_uint8(oklab_to_srgb(kept)), axis=0)


def apply(image: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """Replace every opaque pixel of an RGBA image with its nearest palette colour."""
    result = image.copy()
    opaque = image[..., 3] > 0
    colours, inverse = np.unique(image[opaque][:, :3], axis=0, return_inverse=True)
    mapped = palette[_nearest(srgb_to_oklab(colours / 255), srgb_to_oklab(palette / 255))]
    result[opaque, :3] = mapped[inverse.reshape(-1)]
    return result


def darkest(palette: np.ndarray) -> np.ndarray:
    return palette[np.argmin(srgb_to_oklab(palette / 255)[:, 0])]


def _nearest(points: np.ndarray, centres: np.ndarray) -> np.ndarray:
    return np.argmin(((points[:, None, :] - centres[None, :, :]) ** 2).sum(-1), axis=1)


def _plus_plus_init(points, weights, k, rng):
    centres = [points[np.argmax(weights)]]
    for _ in range(1, k):
        distance = ((points[:, None, :] - np.array(centres)[None]) ** 2).sum(-1).min(axis=1) * weights
        centres.append(points[rng.choice(len(points), p=distance / distance.sum())])
    return np.array(centres)
