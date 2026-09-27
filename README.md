# pixel-craft

Tools for making consistent pixel art game assets, in the vein of
[PixelLab](https://www.pixellab.ai/). Nothing is built yet. This repo holds the research,
the technical choices and the roadmap.

## Current direction

No image API budget, so consistency comes from 3D, not from an image model:
**concept art in Gemini, then image-to-3D, Mixamo rig and animation, then a scripted Blender
render in N directions at sprite size with no anti-aliasing and toon shading, then palette and
grid cleanup.** This is the approach Dead Cells used. See
[docs/09-blender-pipeline.md](docs/09-blender-pipeline.md) and, for why nothing existing fits,
[docs/08-existing-projects.md](docs/08-existing-projects.md).

Training our own models (below, and docs 03–04) is the long-term option if this becomes a product.

## How PixelLab works (the short version)

PixelLab is not one magic model. It is a pixel-art-tuned diffusion model wrapped in:

1. **Style controls exposed as parameters**: outline, shading, detail, camera view, direction,
   isometric, palette. These are almost certainly caption attributes the model was trained on.
2. **Reference-conditioned tools**: rotate, inpaint, animate-from-skeleton, animate-from-text,
   style transfer. Each takes an existing sprite and keeps it consistent.
3. **Deterministic post-processing**: a real pixel grid, a fixed palette, binary alpha.
4. **Game-shaped outputs**: 4/8-direction characters, sprite sheets, Wang tilesets, isometric
   tiles. It also ships an Aseprite plugin, a REST API and an MCP server.

A clone in 2026 can be built from open, commercially licensed parts:

| Layer | Pick | Why |
| --- | --- | --- |
| Base model | **FLUX.2 [klein] 4B** (Apache 2.0) | Small, fast, text-to-image *and* multi-reference editing in one model, commercial use allowed |
| Editing / rotation / pose | **Qwen-Image-Edit-2509** (Apache 2.0) as the alternative | Multi-image editing, native keypoint (pose) control, strong LoRA ecosystem |
| Fine-tuning | LoRA per task (style, rotate, pose, tileset) with ostris/ai-toolkit | Cheap to train, easy to swap per request |
| Pixel fixing | Our own grid snap, plus Retro-Diffusion/pixel-art-fixer (MIT) as a fallback | We control the upscale factor, so the grid is known; the fixer covers the rest |
| Palette | OKLab k-means + nearest-colour mapping, optional Bayer dithering | Perceptually correct, cheap, deterministic |
| Serving | FastAPI + Postgres job queue + serverless GPU (Modal or RunPod) | Scale to zero while usage is low |
| Clients | Web editor, Aseprite extension (WebSocket), REST API, MCP server | The same surfaces PixelLab has |

The hard part is the **data**, not the model: paired examples for rotation (same character in
8 directions) and animation (same character across pose frames). The plan is to render them
synthetically from 3D models through a pixel-art shader. See
[docs/04-models-and-training.md](docs/04-models-and-training.md).

## Docs

1. [PixelLab teardown](docs/01-pixellab-teardown.md): features, full API surface (from their
   public SDK), pricing, and what the parameters reveal about the internals
2. [Landscape](docs/02-landscape.md): competitors, open-source models, papers, tools
3. [Architecture](docs/03-architecture.md): system design for the clone
4. [Models and training](docs/04-models-and-training.md): base model, LoRAs, rotation,
   animation, tilesets, inpainting, and where the data comes from
5. [Pixel post-processing](docs/05-pixel-postprocessing.md): grid, palette and alpha, with algorithms
6. [Data, licensing and legal](docs/06-data-and-legal.md)
7. [Roadmap and costs](docs/07-roadmap.md)
8. [Existing open-source projects](docs/08-existing-projects.md)
9. [Blender pipeline, the Dead Cells route](docs/09-blender-pipeline.md)
10. [Sources](docs/sources.md)

## Research notes

- The PixelLab API surface in doc 01 comes from reading their public Python SDK
  (`pixellab-code/pixellab-python`), not from their docs site. pixellab.ai, arxiv.org and
  huggingface.co were blocked from the research environment. Claims about those pages come from
  search-result excerpts and are marked as such.
- Anything that says **(inferred)** is a reasoned guess about PixelLab's internals, not a fact.
