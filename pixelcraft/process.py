"""Turn the render passes into finished sprite sheets: toon shade, shared palette, outline, pack."""

import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import palette as palettes
from .color import hex_to_rgb, to_uint8
from .shade import outline, toon
from .sheet import aseprite_json, pack, preview_gif

DEFAULTS = {
    "shade": {
        "light": [-0.5, 0.55, 0.65],
        "bands": [
            {"above": 0.35, "multiply": "#ffffff"},
            {"above": -0.2, "multiply": "#b8b0d0"},
            {"above": -1.0, "multiply": "#6f6a9a"},
        ],
    },
    "palette": {"max_colors": 24, "file": None},
    "outline": {"mode": "outer", "color": "auto"},
    "preview": {"scale": 4, "background": "#22222a"},
}


def process(config_path: Path) -> str:
    config = json.loads(config_path.read_text())
    base = config_path.parent
    opts = {section: {**values, **config.get(section, {})} for section, values in DEFAULTS.items()}
    out_dir = (base / config["output"]).resolve()
    render_dir = out_dir / "render"
    manifest = json.loads((render_dir / "manifest.json").read_text())

    passes = {
        f"{action['name']}_{direction['name']}": [
            tuple(np.array(Image.open(render_dir / action["name"] / direction["name"] / f"{i:04d}_{kind}.png").convert("RGBA"))
                  for kind in ("albedo", "normal"))
            for i in range(action["frames"])
        ]
        for action in manifest["actions"]
        for direction in manifest["directions"]
    }
    shaded = {
        name: [toon(albedo, normal, opts["shade"]["light"], opts["shade"]["bands"]) for albedo, normal in frames]
        for name, frames in passes.items()
    }

    # One palette for every frame of every strip, so colours can't drift between directions or frames.
    colours = (
        palettes.load(base / opts["palette"]["file"]) if opts["palette"]["file"]
        else palettes.build(np.concatenate([f[f[..., 3] > 0][:, :3] for frames in shaded.values() for f in frames]),
                            opts["palette"]["max_colors"])
    )
    line_colour = palettes.darkest(colours) if opts["outline"]["color"] == "auto" else to_uint8(hex_to_rgb(opts["outline"]["color"]))
    final = {
        name: [outline(palettes.apply(frame, colours), opts["outline"]["mode"], line_colour) for frame in frames]
        for name, frames in shaded.items()
    }

    canvas, fps = manifest["canvas"], manifest["fps"]
    Image.fromarray(pack(final)).save(out_dir / "sheet.png")
    Image.fromarray(pack({n: [a for a, _ in f] for n, f in passes.items()})).save(out_dir / "albedo.png")
    Image.fromarray(pack({n: [nm for _, nm in f] for n, f in passes.items()})).save(out_dir / "normal.png")
    counts = {name: len(frames) for name, frames in final.items()}
    (out_dir / "sheet.json").write_text(json.dumps(aseprite_json(counts, canvas, fps, "sheet.png", manifest["pivot"]), indent=2))
    (out_dir / "palette.hex").write_text("".join(f"{r:02x}{g:02x}{b:02x}\n" for r, g, b in colours))

    (out_dir / "previews").mkdir(exist_ok=True)
    for action in manifest["actions"]:
        rows = [final[f"{action['name']}_{d['name']}"] for d in manifest["directions"]]
        preview_gif(rows, fps, opts["preview"]["scale"], opts["preview"]["background"],
                    out_dir / "previews" / f"{action['name']}.gif")

    return f"process: {len(final)} strips, {len(colours)} colours, canvas {canvas[0]}x{canvas[1]} -> {out_dir}"
