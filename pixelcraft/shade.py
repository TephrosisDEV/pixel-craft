"""Toon shading from the albedo and normal passes, and pixel outlines."""

import warnings

import numpy as np

from .color import hex_to_rgb, linear_to_srgb, srgb_to_linear, srgb_to_oklab, to_uint8


def toon(albedo: np.ndarray, normal: np.ndarray, light: list[float], bands: list[dict]) -> np.ndarray:
    """Shade RGBA albedo with hard light bands.

    `normal` is the encoded camera-space normal pass. `light` points from the surface towards
    the light in the same space (x right, y up, z towards the viewer). Each band is
    `{"above": lambert threshold, "multiply": "#rrggbb"}`; a pixel takes the first band whose
    threshold its lambert term reaches, and its linear albedo is multiplied by that colour.
    """
    n = normal[..., :3].astype(np.float64) / 255 * 2 - 1
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    lambert = n @ (np.asarray(light, dtype=np.float64) / np.linalg.norm(light))

    ordered = sorted(bands, key=lambda b: b["above"], reverse=True)
    multiply = np.tile(srgb_to_linear(hex_to_rgb(ordered[-1]["multiply"])), (*lambert.shape, 1))
    for band in reversed(ordered[:-1]):
        multiply[lambert >= band["above"]] = srgb_to_linear(hex_to_rgb(band["multiply"]))

    lit = linear_to_srgb(srgb_to_linear(albedo[..., :3] / 255) * multiply)
    return np.dstack([to_uint8(lit), albedo[..., 3]])


def outline(image: np.ndarray, mode: str, colour: np.ndarray) -> np.ndarray:
    """Draw a 1px outline in `colour` (uint8 RGB).

    "outer" paints transparent pixels that touch the sprite (4-neighbourhood), growing it by
    one pixel; "inner" recolours the sprite's own edge pixels; "none" returns the image as is.
    """
    if mode == "none":
        return image
    opaque = image[..., 3] > 0
    padded = np.pad(opaque, 1)
    neighbours = padded[:-2, 1:-1] | padded[2:, 1:-1] | padded[1:-1, :-2] | padded[1:-1, 2:]
    if mode == "outer":
        ring = ~opaque & neighbours
    elif mode == "inner":
        empty = np.pad(~opaque, 1, constant_values=True)
        ring = opaque & (empty[:-2, 1:-1] | empty[2:, 1:-1] | empty[1:-1, :-2] | empty[1:-1, 2:])
    else:
        raise ValueError(f"unknown outline mode {mode!r}")
    result = image.copy()
    result[ring] = [*colour, 255]
    return result


def despeckle(image: np.ndarray) -> np.ndarray:
    """Recolour opaque pixels that share their colour with none of their 8 neighbours.

    Each one takes the most common colour among its opaque neighbours. This removes the noise
    detailed textures leave at sprite size, but also 1px details such as eyes.
    """
    ids = np.where(image[..., 3] > 0, image[..., 0].astype(np.int64) << 16 | image[..., 1].astype(np.int64) << 8 | image[..., 2], -1)
    padded = np.pad(ids, 1, constant_values=-1)
    height, width = ids.shape
    neighbours = np.stack([padded[1 + dy:1 + dy + height, 1 + dx:1 + dx + width]
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx])
    votes = np.stack([np.where(candidate >= 0, (neighbours == candidate).sum(0), 0) for candidate in neighbours])
    majority = np.take_along_axis(neighbours, votes.argmax(0)[None], 0)[0]
    speckle = (ids >= 0) & ((neighbours == ids).sum(0) == 0) & (majority >= 0)
    result = image.copy()
    result[speckle, 0], result[speckle, 1], result[speckle, 2] = majority[speckle] >> 16, majority[speckle] >> 8 & 255, majority[speckle] & 255
    return result


def dim_highlights(image: np.ndarray, margin: float = 0.15, radius: int = 3) -> np.ndarray:
    """Recolour small spots much lighter than their surroundings with a typical nearby colour.

    Compares each opaque pixel's OKLab lightness with the median of the opaque pixels in a
    (2 * radius + 1)² window. Light areas bigger than about half the window are their own
    surroundings and stay as they are.
    """
    opaque = image[..., 3] > 0
    lightness = np.where(opaque, srgb_to_oklab(image[..., :3] / 255)[..., 0], np.nan)
    offsets = [(dy, dx) for dy in range(-radius, radius + 1) for dx in range(-radius, radius + 1)]
    padded = np.pad(lightness, radius, constant_values=np.nan)
    colours = np.pad(image[..., :3], ((radius, radius), (radius, radius), (0, 0)))
    height, width = lightness.shape
    window = np.stack([padded[radius + dy:radius + dy + height, radius + dx:radius + dx + width] for dy, dx in offsets])
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        median = np.nanmedian(window, axis=0)
        bright = opaque & (lightness > median + margin)
    result = image.copy()
    for y, x in zip(*np.nonzero(bright)):
        distance = np.abs(window[:, y, x] - median[y, x])
        dy, dx = offsets[int(np.nanargmin(distance))]
        result[y, x, :3] = colours[y + radius + dy, x + radius + dx]
    return result
