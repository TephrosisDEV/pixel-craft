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

## Planned command

```
pixelcraft make concept.png --name beast --trellis http://pc.local:7860 --height 140
```

writes `assets/creatures/beast/` (concept, model, config with `"preset": "trellis"`) and runs
the rest. Rigging stays manual (`rig.json`) until auto-rigging joins the GPU box.
