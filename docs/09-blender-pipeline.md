# 09. Blender pipeline (the Dead Cells route)

Every tool here is free. Consistency across directions and frames comes free too, because
everything is rendered from one rigged model.

```
Gemini (AI Studio UI)     image → 3D              rig + animate       Blender (headless script)        Python
concept, A-pose,     ──►  TRELLIS.2 / Tripo /  ──► Mixamo, in-place ──► ortho cam, N directions,     ──► shared palette, grid snap,
front view, plain bg      Meshy free tier          clips (FBX)           tiny render, no AA,               alpha, sprite sheet + JSON
                                                                         colour + normal passes
```

## Steps

1. **Concept.** Draw or generate a 2D model sheet first: A-pose, front view, plain background,
   ideally front/side/back. The design lives in 2D, and 3D only serves it.
2. **Image to 3D.** [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) (MIT, 24 GB GPU locally,
   or a hosted demo), or the Tripo or Meshy free tiers. Avoid Hunyuan3D in the EU, UK and South
   Korea: its licence excludes those regions. Single-image meshes are rough, which doesn't show
   at 32–64 px.
3. **Rig and animate.** Mixamo auto-rig for humanoids. Tick *In Place*. Rigify or a manual rig
   for non-humanoids.
4. **Render.** A scripted Blender run (`blender -b file.blend -P render.py`) renders every
   animation × direction × frame.
5. **Cleanup.** See [doc 05](05-pixel-postprocessing.md). Use one palette across every frame of
   a character.
6. **Hand finish.** Fix eyes, weapon tips and key poses in Pixelorama or Aseprite.

## What Dead Cells did

From Thomas Vasseur's
[Game Developer article](https://www.gamedeveloper.com/production/art-design-deep-dive-using-a-3d-pipeline-for-2d-animation-in-i-dead-cells-i-)
(2018). The article was blocked from the research environment, so this comes from summaries of it:

- Pixel art model sheet first, then the 3D model and skeleton in 3ds Max.
- A homebrew renderer drew the mesh **at very small size, without anti-aliasing**.
- Each frame was exported as a **PNG plus a normal map**. A **basic toon shader in the engine**
  lit it, so sprites react to in-game lights.
- Retakes meant moving keyframes. Animations were reused across characters sharing a skeleton.
  The target was 30 fps.

## Removing the 3D look (our rules, on top of Dead Cells)

- **Low-poly mesh, detail painted in the texture**, flat colours with no baked shading.
  Aim for 1 texel ≈ 1 output pixel.
- **Blender settings:**
  - Colour management *View Transform* = **Standard** (AgX/Filmic desaturate, which reads as 3D).
  - Film **filter size = 0**.
  - Image texture interpolation = **Closest**.
  - No ambient occlusion, bloom or soft shadows in the sprite pass.
- **2–3 hard light bands.** Shader to RGB, then a *Constant* colour ramp, multiplied by the flat
  albedo. One key light from a fixed direction. Or export albedo + normal and toon-shade in the
  engine, the way Dead Cells did.
- **Grid lock.** In-place animations. An orthographic camera whose scale gives an integer world
  size per pixel. Character origin snapped to the pixel grid, to stop 1 px jitter.
- **Push the animation.** Exaggerate poses and anticipation, snap into attacks, hold key poses,
  bone-scale squash and stretch. For a more hand-drawn feel than Dead Cells' smooth 30 fps,
  use *Constant* interpolation (stepped).
- **Outline** by inverted hull (solidify + flipped normals, backface material) or Freestyle.
  Or add it in post: the outermost opaque ring gets the darkest palette colour.
- **Effects are their own track.** Much of Dead Cells' punch is hand-made effects,
  dynamic lighting and screen shake, not the character sprite.

## Render passes to export per frame

| Pass | Use |
| --- | --- |
| Albedo (emission-only flat colour) | Base sprite |
| Toon-lit colour | Ready-to-use sprite when the engine has no lighting |
| Normal (view space, encoded to RGB) | Dynamic toon lighting in the engine |
| Alpha | Binarized mask |

## References

- [Dead Cells shader case study (video)](https://www.youtube.com/watch?v=iNDRre6q98g)
- [Blender Artists: mimicking Dead Cells' workflow](https://blenderartists.org/t/mimicking-dead-cells-workflow-from-3d-animation-to-2d-pixel-animation/1124638)
- [Foozle: render 4 or 8 direction sprites from Blender](https://foozlecc.itch.io/render-4-or-8-direction-sprites-from-blender)
- [8 Directions Render Plugin](https://auteddy.gumroad.com/l/8d_blender_plugin)
- [GameDev.tv: Blender 2D sprites course](https://gamedev.tv/courses/blender-sprites)
