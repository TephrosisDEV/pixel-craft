# 03. Architecture

## Shape

```
 Clients                         API                         Workers (GPU)
 ────────                        ───                         ─────────────
 Web editor (React + canvas) ┐
 Aseprite extension (Lua/WS) ├─► FastAPI  ──► jobs table ──► inference worker
 REST / SDK                  │   auth, credits  (Postgres,     ├ base model + LoRA per tool
 MCP server                  ┘   validation      SKIP LOCKED)  ├ pixel post-processing
                                  │                            └ writes result to object storage
                                  └◄── job status / webhook / SSE ◄──┘
```

- **One job model for everything.** Every tool (generate, inpaint, rotate, animate, tileset) is
  a job: `{id, tool, params, status, result_urls, cost}`. Short jobs can be awaited
  synchronously by the API. Long ones (8 directions, animations, tilesets) return an ID, the way
  PixelLab's MCP does.
- **Queue in Postgres.** `SELECT … FOR UPDATE SKIP LOCKED` is enough until thousands of jobs a
  minute. No Redis or Celery on day one.
- **Stored entities.** `character` (reference image, directions, style params, palette) and
  `animation` (frames, skeleton per frame). This is what lets "animate my character" work without
  re-uploading.
- **Object storage** (S3/R2) for all images. The API returns URLs, plus base64 on the sync path
  for API parity.

## Inference worker

Use Python with `diffusers`, not ComfyUI, in production. ComfyUI is excellent for prototyping
a pipeline in an afternoon. Port it once it works.

Per request:

1. Resolve the tool to a base model plus LoRA set (hot-swapped; keep base weights resident).
2. Build the conditioning:
   - the prompt from description plus style tokens (outline/shading/detail/view/direction/
     isometric), in the exact caption format used in training;
   - reference images (style, character, previous frames) for the editing model;
   - pose images rendered from skeleton keypoints for animation;
   - masks for inpainting and tileset borders.
3. Sample at **k× the target resolution**, where k = 8 for targets ≤ 64 px and 4 for larger
   targets, so each art pixel is a k×k block in model space.
4. Post-process ([doc 05](05-pixel-postprocessing.md)): grid snap, palette, alpha, outline
   cleanup. The result has exactly `target_w × target_h` pixels.
5. For multi-output tools (8 directions, N frames), process all outputs with **one shared
   palette** so they can't drift.

## Serving

- **Serverless GPU** while traffic is low. Modal bills per second (H100 about $3.95/h, L40S about
  $3.51/h) and scales to zero. RunPod pods are cheaper per hour (L40S about $1.14/h) and win once
  a GPU is busy more than about 80% of the time. Start on Modal or RunPod serverless. Move to
  reserved pods once utilisation justifies it.
- A 4B model at 512–1024 px with 4–8 distilled steps is a few seconds on an L40S. Batch
  multi-view or multi-frame jobs into one sheet image instead of N calls.
- Cold starts are the main UX risk. Keep one warm worker during active hours.

## Clients

- **Web editor.** A canvas pixel editor (layers, palette, selection-as-mask) with the AI tools in
  a side panel. Selection becomes the inpainting mask. Draw the skeleton over the sprite for
  pose animation. Pixelorama and Piskel are references for the editor part.
- **Aseprite extension.** Lua. Aseprite can open a WebSocket client but not a server, so the
  extension talks to our API over WebSocket or HTTP. It sends the active cel or selection and
  writes results back as new layers or frames.
- **MCP server.** A thin wrapper over the REST API with async job tools, mirroring
  `create_character`, `animate_character` and `create_tileset`.
- **SDKs.** Generate from the OpenAPI spec that FastAPI emits.

## Tech choices (defaults, change if there's a reason)

| Concern | Choice |
| --- | --- |
| API | Python 3.12, FastAPI, Pydantic, SQLAlchemy/psycopg |
| DB | Postgres (jobs, users, credits, characters) |
| Storage | Cloudflare R2 |
| Inference | diffusers + PEFT LoRAs, torch compile, fp8/bf16 |
| Post-processing | NumPy/OpenCV in-worker. Optionally the pixel-art-fixer Rust core via PyO3 |
| Web | Next.js/React, canvas 2D (WebGL only if large maps need it) |
| Payments | Stripe, credit-based like PixelLab |
| Auth | API keys for the API/MCP/Aseprite, session auth for web |
