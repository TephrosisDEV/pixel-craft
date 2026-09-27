# 01. PixelLab teardown

## What the product does

Four core workflows (from PixelLab's site and reviews):

- **Text to sprite / image.** Two models: **PixFlux** (medium to extra-large images, up to 400×400
  area, better text understanding) and **BitForge** (small to medium, style reference image
  support). The PixFlux docs page also says the model is trained on 16×16 pixel tiles
  (search excerpt, not verified).
- **Characters.** Create a character in 4 or 8 directions. The **Rotate** tool takes one view and
  generates the other seven. It can also change camera view between side, low top-down and
  high top-down.
- **Animation.**
  - *Animate with text*: one reference frame plus an action ("walk", "swing sword"), giving 1–20 frames.
  - *Animate with skeleton*: estimate a skeleton from the sprite, edit keypoints per frame,
    and the model renders each pose in the character's style.
  - *Template animations* (walk, run, idle…) on stored characters, through the MCP server.
- **Tilesets and maps.**
  - *Create tileset*: two terrain descriptions (`lower`, `upper`) give a connectable
    **Wang tileset**. It exports to Wang, dual-grid 15-tile and 3×3 formats. There is a
    sidescroller variant with platform thickness.
  - Isometric tiles.
  - *Create tiles (Pro)* with up to 16 style reference tiles.
  - A *Map* workshop that extends maps with inpainting.
- **Editing.** Inpainting that preserves the surrounding style (change clothes, add accessories),
  and style transfer from reference images.

Surfaces: a web editor, an **Aseprite extension**, a REST API (v1 and v2) with Python and JS
SDKs, and an **MCP server** ("Vibe Coding") whose tools are asynchronous jobs taking 2–5 minutes.

## API surface (read from the public Python SDK)

Base URL `https://api.pixellab.ai/v1`. All images go over the wire as base64. Responses carry
`image(s)` and `usage`.

Shared enums:

```text
CameraView = "side" | "low top-down" | "high top-down"
Direction  = south | south-east | east | north-east | north | north-west | west | south-west
Outline    = "single color black outline" | "single color outline" | "selective outline" | "lineless"
Shading    = "flat shading" | "basic shading" | "medium shading" | "detailed shading" | "highly detailed shading"
Detail     = "low detail" | "medium detail" | "highly detailed"
```

Skeleton keypoint labels (18): NOSE, NECK, R/L SHOULDER, R/L ELBOW, R/L ARM, R/L HIP, R/L KNEE,
R/L LEG, R/L EYE, R/L EAR. Each keypoint is `{x, y, label, z_index}`.

| Endpoint | Key parameters |
| --- | --- |
| `POST /generate-image-pixflux` | description, negative_description, image_size, text_guidance_scale (1–20, default 8), outline, shading, detail, view, direction, isometric, no_background, coverage_percentage (0–100), init_image + init_image_strength (0–1000, default 300), color_image (forced palette), seed |
| `POST /generate-image-bitforge` | as above, plus extra_guidance_scale (style, 0–20), style_strength (0–100), style_image, inpainting_image + mask_image, skeleton_keypoints + skeleton_guidance_scale, oblique_projection |
| `POST /inpaint` | description, inpainting_image, mask_image (white = repaint), text/extra guidance, the style enums, init_image, color_image |
| `POST /rotate` | from_image, from_view/to_view, from_direction/to_direction, or view_change/direction_change (degrees), image_guidance_scale, mask_image, init_image, color_image |
| `POST /animate-with-text` | reference_image, description, action, view, direction, n_frames (1–20), start_frame_index, text/image guidance, per-frame init_images, inpainting_images, mask_images, color_image |
| `POST /animate-with-skeleton` | reference_image, skeleton_keypoints (one list per frame), view, direction, reference_guidance_scale, pose_guidance_scale, per-frame init/inpainting/mask images, color_image |
| `POST /estimate-skeleton` | image (character on transparent background), giving keypoints |
| `GET /balance` | credits |

The v2 API (`/v2/create-image-pixflux`, `/v2/create-image-bitforge`, `/animate-with-text-v3`,
character and tileset jobs) adds stored characters and job IDs. The OpenAPI spec is at
`api.pixellab.ai/v1/openapi.json`, but that host was blocked from this environment.

## What the parameters reveal (inferred)

- **`init_image_strength` 0–1000** is a diffusion timestep: 1000 steps is the DDPM schedule of
  SD-family models. This is img2img/SDEdit. The model was at least originally a Stable
  Diffusion–style latent diffusion model. The name "PixFlux" hints at a later Flux-based model.
- **Style enums are caption tokens.** Outline, shading, detail, view and direction are discrete
  labels. The cheapest way to make a model obey them is to caption the training data with exactly
  these phrases. They are "weakly guiding" in the inpaint docs, which fits prompt conditioning
  rather than a hard control.
- **`extra_guidance_scale` and `skeleton_guidance_scale`** are separate classifier-free-guidance
  terms for the style image and the pose. That is multi-condition CFG, the same pattern as
  InstructPix2Pix's text and image scales or ControlNet conditioning scales.
- **The skeleton format is OpenPose/COCO-18.** The labels map one to one to COCO-18
  (wrist = "ARM", ankle = "LEG"). That means a pose ControlNet or pose-conditioned editing model
  and off-the-shelf pose estimators can be reused. `z_index` handles limb draw order.
- **`color_image`** is palette forcing. At minimum it is quantization to the palette after
  generation. It may also steer during sampling.
- **`coverage_percentage`** is probably a caption token or a bounding-box mask controlling how
  much of the canvas the subject fills. This matters for sprites that must sit consistently in
  a fixed frame.
- **Animation takes one reference plus N frame slots, with per-frame init, inpaint and mask
  lists.** That points to generating all frames jointly, probably laid out as a sheet in one
  image, which is the standard trick for cross-frame consistency. `start_frame_index` supports
  extending a sequence.
- **Rotation takes `direction_change` in degrees and a from/to view.** That is a
  view-conditioned editing model: an input image plus a target-view token.

## Pricing (third-party reports, verify before relying on)

- Free: 40 fast generations, then 5 slow per day.
- Tier 1 (about $12/mo, down to $9 with loyalty discount): up to 128×128 generation area,
  about 1–2k generations/mo.
- Tier 2: about $22/mo at max discount.
- Tier 3 "Pixel Architect": $50/mo, highest priority, 20 concurrent jobs, team features.
- Basic tools cost 1 credit. Newer "Pro" tools cost up to 40.

Reviewers' consensus: best-in-class grid cleanliness and consistency among pixel art tools.
Weaknesses are large-scene coherence and occasional off-model rotations.
