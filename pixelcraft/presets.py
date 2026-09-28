"""Named bundles of settings for a kind of source model, applied under a config's own values.

    {"preset": "trellis", "render": {"height": 140}}  ->  trellis settings, with height overridden

Imported both by the Blender render script and by the processing step, so it must not use
relative imports.
"""

PRESETS = {
    # Raw TRELLIS.2 image-to-3D output. Each entry fixes a problem seen on real output:
    "trellis": {
        "render": {
            "strip_ground": True,         # the concept's ground shadow becomes a mesh sheet under the feet
            "texture_colors": "linear",   # textures are written linear but tagged sRGB: far too dark
            "texture_bleed": True,        # white filler between texture islands shows as specks
            "texture_despeckle": True,    # bright spots baked into the texture show as specks
            "remesh": 0.005,              # thousands of overlapping fragments make the sprite shimmer
            "keep_posture": True,         # concepts are posed (hunched, leaning); don't straighten them
        },
        "shade": {"normal_blur": 2},      # ragged light-band edges flicker as the surface moves
        "palette": {"max_colors": 32},
        "cleanup": {"despeckle": True, "highlights": True},  # remaining isolated and light specks
    },
}


def apply(config: dict) -> dict:
    """The config with its preset's sections filled in underneath its own values."""
    preset = PRESETS.get(config.get("preset"), {}) if config.get("preset") else {}
    if config.get("preset") and not preset:
        raise ValueError(f"unknown preset {config['preset']!r}, choose from {sorted(PRESETS)}")
    merged = dict(config)
    for section, values in preset.items():
        merged[section] = {**values, **config.get(section, {})}
    return merged
