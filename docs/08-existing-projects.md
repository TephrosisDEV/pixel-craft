# 08. Existing open-source projects

Checked before building anything. None of them is a PixelLab clone with its own models. The good
ones are a UI plus deterministic cleanup around **hosted** image models. The "one-shot" games
with full art are made the same way: Nano Banana Pro or GPT Image 2 for images, plus a cleanup
script an agent wrote.

| Project | Stars (Sep 2026) | Licence | Image backend | Notes |
| --- | --- | --- | --- | --- |
| [sprite-sheet-creator](https://github.com/blendi-remade/sprite-sheet-creator) | ~1.8k | not stated | fal.ai: Nano Banana Pro/Lite, GPT Image 2, Bria background removal | Next.js. Text or image to character, walk/jump/attack sheets, side-scroller or isometric, play-test sandbox |
| [PerfectPixel Studio](https://github.com/gykim80/perfectpixel-studio) | ~570 | MIT | Gemini 3 Pro Image, fal, OpenRouter, Seedream | Go + Wails + React. 8 directions, 100+ actions. Best cleanup: YCbCr chroma matting, DP frame segmentation, alpha-centroid anti-jitter, shared-palette grid snap. Aseprite JSON export |
| [SpriteBrew](https://github.com/GAlbanese09/spritebrew) | ~56 | AGPL-3.0 | Retro Diffusion API | Live paid product. Characters, tiles, animation, 6 engine exporters |
| [Sprute](https://github.com/sprited-ai/sprute) | 2 | MIT | Local ComfyUI (~108 GB of models) | The only fully local one. 8 directions × idle/walk/run. Early |
| [8-direction-pixel-character-generate](https://github.com/oomol-flows/8-direction-pixel-character-generate) | – | – | – | Image to 8-view sheet |
| [pixel-2d-game-art](https://github.com/harumaxy/pixel-2d-game-art) | – | – | Local SD1.5 + AnimateDiff | Mixamo/Quaternius clips, Blender pose hints, pixelate, 8-direction sheet |

## Constraint: no image API budget

A Claude subscription has no image model. Gemini is available through the AI Studio web UI.
The free API model (Gemini 2.5 Flash Image) reportedly shuts down on 2026-10-02, and newer
Gemini image models reportedly need a paid key. So:

- Use Gemini by hand for **concept art only**, a few images per character.
- Get consistency from **3D renders in Blender** (doc 09), not from an image model.
- Tiles, items and UI: Claude writes the pixel grids directly, or procedural generators.

That makes docs 03–04 (own models, own inference) the long-term option, not the starting point.
