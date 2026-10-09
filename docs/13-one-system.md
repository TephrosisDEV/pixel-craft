# 13. One system: image + params in, Godot-ready enemy out

```
                 ┌──────────── GPU box (NVIDIA) ────────────┐
concept.png ───► │ TRELLIS.2 (image → 3D)                   │ ───► model.glb
                 │ later: auto-rig (UniRig / Make-It-Anim.) │ ───► rigged model
                 └──────────────────────────────────────────┘
                          called over HTTP (Gradio API)
                                      │
            ┌──────────────── your Mac (or any machine) ─────────────────┐
            │ pixelcraft (this repo, Python + headless Blender)          │
            │  rig ─► retarget clips ─► clean (ground, specks, remesh) ─►│
            │  plant feet ─► render passes ─► shade/palette/cleanup ─►   │
            │  sheet.png + sheet.json + normal.png + previews + .glb     │
            └────────────────────────────────────────────────────────────┘
                                      │
                    Godot: godot/pixelcraft_sprite.gd (AnimatedSprite2D,
                    normal-mapped for 2D lights)
```

## What each piece is for

| Piece | Role | Where it runs |
| --- | --- | --- |
| **TRELLIS.2** | Image → textured 3D model. The only step that needs a big NVIDIA GPU. | A GPU box: your Windows PC with the 4080, a rented cloud GPU, or the Hugging Face demo |
| **pixelcraft** | Everything else: rigging, animations, all the clean-up fixes, rendering, pixel processing, sheets. One config per enemy. | Anywhere Blender runs, including a Mac |
| **Godot** | The game. `pixelcraft_sprite.gd` turns a sheet into an animated, light-reactive sprite. | Your game |
| **GodotPixelRenderer** | Not part of the pipeline: a viewer for trying looks live. `pixelcraft glb` exports the prepared enemy for it. Its dithering and inner lines are available in pixelcraft as `shade.dither` and `outline.inner`. | Your Mac, by hand |

GodotPixelRenderer has no API: it's a GUI app, and wrapping it would duplicate pixelcraft's render
step without the fixes generated models need. Using it as a viewer keeps one source of truth.

## On a Mac

TRELLIS.2 needs CUDA (NVIDIA), and its README only supports Linux, so it can't run on a Mac.
Everything else can: Blender and the `bpy` module run on Apple Silicon. Options for the TRELLIS
step, cheapest first:

1. **Your Windows PC as the GPU box.** Run the TRELLIS.2 demo app there (Docker or WSL2) and point
   pixelcraft at `http://<pc>:7860`. Free, unlimited.
2. **Hugging Face demo with a free account.** A small daily GPU allowance; fine for an enemy or two.
3. **A rented GPU** (RunPod, Modal and similar) for batches. Billed per minute while it runs.

The demo app's API has two steps, `image_to_3d` (image + seed + quality settings) then
`extract_glb` (face count + texture size); a Gradio client can call both.

## What we take from GodotPixelRenderer

- **Its animation library.** The sample skeleton carries KayKit's 95 CC0 clips. pixelcraft
  retargets them onto any humanoid enemy (`assets/creatures/beast/beast_kaykit.json`), so the clips
  you can play in its viewer are the ones the pipeline renders.
- **Its look controls**, as config: camera side/position (`start_angle`, `pitch`, `height`),
  colour steps and palette remap (`palette.max_colors`, `palette.file`), dithering and edges
  (`shade.dither`, `outline.inner`). Its three-light rig (key, fill, rim) has no counterpart: the
  sheet's normal map lets Godot's 2D lights do that at runtime.

## The other route: image models plus pixel snapping

The "Stop Generating Fake Pixel Art" workflow (GPT Image 2 or Nano Banana 2) skips 3D: generate a
1024² chroma-green anchor, pixel-snap it
([Sprite Fusion Pixel Snapper](https://spritefusion.com/pixel-snapper), open source), scale back up
with nearest neighbour, generate a 2048×1536 pose board per animation from the anchor plus a
checkered pixel grid, then cut frames by chroma key and bounding box, pick frames, snap each, align
them by hand, key out the background and pack.

It fixes three problems image models create: off-grid "mixels", frames bleeding into each other,
and frames drifting. The 3D route doesn't have them: every frame is rendered on the pixel grid,
into its own cell, from the same pivot. Its author also says image models can't do walk cycles.
Worth trying for enemies 3D can't rig (slimes, swarms, ghosts), with Gemini as the image model.

## Planned command

```
pixelcraft make concept.png --name beast --trellis http://pc.local:7860 --height 140
```

writes `assets/creatures/beast/` (concept, model, config with `"preset": "trellis"`) and runs
the rest. Rigging stays manual (`rig.json`) until auto-rigging joins the GPU box.
