# 04. Models and training

## Base model

**FLUX.2 [klein] 4B (Apache 2.0).** It is small enough for cheap inference and LoRA training on
one 24–48 GB GPU, and it does text-to-image and multi-reference editing in one network. That
covers generate, inpaint, style reference, rotate and pose from one base.

Fallback or second opinion: **Qwen-Image-Edit-2509 (Apache 2.0)**. It is heavier, but it has
native keypoint control and a proven "multiple angles" community LoRA. Run the same rotation
eval on both before committing.

Avoid shipping on FLUX.1-dev or klein 9B (non-commercial licences).

## The trick every pixel model uses

Diffusion models don't produce a 32×32 image well. They produce a 512×512 image where each
"pixel" is a 16×16 block. So:

- **Training data:** take native pixel art (1 art pixel = 1 image pixel), nearest-neighbour
  upscale by k to the model's working size, and pad onto a canvas.
- **Inference:** generate at k×, then snap to the grid and downscale.

Because we choose k and the canvas, the grid is known at inference. That is much easier than
fixing arbitrary "fake pixel art". pixel-art-fixer is only needed for user uploads and as
a safety net.

## LoRA 1: style (text to sprite)

- **Captions carry the controls.** Every training image is captioned with PixelLab-style
  attributes: `outline: single color black outline, shading: basic shading, detail: medium
  detail, view: low top-down, direction: south, isometric: no, background: none`, plus a content
  description. Auto-label outline, shading and detail with simple image statistics (outline
  pixel ratio, colours per hue ramp) and a VLM. Labelling by hand doesn't scale.
- **Resolution buckets.** Train sizes 16–256 with the right k per bucket so the model learns
  both chunky and hi-bit styles.
- **Size:** a few thousand well-labelled images is enough for a strong style LoRA. Quality and
  licence matter more than volume (see doc 06).

## LoRA 2: rotation (one view to eight views)

This is the moat feature, and paired data is the bottleneck.

**Synthetic data from 3D.** Take rigged, licensed 3D characters (Mixamo-style rigs, CC0 or
bought model packs). Render each at 8 yaw angles × 3 camera pitches (side, low top-down, high
top-down) with a **pixel-art shader**: low-res render target, cel/posterized lighting, outline
pass, palette quantization. Every character gives 24 perfectly consistent views.

Mix in **real hand-drawn directional sprites** where licences allow, for example the LPC 4-view
characters (CC-BY-SA/GPL, check terms). Synthetic-only data leaves a "3D look".

**Formulation**, with two options (try both):

- (a) **Pairwise edit:** input = source view + caption `rotate from south to north-east, view:
  low top-down`, target = the other view. Simple and matches the `/rotate` API.
- (b) **Turnaround sheet:** generate all 8 directions in one 3×3 grid image (centre cell = the
  reference). Joint generation shares attention across views, so consistency is better. This is
  what the Flux Kontext turnaround LoRAs do. It is likely the better default for "create 8-dir
  character". Keep (a) for single fixes.

## LoRA 3: pose-driven animation

**Skeleton format:** COCO-18 keypoints (same labels as PixelLab), rendered as an OpenPose-style
colour stick image at k× scale.

**Data:**

- Synthetic: the same 3D rigs, animated with mocap clips (walk, run, idle, attack, jump), rendered
  through the pixel shader at 4 or 8 frames per cycle. Export the projected joint positions per
  frame as keypoints. That gives exact pose/frame pairs for free.
- Real: licensed sprite sheets with keypoints from a pose estimator run on the upscaled frames.
  Correct these by hand. Pose estimators are poor on 32 px sprites.

**Formulation:** input = reference sprite + pose image(s), target = the frame(s). As with
rotation, generate **all frames of a cycle in one sheet image** so identity, palette and
proportions stay locked. Qwen-Image-Edit's built-in keypoint conditioning is a head start.

**Animate with text:** map the action text to a pose sequence. Start with templates (walk, run,
idle, attack, jump, hurt, death × 8 directions) and retarget them to the character's estimated
skeleton. That covers the common cases and is deterministic. PoseCrafts shows text-to-OpenPose
motion is possible for freeform actions later.

**Alternative path:** Wan 2.2 I2V with a pixel-animation LoRA, then fix every frame with a shared
grid and palette. It is better for organic motion (fire, water, capes) and worse for exact game
timing. Keep it for effects animation.

## LoRA 4: tilesets

Target: a **Wang 2-corner tileset** (16 tiles, 15 for dual-grid) from two terrain prompts.

Approach:

1. Generate a seamless texture for each terrain. Use circular padding in the conv layers / VAE,
   or Tiled-Diffusion-style latent wrapping. The texture wraps in both directions.
2. Build the 16 corner combinations as **masks** on a 4×4 layout. Generate the transitions by
   **inpainting the boundary band** with both textures as context and a caption like
   `tileset transition: grass to sand, top-down`.
3. Snap to grid, then share one palette across all 16 tiles.
4. Verify connectivity automatically: assemble a random map from the tiles and measure seam
   error on every edge. Regenerate tiles that fail.

Sidescroller variant: the same approach with a platform-thickness mask instead of corners.
Isometric: train with isometric captions and a diamond canvas mask.

## Inpainting and style reference

Both come from the editing base model almost for free: masked-region editing with the original
as reference. Train a small LoRA on pixel art edit pairs (clothing swaps, accessory adds). Build
them by compositing parts of licensed sprites. After generation, **paste back only the masked
pixels** so nothing outside the selection changes, then re-quantize the pasted region to the
image's existing palette.

## Evals (build these before training)

- **Grid:** percentage of outputs whose detected native size equals the requested size. Use
  pixel-bench from Retro Diffusion as an external check.
- **Palette:** colour count ≤ limit, ΔE to the requested palette.
- **Rotation consistency:** DINOv2/CLIP similarity between views, and palette overlap between
  views. Human A/B against PixelLab on a fixed set of 50 characters.
- **Animation:** per-frame identity similarity to the reference, palette drift across frames,
  and keypoint error (pose estimator on output vs requested pose).
- **Tileset:** seam error on assembled random maps.
