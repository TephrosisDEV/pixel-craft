# 07. Roadmap and costs

Each phase ends with something usable and an eval number. Don't start a phase before the
previous eval is good enough.

## Phase 0: baseline in a weekend

- ComfyUI: FLUX.2 klein 4B (or SDXL + pixel-art-xl) at 8×, then our grid snap and OKLab palette.
- Build the eval set: 200 prompts across sizes and styles, plus 50 reference characters.
- **Exit:** grid-correct ≥ 95% on our own outputs; a gallery we'd show someone.

## Phase 1: text to sprite, as an API (2–4 weeks)

- Data pipeline plus licence manifest. 3–5k captioned CC0 and commissioned images.
- Style LoRA with the caption controls (outline/shading/detail/view/direction/isometric).
- FastAPI, the job table, one GPU worker on serverless, `POST /generate`, API keys, credits.
- Post-processing module with tests on fixed fixtures.
- **Exit:** blind A/B against PixelLab text-to-sprite at 32/64/128 px, at least parity on half the prompts.

## Phase 2: consistency tools (4–8 weeks, the real work)

- 3D pixel shader render farm, which gives rotation and animation pairs.
- Rotation LoRA: turnaround sheet plus pairwise edit. `POST /rotate`, `POST /characters`
  (4 or 8 directions).
- Inpainting with paste-back and palette lock.
- **Exit:** view consistency and palette overlap above the thresholds in doc 04, and humans
  prefer ours or call it a tie ≥ 40% against PixelLab rotate.

## Phase 3: animation (4–6 weeks)

- Skeleton estimate (pose model on upscaled sprite plus manual fix UI).
- Pose LoRA with sheet-based multi-frame generation. Template library (walk/run/idle/attack/jump/hurt).
- `POST /animate-with-skeleton`, `POST /animate` (template or text).
- **Exit:** 8-frame walk cycle in 8 directions that loops with no visible identity drift.

## Phase 4: tilesets and maps (3–4 weeks)

- Seamless terrain generation, then Wang 16 / dual-grid 15 transitions via inpainting, with
  the automatic seam checker.
- Export to Godot/Tiled/Unity formats.

## Phase 5: surfaces (in parallel from phase 1)

- Web editor (canvas, layers, palette, selection as mask, skeleton overlay).
- Aseprite extension.
- MCP server.
- Stripe credits.

## Rough costs

| Item | Estimate |
| --- | --- |
| LoRA training run (4B, a few thousand images) | Several GPU-hours on one H100: tens of dollars per run. Budget for dozens of runs |
| 3D render farm for pairs | CPU/GPU rendering, mostly one-off. The asset licences cost more than compute |
| Inference per image (4B, few steps, L40S) | A few seconds of GPU, roughly $0.002–0.01 per image on serverless at list prices, before cold-start overhead |
| Commissioned art for the style set | The biggest variable. It is also the biggest quality lever |

PixelLab charges about $9–50/mo for 1–2k+ generations, so the unit economics work if one
generation costs under about a cent and cold starts are kept low.

## Biggest risks

1. **Rotation quality.** If 8-direction consistency isn't there, the product is just another
   text-to-sprite tool. De-risk it first in phase 2 with a small render set before building
   everything else.
2. **Synthetic look.** Rotation and animation trained only on 3D renders can look like 3D. Mix
   in real sprites and commissioned pairs.
3. **Data licences.** Fixing provenance after training means retraining.
4. **Cold starts** hurting the editor UX. Keep a warm worker, and design the UI around
   async jobs from the start.
