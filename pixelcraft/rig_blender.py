"""Rig a model with a Mixamo-named humanoid skeleton from joint positions, inside Blender.

    python pixelcraft/rig_blender.py rig.json          (bpy module)
    blender -b -P pixelcraft/rig_blender.py -- rig.json

rig.json: {"model": "beast.glb", "output": "beast_rigged.blend", "joints": {"Hips": [x, y, z], ...}}
with world positions (Z up) for Hips, Spine, Spine1, Spine2, Neck, Head, HeadTop and, per side
(Left/Right), Arm, ForeArm, Hand, HandEnd, UpLeg, Leg, Foot, ToeBase. Shoulders and toe tips
are derived. The result retargets any Mixamo or Unreal-named animation through `pixelcraft`.

A stopgap until automatic rigging (Make-It-Animatable, UniRig) runs on a GPU: joints are placed
by hand. Skinning is automatic and built for generated meshes, which are fragment soups that
Blender's own heat weighting fails on.
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

TORSO = {"Hips": ("Hips", "Spine", None), "Spine": ("Spine", "Spine1", "Hips"), "Spine1": ("Spine1", "Spine2", "Spine"),
         "Spine2": ("Spine2", "Neck", "Spine1"), "Neck": ("Neck", "Head", "Spine2"), "Head": ("Head", "HeadTop", "Neck")}


def bones():
    """name: (head joint, tail joint, parent) for the full skeleton."""
    skeleton = dict(TORSO)
    for s in ("Left", "Right"):
        skeleton.update({
            f"{s}Shoulder": (f"{s}Shoulder", f"{s}Arm", "Spine2"), f"{s}Arm": (f"{s}Arm", f"{s}ForeArm", f"{s}Shoulder"),
            f"{s}ForeArm": (f"{s}ForeArm", f"{s}Hand", f"{s}Arm"), f"{s}Hand": (f"{s}Hand", f"{s}HandEnd", f"{s}ForeArm"),
            f"{s}UpLeg": (f"{s}UpLeg", f"{s}Leg", "Hips"), f"{s}Leg": (f"{s}Leg", f"{s}Foot", f"{s}UpLeg"),
            f"{s}Foot": (f"{s}Foot", f"{s}ToeBase", f"{s}Leg"), f"{s}ToeBase": (f"{s}ToeBase", f"{s}ToeEnd", f"{s}Foot"),
        })
    return skeleton


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    config_path = Path(argv[0]).resolve()
    config = json.loads(config_path.read_text())
    joints = {name: Vector(position) for name, position in config["joints"].items()}
    for side in ("Left", "Right"):
        joints[f"{side}Shoulder"] = joints["Spine2"] + (joints[f"{side}Arm"] - joints["Spine2"]) * 0.35
        foot_direction = (joints[f"{side}ToeBase"] - joints[f"{side}Foot"]).normalized()
        joints[f"{side}ToeEnd"] = joints[f"{side}ToeBase"] + foot_direction * 0.05 * (joints["Head"].z - joints[f"{side}ToeBase"].z)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(config_path.parent / config["model"]))
    mesh = next(o for o in bpy.data.objects if o.type == "MESH")
    skeleton = bones()
    armature = build_armature(skeleton, joints)
    skin(mesh, armature, skeleton, joints)
    for obj in [o for o in bpy.data.objects if o.type == "EMPTY"]:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(config_path.parent / config["output"]))
    print(f"rig: {len(skeleton)} bones on {len(mesh.data.vertices)} vertices -> {config['output']}")


def build_armature(skeleton, joints):
    data = bpy.data.armatures.new("Armature")
    armature = bpy.data.objects.new("Armature", data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (head, tail, _) in skeleton.items():
        bone = data.edit_bones.new(f"mixamorig:{name}")
        bone.head, bone.tail = joints[head], joints[tail]
    for name, (_, _, parent) in skeleton.items():
        if parent:
            data.edit_bones[f"mixamorig:{name}"].parent = data.edit_bones[f"mixamorig:{parent}"]
    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


def skin(mesh, armature, skeleton, joints):
    """Each vertex takes its nearest bone on its own side of the body, then blends only with that
    bone's parent and children, so neighbouring limbs (the two legs, an arm and a leg) never mix."""
    verts = np.array([mesh.matrix_world @ v.co for v in mesh.data.vertices])
    names = list(skeleton)
    heads = np.array([joints[skeleton[n][0]] for n in names])
    tails = np.array([joints[skeleton[n][1]] for n in names])
    segment = tails - heads
    t = np.clip(((verts[:, None, :] - heads[None]) * segment[None]).sum(-1) / (segment ** 2).sum(-1)[None], 0, 1)
    distance = np.linalg.norm(verts[:, None, :] - (heads[None] + t[..., None] * segment[None]), axis=-1)
    side = np.array([1 if n.startswith("Left") else -1 if n.startswith("Right") else 0 for n in names])
    height = max(j.z for j in joints.values()) - min(j.z for j in joints.values())
    wrong_side = (side[None] * (verts[:, :1] - joints["Hips"].x)) < -0.02 * height
    nearest = np.argmin(np.where(wrong_side, np.inf, distance), axis=1)
    family = np.eye(len(names), dtype=bool)
    for i, name in enumerate(names):
        parent = skeleton[name][2]
        if parent:
            family[i, names.index(parent)] = family[names.index(parent), i] = True
    weights = np.where(family[nearest] & ~wrong_side, 1 / (distance ** 4 + 1e-12), 0)
    weights /= weights.sum(1, keepdims=True)
    for b, name in enumerate(names):
        group = mesh.vertex_groups.new(name=f"mixamorig:{name}")
        for v in np.nonzero(weights[:, b] > 0.02)[0]:
            group.add([int(v)], float(weights[v, b]), "REPLACE")
    mesh.parent = armature
    mesh.modifiers.new("Armature", "ARMATURE").object = armature


if __name__ == "__main__":
    main()
