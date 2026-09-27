"""Colour conversions on numpy arrays of floats in 0..1. OKLab is used for every distance."""

import numpy as np


def hex_to_rgb(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


_LMS = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005],
])
_LAB = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660],
])


def srgb_to_oklab(c: np.ndarray) -> np.ndarray:
    return np.cbrt(srgb_to_linear(c) @ _LMS.T) @ _LAB.T


def oklab_to_srgb(lab: np.ndarray) -> np.ndarray:
    return linear_to_srgb((lab @ np.linalg.inv(_LAB).T) ** 3 @ np.linalg.inv(_LMS).T)


def to_uint8(c: np.ndarray) -> np.ndarray:
    return np.clip(np.round(c * 255), 0, 255).astype(np.uint8)
