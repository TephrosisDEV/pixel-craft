# pixel-craft

Turns a concept image into animated pixel-art sprite sheets for a side-view **Godot** game with
many enemies: image → 3D (TRELLIS.2) → rig → retargeted animations → Blender render → pixel
processing → Godot sprite. How the pieces fit: `docs/13-one-system.md`.
The owner is new to 3D and works on a Mac (TRELLIS.2 can't run there; it needs an NVIDIA GPU box).
Explain in plain words; show results as MP4 (their phone shows GIFs as stills).

## Layout

| Path | What |
| --- | --- |
| `pixelcraft/render_blender.py` | Blender side: load model and animations, clean the mesh, render albedo + normal passes |
| `pixelcraft/retarget_blender.py` | Humanoid retargeting by bone role (Mixamo and Unreal names) |
| `pixelcraft/remesh_blender.py` | Voxel remesh with baked, smoothed vertex colour and copied skin weights |
| `pixelcraft/rig_blender.py` | Rig a model from hand-placed joints (stopgap until GPU auto-rigging) |
| `pixelcraft/export_blender.py` | `pixelcraft glb`: the prepared, animated enemy as one GLB (for GodotPixelRenderer or Godot) |
| `godot/pixelcraft_sprite.gd` | Godot node: plays `sheet.json`, normal-mapped for 2D lights, origin at the feet |
| `pixelcraft/process.py`, `shade.py`, `palette.py`, `sheet.py` | Pure Python: toon shading, palette, cleanup, outline, sheets, GIF/MP4 |
| `pixelcraft/presets.py` | `"preset": "trellis"` bundles every fix below for raw TRELLIS.2 output |
| `assets/creatures/<name>/` | Per enemy: source `.glb`, `concept.jpg`, `rig.json` (joints), render config |
| `examples/make_test_knight.py` | Test rig and clips (`idle`, `walk`, `attack`, `lunge`) with Mixamo bone names |
| `tools/flicker.py` | Measures shimmer in a finished sheet |
| `docs/12-enemy-recipe.md` | Step by step for a new enemy |

## Commands

```sh
pip install -e ".[dev,video]" bpy                   # bpy = Blender as a Python module (5.0)
PIXELCRAFT_BLENDER=$(which python) pixelcraft run <config.json>   # or point it at blender.exe
python pixelcraft/rig_blender.py assets/creatures/<name>/rig.json
PIXELCRAFT_BLENDER=$(which python) pixelcraft glb <config.json>   # prepared enemy -> <output>/<name>.glb
python tools/flicker.py out/<name>                   # glisten % per animation; the flat knight is ~0.5-0.8
PIXELCRAFT_GODOT=/path/to/godot pytest              # render tests skip without bpy, Godot test without Godot
```

Blender needs `examples/knight.blend` (`python examples/make_test_knight.py examples/knight.blend`)
for the `lunge` clip, and `assets/animations/Soldier.glb` (three.js repo,
`examples/models/gltf/Soldier.glb`, git-ignored) for the walk.

## Lessons from real models (each is a setting; keep them)

Found on the first real enemy (`assets/creatures/beast`). All are on in `"preset": "trellis"`.

1. **Ground sheet:** TRELLIS turns the concept's ground shadow into flat mesh fragments at the
   feet, which then flap with the legs. `strip_ground` removes islands in the bottom 4% of height.
2. **Dark textures:** TRELLIS writes linear colour into textures tagged sRGB (~18/255 instead of
   ~75). `texture_colors: "linear"`.
3. **White specks, three sources:** atlas filler between UV islands (`texture_bleed`), bright spots
   baked into the texture (`texture_despeckle`), and rare colours claiming palette slots
   (`palette.min_share`, 0.2%). Leftovers: `cleanup.highlights` and `cleanup.despeckle`.
4. **Shimmering pixels:** the mesh is thousands of overlapping fragments with different texture
   patches, so each pixel hits a different one per frame. Texture size and colour count don't
   help. `remesh` (voxel size as a fraction of height) fuses it into one surface with smoothed
   vertex colour; `shade.normal_blur` stops light bands flickering on the voxel grain. Measure
   with `tools/flicker.py`: beast went from 1.84% to ~1.2% (walk).
5. **Hunched posture straightened:** retargeting aligns rest poses. `keep_posture` keeps the
   model's own spine/neck/head pose.
6. **Legs glued together:** nearest-bone skinning let inner-thigh vertices follow both legs.
   `rig_blender.py` limits each vertex to bones on its own side and within one limb.
7. **Long limbs swinging wildly:** human arm motion on much longer arms. `arm_motion` scales arm
   rotation, per animation (`{"walk": 0.5}`).
8. **Attack reading badly from the side:** twisting motions don't read in profile. `lunge` uses only
   pitch (x) rotations: wind-up, lunge, follow-through, recover. In the knight rig, +x on
   Hips/Spine leans forward, -x on arms raises them forward/up, and thigh -x with shin +x bends
   the knee forward (check signs numerically on bone positions; small renders are easy to misread).
9. **Feet skating in attacks:** swinging legs without moving the body slides the feet, and a
   creature's legs never match the source rig exactly. `plant_feet: ["attack"]` pins both feet to
   their first-frame position with two-bone IK. The knee bend direction and foot angle must also
   come from the first frame, or the knee swings around the hip-ankle line. A perfectly straight
   leg has no bend direction: knees then bend towards the facing direction (without that, the
   solver silently did nothing on the knight).
10. **Hip motion vanishing:** retargeting scales hip movement by hip height, which must be measured
   above the feet: TRELLIS puts the origin mid-body, which shrank the crouch to nothing.
11. **Debugging deformation:** colour the mesh by dominant bone group (legs red, arms blue) and
   print bone vs. mesh positions per frame. It separated "bone moves" from "skin moves" in minutes.
12. **Sinking into the floor in Godot:** the sheet pivot was the model origin, mid-body on TRELLIS
   models. The pivot is now the floor point under the origin, so the Godot node's origin is the feet.
13. **Dither and inner lines** (`shade.dither`, `outline.inner`, ideas from GodotPixelRenderer)
   tripled the beast's glisten (1.2% → 3.9%): screen-fixed dither crawls over a moving body and
   inner lines catch surface bumps. Off by default; try them on smooth models only.
14. **Never write into the source folder:** a default export path once overwrote the beast's
   source `.glb` (restored from git). Outputs go under the config's `output` folder, and the GLB
   export refuses to overwrite the model it loaded.

Blender gotchas hit along the way:
- Persistent render data plus material-override switching renders materials black. Keep it off.
- Changing an image's colour space reloads it from disk and drops pixel edits: edit after.
- With the pip `bpy` module, `import bmesh` only works after `import bpy`.
- Cycles camera space has +Z into the scene; the normal pass flips it.
- Importing a file twice suffixes action names `.001`; match names with the suffix stripped.
- Retarget keys the bone's own rotation mode; forcing quaternions broke Euler actions.
- A `.blend` can't load data from itself; use a second copy as an animation source.

## Environment notes

This cloud session can't reach Hugging Face, arxiv, Tripo or Meshy, and has no GPU. TRELLIS.2
and auto-rigging run on the owner's Windows PC (RTX 4080, 16 GB): see `docs/11-windows-setup.md`.
