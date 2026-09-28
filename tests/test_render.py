"""End-to-end render of the example knight. Needs the bpy module (pip install bpy) in the test environment."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("bpy")

ROOT = Path(__file__).resolve().parents[1]
KNIGHT_COLOURS = {(224, 176, 138), (138, 149, 168), (156, 47, 58), (46, 49, 64), (91, 58, 41), (214, 221, 230), (201, 161, 59)}


def test_render_gives_flat_hard_edged_frames_for_each_direction(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "examples" / "make_test_knight.py"), str(tmp_path / "knight.blend")], check=True)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"model": "knight.blend", "output": "out", "render": {"height": 48, "directions": 8, "frame_step": 2}}))
    subprocess.run([sys.executable, str(ROOT / "pixelcraft" / "render_blender.py"), str(config)], check=True)

    render = tmp_path / "out" / "render"
    manifest = json.loads((render / "manifest.json").read_text())
    assert [d["name"] for d in manifest["directions"]] == ["s", "se", "e", "ne", "n", "nw", "w", "sw"]
    assert {a["name"] for a in manifest["actions"]} == {"idle", "walk", "attack"}

    for path in render.glob("*/*/*_albedo.png"):
        frame = np.array(Image.open(path))
        assert list(frame.shape[1::-1]) == manifest["canvas"]
        assert set(np.unique(frame[..., 3])) <= {0, 255}
        assert {tuple(int(v) for v in c) for c in frame[frame[..., 3] > 0][:, :3]} <= KNIGHT_COLOURS


def test_retargeting_an_animation_onto_its_own_rig_reproduces_it(tmp_path):
    for name in ("knight.blend", "source.blend"):
        subprocess.run([sys.executable, str(ROOT / "examples" / "make_test_knight.py"), str(tmp_path / name)], check=True)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "model": "knight.blend",
        "animations": {"walk_retargeted": "source.blend#walk"},
        "actions": ["walk", "walk_retargeted"],
        "output": "out",
        "render": {"height": 48, "directions": 4, "frame_step": 2},
    }))
    subprocess.run([sys.executable, str(ROOT / "pixelcraft" / "render_blender.py"), str(config)], check=True)

    render = tmp_path / "out" / "render"
    overlaps = []
    for original in render.glob("walk/*/*_albedo.png"):
        a = np.array(Image.open(original))[..., 3] > 0
        b = np.array(Image.open(render / "walk_retargeted" / original.parent.name / original.name))[..., 3] > 0
        overlaps.append((a & b).sum() / (a | b).sum())
    assert len(overlaps) == 4 * 16
    assert min(overlaps) > 0.97


def test_ground_sheet_under_the_feet_is_stripped(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "examples" / "make_test_knight.py"), str(tmp_path / "knight.blend")], check=True)
    add_ground = (
        "import bpy, sys; bpy.ops.wm.open_mainfile(filepath=sys.argv[1]); "
        "bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0.01)); "
        "bpy.ops.wm.save_as_mainfile(filepath=sys.argv[2])"
    )
    subprocess.run([sys.executable, "-c", add_ground, str(tmp_path / "knight.blend"), str(tmp_path / "grounded.blend")], check=True)

    canvases = []
    for model in ("knight.blend", "grounded.blend"):
        config = tmp_path / f"{model}.json"
        config.write_text(json.dumps({"model": model, "actions": ["idle"], "output": f"out_{model}",
                                      "render": {"height": 32, "directions": 2, "frame_step": 8}}))
        subprocess.run([sys.executable, str(ROOT / "pixelcraft" / "render_blender.py"), str(config)], check=True)
        canvases.append(json.loads((tmp_path / f"out_{model}" / "render" / "manifest.json").read_text())["canvas"])
    assert canvases[0] == canvases[1]
