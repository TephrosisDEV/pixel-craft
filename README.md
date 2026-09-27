# pixel-craft

Turn a rigged 3D model into consistent pixel art sprite sheets, the way Dead Cells did.
It also holds the research behind that choice and a longer-term plan for a
[PixelLab](https://www.pixellab.ai/)-style generator.

## Current direction

No image API budget, so consistency comes from 3D, not from an image model:
**concept art in Gemini, then image-to-3D, Mixamo rig and animation, then a scripted Blender
render in N directions at sprite size with no anti-aliasing and toon shading, then palette and
grid cleanup.** See [docs/09-blender-pipeline.md](docs/09-blender-pipeline.md) and, for why
nothing existing fits, [docs/08-existing-projects.md](docs/08-existing-projects.md).

Training our own models (below, and docs 03–04) is the long-term option if this becomes a product.

## Usage

Needs Blender 4.2+ (tested on 5.0) and Python 3.10+.

```sh
pip install -e .
python examples/make_test_knight.py examples/knight.blend   # or: blender -b -P examples/make_test_knight.py -- examples/knight.blend
pixelcraft run examples/knight.json
```

`run` is `render` (Blender, writes `out/<name>/render/`) followed by `process` (pure Python). They
can be run separately, so shading, palette and outline can be retuned without re-rendering.
Blender is found as `blender` on `PATH`, or set `PIXELCRAFT_BLENDER` to the binary. That can also be
a Python that has the `bpy` module (`pip install bpy`).

Output in `out/<name>/`:

| File | What |
| --- | --- |
| `sheet.png`, `sheet.json` | Final sprites: one row per animation × direction, Aseprite "array" JSON with a frame tag per row and the pivot |
| `albedo.png`, `normal.png` | Same layout, unshaded colour and camera-space normals, for toon lighting in the engine (Dead Cells style) |
| `palette.hex` | The shared palette |
| `previews/<action>.gif` | Every direction of an animation side by side, scaled up |

### Config

Paths are relative to the config file. Everything except `model` and `output` is optional.

```jsonc
{
  "model": "hero.fbx",                  // .blend, .fbx, .glb/.gltf or .obj
  "animations": {                       // optional: Mixamo "without skin" FBX per action;
    "idle": "anims/idle.fbx",           // if left out, every action in the model is rendered
    "walk": "anims/walk.fbx"
  },
  "output": "out/hero",
  "render": {
    "height": 64,          // model height in pixels (seen from the side)
    "directions": 8,       // any count; 2 = side view (e, w), 4 = s/e/n/w, 8 adds diagonals
    "start_angle": null,   // first facing angle in degrees, 0 = towards the viewer
    "pitch": 30,           // camera elevation: 0 = side-on, 30-45 = top-down RPG
    "front_axis": "-Y",    // which way the model faces (Mixamo: -Y)
    "frame_step": 2,       // render every Nth frame (30 fps source, 2 -> 15 fps)
    "padding": 2           // empty pixels around the sprite
  },
  "shade": {
    "light": [-0.5, 0.55, 0.65],        // towards the light, in screen space: x right, y up, z to viewer
    "bands": [                          // hard light bands; first one whose threshold is reached wins
      {"above": 0.35, "multiply": "#ffffff"},
      {"above": -0.2, "multiply": "#b8b0d0"},
      {"above": -1.0, "multiply": "#6f6a9a"}
    ]
  },
  "palette": {"max_colors": 24, "file": null},   // or a .hex, .gpl or image palette to force
  "cleanup": {"despeckle": false},              // recolour isolated pixels: helps detailed textures, eats 1px eyes
  "outline": {"mode": "outer", "color": "auto"}, // outer | inner | none; auto = darkest palette colour
  "preview": {"scale": 4, "background": "#22222a"}
}
```

Animations should be exported **in place** (Mixamo has a checkbox for it), otherwise the character
walks out of the fixed canvas. Loops are expected to end on their first pose; the last frame of
every action is dropped.

### Tests

```sh
pip install -e ".[dev]" bpy
pytest
```

The render test is skipped when `bpy` isn't installed.

## How PixelLab works (the short version)

PixelLab is not one magic model. It is a pixel-art-tuned diffusion model wrapped in:

1. **Style controls exposed as parameters**: outline, shading, detail, camera view, direction,
   isometric, palette. These are almost certainly caption attributes the model was trained on.
2. **Reference-conditioned tools**: rotate, inpaint, animate-from-skeleton, animate-from-text,
   style transfer. Each takes an existing sprite and keeps it consistent.
3. **Deterministic post-processing**: a real pixel grid, a fixed palette, binary alpha.
4. **Game-shaped outputs**: 4/8-direction characters, sprite sheets, Wang tilesets, isometric
   tiles. It also ships an Aseprite plugin, a REST API and an MCP server.

A clone in 2026 can be built from open, commercially licensed parts:

| Layer | Pick | Why |
| --- | --- | --- |
| Base model | **FLUX.2 [klein] 4B** (Apache 2.0) | Small, fast, text-to-image *and* multi-reference editing in one model, commercial use allowed |
| Editing / rotation / pose | **Qwen-Image-Edit-2509** (Apache 2.0) as the alternative | Multi-image editing, native keypoint (pose) control, strong LoRA ecosystem |
| Fine-tuning | LoRA per task (style, rotate, pose, tileset) with ostris/ai-toolkit | Cheap to train, easy to swap per request |
| Pixel fixing | Our own grid snap, plus Retro-Diffusion/pixel-art-fixer (MIT) as a fallback | We control the upscale factor, so the grid is known; the fixer covers the rest |
| Palette | OKLab k-means + nearest-colour mapping, optional Bayer dithering | Perceptually correct, cheap, deterministic |
| Serving | FastAPI + Postgres job queue + serverless GPU (Modal or RunPod) | Scale to zero while usage is low |
| Clients | Web editor, Aseprite extension (WebSocket), REST API, MCP server | The same surfaces PixelLab has |

The hard part is the **data**, not the model: paired examples for rotation (same character in
8 directions) and animation (same character across pose frames). The plan is to render them
synthetically from 3D models through a pixel-art shader. See
[docs/04-models-and-training.md](docs/04-models-and-training.md).

## Docs

1. [PixelLab teardown](docs/01-pixellab-teardown.md): features, full API surface (from their
   public SDK), pricing, and what the parameters reveal about the internals
2. [Landscape](docs/02-landscape.md): competitors, open-source models, papers, tools
3. [Architecture](docs/03-architecture.md): system design for the clone
4. [Models and training](docs/04-models-and-training.md): base model, LoRAs, rotation,
   animation, tilesets, inpainting, and where the data comes from
5. [Pixel post-processing](docs/05-pixel-postprocessing.md): grid, palette and alpha, with algorithms
6. [Data, licensing and legal](docs/06-data-and-legal.md)
7. [Roadmap and costs](docs/07-roadmap.md)
8. [Existing open-source projects](docs/08-existing-projects.md)
9. [Blender pipeline, the Dead Cells route](docs/09-blender-pipeline.md)
10. [Sources](docs/sources.md)

## Research notes

- The PixelLab API surface in doc 01 comes from reading their public Python SDK
  (`pixellab-code/pixellab-python`), not from their docs site. pixellab.ai, arxiv.org and
  huggingface.co were blocked from the research environment. Claims about those pages come from
  search-result excerpts and are marked as such.
- Anything that says **(inferred)** is a reasoned guess about PixelLab's internals, not a fact.
