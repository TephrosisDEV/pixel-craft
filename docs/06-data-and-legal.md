# 06. Data, licensing and legal

Not legal advice. Get a lawyer before charging money.

## Training data

Rule: **every training image has a recorded source and licence.** Keep a manifest
(`source_url, author, license, date, sha256`) from day one. It is cheap now and impossible
to rebuild later.

| Source | Licence | Use |
| --- | --- | --- |
| Kenney asset packs | CC0 | Style LoRA, tiles, items |
| OpenGameArt CC0 subset | CC0 | Style LoRA. Filter per asset; OGA mixes licences |
| LPC (Liberated Pixel Cup) characters | CC-BY-SA / GPL | 4-direction and animation pairs. Attribution and share-alike obligations: check whether they reach model weights before relying on it |
| HF `carlosuperb/lpc-4view-pixel-art-diffusion` | Inherits LPC | Ready-made 4-view pairs with captions |
| Synthetic 3D renders | Licence of the 3D models (CC0 or bought) | Rotation and animation pairs; the main source |
| Commissioned art | Work-for-hire contract | The quality ceiling. Retro Diffusion's edge is artist-curated data |
| HF `jainr3/diffusiondb-pixelart` | CC0, but these are SD outputs | Avoid. Training on another model's outputs teaches its fake-pixel artefacts |

Avoid scraped itch.io packs, sprite rips from commercial games and Pinterest-style scrapes.
They are legally risky, and the style is recognisable enough that users will notice.

## Base model licences

- FLUX.2 [klein] 4B: Apache 2.0, commercial OK.
- Qwen-Image / Qwen-Image-Edit: Apache 2.0, commercial OK.
- FLUX.1 [dev], FLUX.2 [klein] 9B: non-commercial. Fine for experiments, not for the product.
- SDXL: OpenRAIL++, commercial OK with use restrictions.

## Output ownership

- US Copyright Office (Jan 2025 report) and *Thaler v. Perlmutter* (D.C. Cir., Mar 2025): purely
  AI-generated material is not copyrightable, and prompts alone are not sufficient human control.
  Human edits and arrangements can be protected.
- Product consequence: the terms of service should give users whatever rights we have in
  outputs, without promising copyright. The editor and inpainting tools also help here, because
  they increase human authorship.
- Steam requires disclosure of AI-generated content. A short note in our docs helps users.
