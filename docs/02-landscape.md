# 02. Landscape

## Commercial competitors

| Product | Angle | Notes |
| --- | --- | --- |
| PixelLab | Pixel art specialist, characters, animation, tilesets | Biggest dedicated user base (reported 334k–595k monthly visits), Aseprite plugin, MCP |
| Retro Diffusion | Pixel art specialist, style library | FLUX-based flagship model trained on artist-curated data. Aseprite extension ($20 lite / $65 full, runs locally). Web/API pay-per-image (~$0.015 for 64×64). Open-sourced its pixel fixer (MIT) |
| Ludo.ai | All-in-one game asset tool | 8/16/32-bit and hi-bit tiers, sprite sheets of 4–64 frames |
| Scenario, Layer.ai | Studio pipelines, custom style training | Train on your own art for consistency across a game |
| Sprite-AI, SpriteLab, AutoSprite, God Mode AI, Gamelabs, SpriteCook | Smaller sprite generators | Sprite-AI from $5/mo. SpriteLab focuses on 1px outlines and limited palettes |

Where the gap is: most competitors do text-to-sprite well enough. The defensible parts are
**consistency tools** (rotation, pose-driven animation, tilesets that actually connect) and
**editor integration** (Aseprite, engine plugins, MCP for coding agents).

## Open models worth building on

| Model | License | Use |
| --- | --- | --- |
| FLUX.2 [klein] 4B | Apache 2.0 | Primary base: text-to-image plus multi-reference editing, runs on consumer GPUs, released Jan 2026 |
| FLUX.2 [klein] 9B | Non-commercial | Do not ship on it |
| FLUX.1 [dev] | Non-commercial | Many pixel LoRAs exist on it. Good for research, not production |
| Qwen-Image / Qwen-Image-Edit-2509 | Apache 2.0 | Multi-image editing (1–3 inputs), native keypoint/sketch control, ai-toolkit LoRA support. Community "multiple angles" LoRA exists |
| SDXL + nerijs/pixel-art-xl LoRA | OpenRAIL++ | Cheap baseline. Generate, then 8× nearest-neighbour downscale |
| Wan 2.2 I2V + pixel animate LoRA | Apache 2.0 (base) | Image-to-video for sprite animation, then per-frame fixing |
| MV-Adapter, Zero123++ | Various | Multi-view generation research for rotation |

Existing pixel art LoRAs to learn from, or use as a v0 on HF/Civitai: pixel-art-xl (SDXL),
several Flux.1-dev pixel LoRAs, `svntax-dev/pixel_spritesheet_4walk_small_lora_v1` (4-direction
walk sheet), `Limbicnation/pixel-art-lora` (FLUX.2 klein, CC0-only training data with provenance),
a Wan 2.2 walk-cycle side-view LoRA, and Flux Kontext character-turnaround LoRAs.

## Papers

- **SD-πXL** (SIGGRAPH Asia 2024, MIT code). Score distillation into a low-res grid with a fixed
  palette via Gumbel-softmax. Exact palette adherence, but it takes hours per image. Useful as
  a quality reference, not a product path.
- **Sprite Sheet Diffusion** (arXiv 2412.03685). Adapts pose-guided animation (reference net plus
  pose guider plus motion module, in the style of AnimateAnyone) to game sprite sheets. The closest
  published analogue to "animate with skeleton".
- **PixDiff-PIG**. Palette-informed diffusion for pixel art.
- **Tiled Diffusion** (CVPR 2025). Seamless tiling including many-to-many tile connections, which
  is directly relevant to Wang tilesets.
- **MV-Adapter** (ICCV 2025). Multi-view consistent generation as an adapter on T2I models.
- A GAN line of work on sprite direction generation (pix2pix-style, missing-data imputation GAN).
  It shows rotation is learnable from paired directional sprites.

## Open-source pixel fixing tools

| Tool | License | Approach |
| --- | --- | --- |
| Retro-Diffusion/pixel-art-fixer | MIT, Python + Rust | Three grid detectors (autocorrelation, run-length soft-GCD, self-similarity), an evidence stack to arbitrate, two-stage reconstruction (vote on k-means labels, then take colour from the centre-weighted mean of original pixels). Self-reported 77% exact native-size recovery on its own benchmark (pixel-bench) |
| KennethJAllen/proper-pixel-art | MIT, Python | Canny, then morphological close, then Hough lines to build a grid mesh, then quantize and take the mode colour per cell. Shares grid and palette across animation frames to stop flicker |
| jenissimo/unfake.js | MIT, Rust→WASM + JS | Runs-based or edge-aware scale detection, dominant/median/mode downscale, libimagequant palette, morphological cleanup, alpha binarization |
| PixelRefiner | Browser | OKLab k-means, Bayer and Floyd–Steinberg dithering, grid detection |
| Okolors | Rust | OKLab k-means palette extraction |

## Editor integration

- **Aseprite Lua API** has a WebSocket *client* and can run scripts and extensions. PixelLab and
  Retro Diffusion both ship Aseprite extensions. Community MCP bridges (`ase-mcp`) run a local
  server that the extension dials out to.
- **MCP.** PixelLab's MCP exposes `create_character`, `animate_character`, `create_tileset`,
  `create_isometric_tile` and others as async jobs. This is cheap for us to copy once the API exists.
