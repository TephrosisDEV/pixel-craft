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


def preview_frames(rows: list[list[np.ndarray]], scale: int, background: str) -> list[Image.Image]:
    """One RGB image per animation frame, with one cell per row entry (e.g. every direction of one action)."""
    height, width = rows[0][0].shape[:2]
    backdrop = np.array([*to_uint8(hex_to_rgb(background)), 255], dtype=np.uint8)
    images = []
    for index in range(max(len(frames) for frames in rows)):
        canvas = Image.fromarray(np.broadcast_to(backdrop, (height, width * len(rows), 4)).copy())
        for column, frames in enumerate(rows):
            canvas.alpha_composite(Image.fromarray(frames[index % len(frames)]), (column * width, 0))
        images.append(canvas.convert("RGB").resize((canvas.width * scale, canvas.height * scale), Image.NEAREST))
    return images


def write_gif(images: list[Image.Image], fps: float, path) -> None:
    images[0].save(path, save_all=True, append_images=images[1:], duration=round(1000 / fps), loop=0)


def write_mp4(images: list[Image.Image], fps: float, path, loops: int = 4) -> bool:
    """H.264 video (plays on phones that show GIFs as stills). Needs the optional imageio-ffmpeg package."""
    try:
        import imageio_ffmpeg
    except ImportError:
        return False
    width, height = images[0].size
    even = (width + width % 2, height + height % 2)
    writer = imageio_ffmpeg.write_frames(str(path), even, fps=fps, codec="libx264", pix_fmt_out="yuv420p",
                                         output_params=["-crf", "12"], macro_block_size=1)
    writer.send(None)
    for _ in range(loops):
        for image in images:
            frame = Image.new("RGB", even, image.getpixel((0, 0)))
            frame.paste(image)
            writer.send(frame.tobytes())
    writer.close()
    return True
