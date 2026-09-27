# 05. Pixel post-processing

Deterministic, fast, and run on every output. This is where "looks like pixel art" becomes
"is pixel art".

## Pipeline

```
model output (k× size, RGB/A)
  → grid snap        → exactly target_w × target_h cells
  → palette          → ≤ N colours, or exactly the user's palette
  → alpha            → binary transparency
  → cleanup          → orphan pixels, doubled outlines (optional)
  → export           → PNG at 1×, plus preview at integer scale
```

## 1. Grid snap

**Known grid (our own outputs).** We generated at k× on a canvas we laid out, so cell (i, j)
covers `[i·k, (i+1)·k) × [j·k, (j+1)·k)`. The model still drifts by a pixel or two, so:

1. Estimate the phase offset (0..k-1 per axis). Maximise edge energy on cell boundaries versus
   inside cells: sum of |∇| at `x ≡ φ (mod k)`.
2. For each cell, take a **centre-weighted vote**: ignore a 1–2 px border of each cell, where
   anti-aliasing lives. Do not take the mean, which blurs edges.

**Unknown grid (user uploads, "fix my AI image").** Use Retro-Diffusion/pixel-art-fixer (MIT).
Its detection uses three independent detectors (autocorrelation of edge projections,
soft-GCD of run lengths, self-similarity under whole-cell shifts) with arbitration. It
handles non-integer cell sizes and drift. Its reconstruction is two-stage:
- **placement:** k-means quantize to adaptive K ∈ [16, 48], then each cell votes on labels,
  which gives crisp region boundaries;
- **colour:** the winning label's colour is the centre-weighted mean of the *original* pixels in
  that cell carrying that label. The quantized palette decides placement only, never output colour.

That two-stage idea is worth copying into the known-grid path too.

## 2. Palette

- **Work in OKLab.** Euclidean distance there is close to perceptual difference. RGB k-means
  merges dark colours and splits bright ones.
- **Auto palette:** k-means in OKLab on the snapped image (weighted by pixel count), K = the user's
  limit (default 16–32). Merge clusters with ΔE_ok < ~0.02.
- **Forced palette (`color_image`):** extract the unique colours of the uploaded palette image,
  then map every pixel to its nearest palette colour in OKLab.
- **Dithering:** off by default (pixel artists dither on purpose, not everywhere). Offer ordered
  Bayer 4×4 in OKLab as an option. Never use Floyd–Steinberg on sprites; it adds noise that
  looks wrong in motion.
- **Multi-output jobs** (8 directions, animation frames, tilesets): compute **one** palette over
  all outputs together and map each against it. This single step removes most flicker between
  frames. proper-pixel-art does the same for animations.

## 3. Alpha

- Generate on a flat key background (for example pure magenta) or with a transparency-aware model.
- Remove the background by flood fill from the canvas border in OKLab with a tolerance, then
  **binarize** alpha (≥ 0.5 → opaque). Pixel sprites have no partial alpha.
- Remove key-colour fringe: any opaque pixel adjacent to background whose colour is closer to
  the key than to its neighbours gets its nearest neighbour's colour.

## 4. Cleanup (optional, per style)

- **Orphans:** a single pixel differing from all 8 neighbours inside a flat region gets the
  majority neighbour colour. Skip on eyes and highlights (small bright clusters near the top of
  the sprite). Keep this conservative.
- **Outline style:** for `single color black outline`, recolour the outermost opaque ring to
  the darkest palette colour. For `selective outline`, darken the ring by one ramp step of the
  adjacent fill instead.
- **Pixel-perfect lines:** remove L-shaped doubles in 1-px outlines (the Aseprite "pixel perfect"
  rule).

## Cost

All of this is NumPy/OpenCV on a ≤ 1024² image, which takes milliseconds. The pixel-art-fixer
Rust core is reported 11–24× faster than its Python reference if we ever need it at the edge
(for example in the browser via WASM, like unfake.js).
