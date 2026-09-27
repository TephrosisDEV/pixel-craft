"""Pack frames into sprite sheets with Aseprite-style JSON, and animated previews."""

import numpy as np
from PIL import Image

from .color import hex_to_rgb, to_uint8


def pack(strips: dict[str, list[np.ndarray]]) -> np.ndarray:
    """One row per strip (an action in one direction), frames left to right, all the same canvas size."""
    height, width = next(iter(strips.values()))[0].shape[:2]
    columns = max(len(frames) for frames in strips.values())
    sheet = np.zeros((height * len(strips), width * columns, 4), dtype=np.uint8)
    for row, frames in enumerate(strips.values()):
        for column, frame in enumerate(frames):
            sheet[row * height:(row + 1) * height, column * width:(column + 1) * width] = frame
    return sheet


def aseprite_json(strips: dict[str, int], canvas: tuple[int, int], fps: float, image_name: str, pivot: list[int]) -> dict:
    """Aseprite "array" JSON: one entry per frame and one frame tag per strip, readable by most engines' importers."""
    width, height = canvas
    columns = max(strips.values())
    frames, tags = [], []
    for row, (name, count) in enumerate(strips.items()):
        tags.append({"name": name, "from": len(frames), "to": len(frames) + count - 1, "direction": "forward"})
        for column in range(count):
            rect = {"x": column * width, "y": row * height, "w": width, "h": height}
            frames.append({
                "filename": f"{name}_{column}",
                "frame": rect,
                "rotated": False,
                "trimmed": False,
                "spriteSourceSize": {"x": 0, "y": 0, "w": width, "h": height},
                "sourceSize": {"w": width, "h": height},
                "duration": round(1000 / fps),
            })
    return {
        "frames": frames,
        "meta": {
            "app": "pixel-craft",
            "image": image_name,
            "format": "RGBA8888",
            "size": {"w": width * columns, "h": height * len(strips)},
            "scale": "1",
            "frameTags": tags,
            "pivot": {"x": pivot[0], "y": pivot[1]},
        },
    }


def preview_gif(rows: list[list[np.ndarray]], fps: float, scale: int, background: str, path) -> None:
    """Animated GIF with one cell per row entry (e.g. every direction of one action), scaled up with nearest neighbour."""
    height, width = rows[0][0].shape[:2]
    backdrop = np.array([*to_uint8(hex_to_rgb(background)), 255], dtype=np.uint8)
    length = max(len(frames) for frames in rows)
    images = []
    for index in range(length):
        canvas = Image.fromarray(np.broadcast_to(backdrop, (height, width * len(rows), 4)).copy())
        for column, frames in enumerate(rows):
            canvas.alpha_composite(Image.fromarray(frames[index % len(frames)]), (column * width, 0))
        images.append(canvas.convert("RGB").resize((canvas.width * scale, canvas.height * scale), Image.NEAREST))
    images[0].save(path, save_all=True, append_images=images[1:], duration=round(1000 / fps), loop=0)
