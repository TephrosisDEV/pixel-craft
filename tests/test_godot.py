"""The Godot sprite node, run in a real headless Godot on a rendered knight.

Needs the bpy module and PIXELCRAFT_GODOT pointing at a Godot 4.x binary; skipped otherwise.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("bpy")
GODOT = os.environ.get("PIXELCRAFT_GODOT")
pytestmark = pytest.mark.skipif(not GODOT, reason="set PIXELCRAFT_GODOT to a Godot 4 binary")
ROOT = Path(__file__).resolve().parents[1]

CHECK = """extends SceneTree

func _initialize() -> void:
	var sprite = load("res://pixelcraft_sprite.gd").new()
	sprite.sheet_json = "res://knight/sheet.json"
	root.add_child(sprite)
	await process_frame
	var frames: SpriteFrames = sprite.sprite_frames
	for name in frames.get_animation_names():
		var canvas: CanvasTexture = frames.get_frame_texture(name, 0).atlas
		print("ANIM ", name, " ", frames.get_frame_count(name), " ", frames.get_animation_loop(name), " ", canvas.normal_texture != null)
	print("OFFSET ", sprite.offset)
	quit()
"""


def test_sprite_node_builds_animations_with_normal_maps(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "examples" / "make_test_knight.py"), str(tmp_path / "knight.blend")], check=True)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"model": "knight.blend", "actions": ["walk", "attack"], "output": "out",
                                  "render": {"height": 32, "directions": 1, "start_angle": 90, "pitch": 0, "frame_step": 4}}))
    subprocess.run([sys.executable, str(ROOT / "pixelcraft" / "render_blender.py"), str(config)], check=True)
    subprocess.run([sys.executable, "-m", "pixelcraft", "process", str(config)], check=True, cwd=ROOT)

    project = tmp_path / "godot"
    (project / "knight").mkdir(parents=True)
    (project / "project.godot").write_text('config_version=5\n\n[application]\nconfig/name="test"\n')
    shutil.copy(ROOT / "godot" / "pixelcraft_sprite.gd", project)
    for name in ("sheet.png", "sheet.json", "normal.png"):
        shutil.copy(tmp_path / "out" / name, project / "knight")
    (project / "check.gd").write_text(CHECK)
    subprocess.run([GODOT, "--headless", "--import", "--path", str(project)], capture_output=True, timeout=300)
    output = subprocess.run([GODOT, "--headless", "--path", str(project), "--script", "res://check.gd"],
                            capture_output=True, text=True, timeout=300).stdout

    manifest = json.loads((tmp_path / "out" / "render" / "manifest.json").read_text())
    tags = json.loads((tmp_path / "out" / "sheet.json").read_text())["meta"]["frameTags"]
    counts = {tag["name"]: tag["to"] - tag["from"] + 1 for tag in tags}
    assert f"ANIM walk_e {counts['walk_e']} true true" in output
    assert f"ANIM attack_e {counts['attack_e']} false true" in output
    assert f"OFFSET ({-manifest['pivot'][0]:.1f}, {-manifest['pivot'][1]:.1f})" in output
