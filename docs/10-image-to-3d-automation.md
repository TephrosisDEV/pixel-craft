# 10. Automating image → rigged, animated 3D

The goal of this repo is one command: concept image in, animated pixel sprite sheet out.
Rendering and pixel processing are built (`pixelcraft run`). This page covers the part before
that: image → 3D model → rig → animations. Researched Sept 2026.

## Pixel output forgives most 3D defects

Community workflows (r/aigamedev) spend most of their effort on retopology, UV fixes, split
meshes and new materials. That matters for a 3D game. At 64–160 px it mostly doesn't: bad
topology, messy UVs and texture seams disappear. What still shows:

- the **silhouette** (thin parts such as tendrils, capes and tails come out lumpy);
- **joint deformation** (crunched shoulders or knees can show at 128 px and above);
- **texture busyness** (photo-like detail turns into pixel noise; see doc 09).

So a service's raw output is usually good enough. No cleanup stage is needed at first.

## Options

| Option | Image → 3D | Rig | Animations | Automatable | Cost |
| --- | --- | --- | --- | --- | --- |
| **Tripo API** | P2.0 (released 2026-09-21): single image, or up to 4 views (front/left/right/back), native quads, body/clothing/accessories separated | `rig_model`: biped, quadruped, hexapod, octopod, avian, serpentine, aquatic, other; Mixamo-compatible bone spec option | `retarget_animation` presets: idle, walk, run, jump, slash, shoot, hurt, fall, turn, dive, climb, plus quadruped/hexapod/octopod/serpentine/aquatic locomotion | Yes: official Python SDK (`tripo3d`) with image, multiview, rig and retarget | 2,000 free API credits on first key (~$20). Then $0.01/credit. Reported: image → textured model ~56–70 credits, retarget ~20 per animation |
| Meshy | Meshy-6 | Humanoid-focused. Quadrupeds claimed in the web app | 20+ presets free, 600+ paid | API only from Pro ($20/mo). A test-mode key returns sample data | Web app: rigging and animation cost no credits. ~43 credits for a finished character via API |
| Mixamo | – | Humanoids only. Rejects large tails, wings and extra limbs | Large library | No API, manual web upload | Free |
| GrandpaCAD | Mainly CAD, has an "organic mode" | – | – | No public API found | – |
| Local open models | TRELLIS.2 (MIT, 24 GB GPU) | Make-It-Animatable (MIT, humanoids, Mixamo-style skeleton). UniRig (MIT, any body plan, non-standard bone names) | Quaternius Universal Animation Library 1 + 2 (CC0, 250+ incl. zombie locomotion) | Yes, with an NVIDIA GPU, or via Hugging Face Spaces with a daily ZeroGPU quota | Free |

## Recommendation

1. **Tripo backend first.** It is the only option that covers image → model → rig → animation
   in one automatable API, including **non-humanoid** creatures. The free credits cover
   prototyping (roughly 15–25 creatures with a few animations each). After that it costs about
   $1 per creature.
2. **Rig with the Mixamo bone spec**, so the CC0 Quaternius animations and any Mixamo downloads
   can be retargeted onto Tripo rigs locally in Blender. Tripo's preset list alone is short.
3. **Keep "bring your own rigged model"** (already works) for Meshy/Mixamo web exports.
4. **Local backend later** (TRELLIS.2 + Make-It-Animatable/UniRig) if a GPU is available or
   volume makes the API cost matter.

## Input image rules (all services)

- Full body, one character, plain background, no ground shadow.
- Neutral **T- or A-pose**, front view. The Reddit experience matches the docs: a 3/4 view can
  work, but a posed side view reconstructs poorly.
- Painted/rendered style, not pixel art. Pixel art input bakes jagged texture into the model.
- Multi-view (front/side/back of the same design) improves Tripo P2.0 results but is a paid
  feature in the web app. Via the API it is billed per credit.

## Planned command

```
pixelcraft make concept.png --rig biped --animations idle,walk,slash --height 140 --directions 1
  → Tripo: image_to_model → rig_model (Mixamo spec) → retarget_animation → GLB
  → render (headless Blender) → process → sheet.png + sheet.json + previews
```

`TRIPO_API_KEY` comes from the environment and is never written to a config file.

## Sources

- Tripo SDK API reference (rig types, presets, multiview): https://github.com/VAST-AI-Research/tripo-python-sdk/blob/master/docs/API.md
- Tripo P2.0: https://www.tripo3d.ai/blog/tripo-p2-0-preview, https://aicybr.com/blog/tripo-p2-native-quad-mesh-ai-3d-generation
- Tripo API credits: https://aicredits.dev/submissions/190-tripo-ai-2-000-free-api-credits-on-signup-300-month-on-basic-plan, https://developers.tripo3d.ai/en/pricing
- Meshy rigging and pricing: https://www.meshy.ai/features/ai-auto-rigging, https://meshyiai.com/api-pricing/, https://www.meshy.ai/pricing
- Mixamo limits: https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html, https://community.adobe.com/t5/mixamo-discussions/rigging-non-human-shaped-characters/m-p/13634403
- GrandpaCAD: https://grandpacad.com/en
- Comparisons: https://www.indiehackers.com/post/best-ai-3d-model-generator-in-2026-i-tested-9-of-the-best-and-here-is-what-i-found-70ecab1a0a, https://app.cinevva.com/guides/ai-3d-model-generators
- Open models: https://github.com/microsoft/TRELLIS.2, https://github.com/jasongzy/Make-It-Animatable, https://github.com/VAST-AI-Research/UniRig
- CC0 animations: https://quaternius.com/packs/universalanimationlibrary.html, https://quaternius.com/packs/universalanimationlibrary2.html
