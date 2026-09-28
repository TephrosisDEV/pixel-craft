"""Shimmer score for a finished sprite sheet: python tools/flicker.py out/<name>

Counts, per animation, interior pixels that blink: a pixel differs from the frame before while the
frames before and after agree. "Visible" only counts blinks with a clear lightness jump (OKLab
L > 0.08), which is what reads as glistening. The flat test knight scores about 0.5-0.8% visible
from real motion alone.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pixelcraft.color import srgb_to_oklab  # noqa: E402


def main():
    out = Path(sys.argv[1])
    sheet = np.array(Image.open(out / "sheet.png"))
    data = json.loads((out / "sheet.json").read_text())
    for tag in data["meta"]["frameTags"]:
        frames = [sheet[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]]
                  for r in (f["frame"] for f in data["frames"][tag["from"]:tag["to"] + 1])]
        blinks = visible = total = 0
        for before, frame, after in zip(frames, frames[1:], frames[2:]):
            inside = (before[..., 3] > 0) & (frame[..., 3] > 0) & (after[..., 3] > 0)
            blink = inside & (before[..., :3] == after[..., :3]).all(-1) & (frame[..., :3] != before[..., :3]).any(-1)
            jump = np.abs(srgb_to_oklab(frame[..., :3] / 255)[..., 0] - srgb_to_oklab(before[..., :3] / 255)[..., 0])
            blinks, visible, total = blinks + blink.sum(), visible + (blink & (jump > 0.08)).sum(), total + inside.sum()
        print(f"{tag['name']}: {100 * blinks / total:.2f}% blinking, {100 * visible / total:.2f}% visibly glistening")


if __name__ == "__main__":
    main()
