# 11. Windows setup (RTX 4080, 16 GB)

What runs where, and how to install it. The rendering half (`pixelcraft`) is tested. The AI half
(image → 3D, rigging) hasn't been run by us yet: follow the linked official instructions and note
what differs, so this page can be corrected.

## 1. Rendering half (tested)

1. Install [Blender](https://www.blender.org/download/) 4.2 or newer.
2. Install Python 3.11 or newer, then from the repo folder:
   ```powershell
   py -m pip install -e .
   setx PIXELCRAFT_BLENDER "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
   ```
   (Open a new terminal after `setx`; adjust the path to your Blender version.)
3. Check it works:
   ```powershell
   & $env:PIXELCRAFT_BLENDER -b -P examples/make_test_knight.py -- examples/knight.blend
   pixelcraft run examples/knight.json
   ```
   Output lands in `out/knight/`; open `previews/walk.gif`.

## 2. Animations (free)

- [Quaternius Universal Animation Library](https://quaternius.com/packs/universalanimationlibrary.html)
  and [part 2](https://quaternius.com/packs/universalanimationlibrary2.html): CC0, 250+ animations
  including zombie locomotion. Download the glTF/FBX files into `assets/animations/` (not
  committed, see `.gitignore`), then reference single clips as `"walk": "assets/animations/UAL1.glb#Walk_Loop"`.
  Clip names are listed by opening the file in Blender (Dope Sheet → Action Editor).
- Mixamo downloads work the same way ("Without Skin", "In Place").

## 3. Image → 3D on the 4080 (not yet verified by us)

**ComfyUI** is the host for the AI models: it ships the fiddly GPU dependencies as ready-made node
packs and has an HTTP API that `pixelcraft make` will call.

1. Install the [ComfyUI portable build for NVIDIA](https://github.com/comfyanonymous/ComfyUI#installing).
2. In ComfyUI's Manager, search **TRELLIS2** and install the node pack. Community guides report
   that 16 GB runs its full-resolution setting with the low-VRAM option
   ([guide](https://trellis2.app/blog/trellis-2-low-vram)); Microsoft's official figure is 24 GB.
3. Load the pack's example image-to-3D workflow, feed it a **front-view A-pose** image on a plain
   background, and export a `.glb`.

Input image tips are in [doc 10](10-image-to-3d-automation.md#input-image-rules-all-services).

## 4. Rigging (manual for now)

Until automatic rigging is wired in, rig the `.glb` with **Mixamo** (free, humanoids only): upload,
place the markers, download as FBX "With Skin". Any Mixamo or Quaternius animation then retargets
onto it through `pixelcraft`.

Planned automatic options:
- [Make-It-Animatable](https://github.com/jasongzy/Make-It-Animatable) (MIT): humanoids, Mixamo
  bone names, so it plugs straight into the retargeting. Its install targets Linux, so on Windows it
  may need WSL2. Its [online demo](https://huggingface.co/spaces/jasongzy/Make-It-Animatable) works
  meanwhile.
- [UniRig](https://github.com/VAST-AI-Research/UniRig) via
  [ComfyUI-UniRig](https://github.com/PozzettiAndrea/ComfyUI-UniRig) (MIT, 8 GB): any body shape,
  but its bone names aren't standard, so animations would need per-creature mapping.

## 5. First real test

```json
{
  "model": "assets/creature/creature_rigged.fbx",
  "animations": {
    "idle": "assets/animations/UAL1.glb#Idle_Loop",
    "walk": "assets/animations/UAL1.glb#Walk_Loop"
  },
  "output": "out/creature",
  "render": {"height": 140, "directions": 1, "start_angle": 90, "pitch": 0},
  "palette": {"max_colors": 32}
}
```

`directions: 1` with `start_angle: 90` renders the right-facing side view only; the engine mirrors
it for left. Clip names above are examples: check the real ones in the pack.
