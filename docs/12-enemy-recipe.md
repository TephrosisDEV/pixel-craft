# 12. Recipe: a new enemy

What worked for the first real enemy (`assets/creatures/beast`), in order. Every step that fixes a
problem is covered by `"preset": "trellis"`, so a new enemy only needs its own joints and config.

1. **Concept image.** Full body, one creature, side view is fine (that's what the game shows).
   Painted or rendered style is better than pixel art as input.
2. **Image → 3D.** TRELLIS.2 (web demo while it's free, or locally, see doc 11). Download the
   `.glb` into `assets/creatures/<name>/`, together with `concept.jpg`.
3. **Joints.** Until automatic rigging runs on the GPU: render front and side views with a pixel
   grid, read off joint positions, and write `rig.json` (see the beast's for the joint list).
   Depth for limbs can be measured from the mesh; torso joints come from the side view.
4. **Rig.** `python pixelcraft/rig_blender.py assets/creatures/<name>/rig.json`.
5. **Config.** Copy `assets/creatures/beast/beast.json`, keep `"preset": "trellis"`, set the
   height and animations. Humanoid clips from Mixamo or Quaternius retarget automatically.
6. **Render.** `pixelcraft run assets/creatures/<name>/<name>.json`, then look at
   `out/<name>/previews/*.mp4`.
7. **Check shimmer.** `python tools/flicker.py out/<name>`. Around 1% visible glisten is good;
   the flat test knight scores 0.5–0.8%.

## When something looks wrong

| Symptom | Cause | Setting |
| --- | --- | --- |
| Flat shapes flapping at the feet | Ground shadow modelled as mesh | `render.strip_ground` |
| Almost black | Linear texture tagged sRGB | `render.texture_colors: "linear"` |
| White specks | Atlas filler, baked highlights, rare palette colours | `texture_bleed`, `texture_despeckle`, `palette.min_share`, `cleanup.highlights` |
| Pixels shimmer while moving | Fragmented generated mesh | `render.remesh`, `shade.normal_blur` |
| Creature straightened upright | Rest poses aligned | `render.keep_posture` |
| Limbs stretch into each other | Skinning mixes limbs | Re-rig with `rig_blender.py` |
| Arms swing absurdly far | Human motion on long arms | `render.arm_motion: {"walk": 0.5}` |
| Attack unreadable from the side | Twists and sideways motion | Use pitch-only clips like `lunge` |
