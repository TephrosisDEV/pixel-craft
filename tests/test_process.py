import numpy as np

from pixelcraft import palette
from pixelcraft.shade import despeckle, outline, toon
from pixelcraft.sheet import aseprite_json

BANDS = [
    {"above": 0.5, "multiply": "#ffffff"},
    {"above": -1.0, "multiply": "#808080"},
]


def encoded_normal(x, y, z):
    return np.array([[[round((v * 0.5 + 0.5) * 255) for v in (x, y, z)] + [255]]], dtype=np.uint8)


def test_toon_keeps_lit_albedo_and_darkens_the_rest():
    albedo = np.array([[[200, 100, 50, 255]]], dtype=np.uint8)
    lit = toon(albedo, encoded_normal(0, 0, 1), [0, 0, 1], BANDS)
    shadow = toon(albedo, encoded_normal(0, 0, 1), [0, 0, -1], BANDS)
    assert lit[0, 0].tolist() == [200, 100, 50, 255]
    assert (shadow[0, 0, :3] < lit[0, 0, :3]).all()
    assert shadow[0, 0, 3] == 255


def test_outline_outer_grows_the_sprite_and_inner_keeps_its_size():
    image = np.zeros((5, 5, 4), dtype=np.uint8)
    image[2, 2] = [255, 0, 0, 255]
    black = np.array([0, 0, 0], dtype=np.uint8)

    outer = outline(image, "outer", black)
    assert (outer[..., 3] > 0).sum() == 5
    assert outer[2, 2].tolist() == [255, 0, 0, 255]
    assert outer[1, 2].tolist() == [0, 0, 0, 255]
    assert outer[1, 1, 3] == 0

    inner = outline(image, "inner", black)
    assert (inner[..., 3] > 0).sum() == 1
    assert inner[2, 2].tolist() == [0, 0, 0, 255]


def test_palette_build_caps_colours_and_apply_uses_only_them():
    rng = np.random.default_rng(1)
    image = np.dstack([rng.integers(0, 256, (16, 16, 3)), np.full((16, 16), 255)]).astype(np.uint8)
    colours = palette.build(image.reshape(-1, 4)[:, :3], 8)
    mapped = palette.apply(image, colours)
    assert len(colours) <= 8
    assert {tuple(c) for c in mapped.reshape(-1, 4)[:, :3]} <= {tuple(c) for c in colours}


def test_palette_build_keeps_exact_colours_under_the_cap():
    pixels = np.array([[10, 20, 30], [10, 20, 30], [200, 0, 0]], dtype=np.uint8)
    assert palette.build(pixels, 8).tolist() == [[10, 20, 30], [200, 0, 0]]


def test_palette_loads_hex_and_gimp_files(tmp_path):
    (tmp_path / "p.hex").write_text("ff0000\n00ff00\n")
    (tmp_path / "p.gpl").write_text("GIMP Palette\nName: test\n#\n255   0   0\tred\n  0 255   0\tgreen\n")
    assert palette.load(tmp_path / "p.hex").tolist() == [[255, 0, 0], [0, 255, 0]]
    assert palette.load(tmp_path / "p.gpl").tolist() == [[255, 0, 0], [0, 255, 0]]


def test_aseprite_json_lays_out_one_row_per_strip():
    data = aseprite_json({"walk_e": 3, "walk_w": 2}, (10, 20), 10, "sheet.png", [5, 18])
    assert [t["from"] for t in data["meta"]["frameTags"]] == [0, 3]
    assert [t["to"] for t in data["meta"]["frameTags"]] == [2, 4]
    assert data["frames"][4]["frame"] == {"x": 10, "y": 20, "w": 10, "h": 20}
    assert data["frames"][0]["duration"] == 100
    assert data["meta"]["size"] == {"w": 30, "h": 40}


def test_despeckle_recolours_isolated_pixels_only():
    image = np.zeros((4, 5, 4), dtype=np.uint8)
    image[:, :] = [10, 10, 10, 255]
    image[1, 1] = [200, 0, 0, 255]
    image[1:3, 3] = [0, 200, 0, 255]
    cleaned = despeckle(image)
    assert cleaned[1, 1].tolist() == [10, 10, 10, 255]
    assert cleaned[1, 3].tolist() == [0, 200, 0, 255]
    assert cleaned[2, 3].tolist() == [0, 200, 0, 255]
