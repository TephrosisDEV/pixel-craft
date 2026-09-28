"""Build a blocky rigged knight with idle, walk and attack actions, for testing the pipeline.

    python examples/make_test_knight.py examples/knight.blend      (bpy module)
    blender -b -P examples/make_test_knight.py -- examples/knight.blend

Faces -Y like a Mixamo import. Every part is a box parented to a bone, coloured flat. Bones use Mixamo names.
"""

import math
import sys

import bpy
from mathutils import Matrix, Vector

COLOURS = {
    "skin": "#e0b08a",
    "steel": "#8a95a8",
    "tunic": "#9c2f3a",
    "dark": "#2e3140",
    "boots": "#5b3a29",
    "blade": "#d6dde6",
    "gold": "#c9a13b",
}

# name: (head, tail, parent)
BONES = {
    "Hips": ((0, 0, 0.95), (0, 0, 1.15), None),
    "Spine": ((0, 0, 1.15), (0, 0, 1.55), "Hips"),
    "Head": ((0, 0, 1.55), (0, 0, 1.95), "Spine"),
    "LeftArm": ((0.3, 0, 1.5), (0.3, 0, 1.2), "Spine"),
    "LeftForeArm": ((0.3, 0, 1.2), (0.3, 0, 0.95), "LeftArm"),
    "RightArm": ((-0.3, 0, 1.5), (-0.3, 0, 1.2), "Spine"),
    "RightForeArm": ((-0.3, 0, 1.2), (-0.3, 0, 0.95), "RightArm"),
    "LeftUpLeg": ((0.12, 0, 0.95), (0.12, 0, 0.5), "Hips"),
    "LeftLeg": ((0.12, 0, 0.5), (0.12, 0, 0.05), "LeftUpLeg"),
    "RightUpLeg": ((-0.12, 0, 0.95), (-0.12, 0, 0.5), "Hips"),
    "RightLeg": ((-0.12, 0, 0.5), (-0.12, 0, 0.05), "RightUpLeg"),
}

# bone: [(centre, size, colour), ...] in world space at rest
PARTS = {
    "Hips": [((0, 0, 1.02), (0.44, 0.26, 0.2), "tunic")],
    "Spine": [((0, 0, 1.33), (0.5, 0.3, 0.4), "steel"), ((0, -0.155, 1.3), (0.16, 0.02, 0.24), "tunic")],
    "Head": [
        ((0, 0, 1.72), (0.34, 0.32, 0.34), "skin"),
        ((0, 0.02, 1.86), (0.38, 0.36, 0.14), "steel"),
        ((0.07, -0.165, 1.74), (0.05, 0.02, 0.06), "dark"),
        ((-0.07, -0.165, 1.74), (0.05, 0.02, 0.06), "dark"),
    ],
    "LeftArm": [((0.3, 0, 1.36), (0.16, 0.18, 0.32), "steel")],
    "LeftForeArm": [((0.3, 0, 1.07), (0.14, 0.16, 0.26), "skin")],
    "RightArm": [((-0.3, 0, 1.36), (0.16, 0.18, 0.32), "steel")],
    "RightForeArm": [
        ((-0.3, 0, 1.07), (0.14, 0.16, 0.26), "skin"),
        ((-0.3, -0.12, 0.95), (0.06, 0.1, 0.06), "gold"),
        ((-0.3, -0.19, 0.95), (0.2, 0.04, 0.04), "gold"),
        ((-0.3, -0.5, 0.95), (0.06, 0.6, 0.03), "blade"),
    ],
    "LeftUpLeg": [((0.12, 0, 0.72), (0.17, 0.2, 0.44), "tunic")],
    "LeftLeg": [((0.12, 0, 0.28), (0.15, 0.18, 0.46), "boots"), ((0.12, -0.05, 0.04), (0.16, 0.28, 0.08), "boots")],
    "RightUpLeg": [((-0.12, 0, 0.72), (0.17, 0.2, 0.44), "tunic")],
    "RightLeg": [((-0.12, 0, 0.28), (0.15, 0.18, 0.46), "boots"), ((-0.12, -0.05, 0.04), (0.16, 0.28, 0.08), "boots")],
}


def main():
    out_path = (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    armature = build_armature(scene)
    materials = {name: flat_material(name, hex_colour) for name, hex_colour in COLOURS.items()}
    for bone_name, boxes in PARTS.items():
        for i, (centre, size, colour) in enumerate(boxes):
            attach_box(scene, armature, bone_name, f"{bone_name}.{i}", centre, size, materials[colour])
    animate(armature)
    bpy.ops.wm.save_as_mainfile(filepath=out_path)
    print(f"saved {out_path}")


def build_armature(scene):
    data = bpy.data.armatures.new("Armature")
    armature = bpy.data.objects.new("Armature", data)
    scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (head, tail, parent) in BONES.items():
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = data.edit_bones[parent]
            bone.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    return armature


def flat_material(name, hex_colour):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*(srgb_to_linear(int(hex_colour[i:i + 2], 16) / 255) for i in (1, 3, 5)), 1.0)
    return material


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def attach_box(scene, armature, bone_name, name, centre, size, material):
    cx, cy, cz = centre
    hx, hy, hz = (s / 2 for s in size)
    verts = [(cx + x * hx, cy + y * hy, cz + z * hz) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    bone = armature.data.bones[bone_name]
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    rest = armature.matrix_world @ bone.matrix_local @ Matrix.Translation(Vector((0, bone.length, 0)))
    obj.matrix_parent_inverse = rest.inverted()


def animate(armature):
    """Keyframe three actions. Loops end on their first pose; the renderer drops that last frame."""
    data = armature.animation_data_create()

    def key(action_name, frames):
        action = bpy.data.actions.new(action_name)
        action.use_fake_user = True
        data.action = action
        for frame, pose in frames:
            for pose_bone in armature.pose.bones:
                pose_bone.rotation_euler = (0, 0, 0)
                pose_bone.location = (0, 0, 0)
            for bone_name, (rotation, location) in pose.items():
                pose_bone = armature.pose.bones[bone_name]
                pose_bone.rotation_euler = [math.radians(a) for a in rotation]
                pose_bone.location = location
            for pose_bone in armature.pose.bones:
                pose_bone.keyframe_insert("rotation_euler", frame=frame)
                pose_bone.keyframe_insert("location", frame=frame)

    r = lambda x=0, y=0, z=0, loc=(0, 0, 0): ((x, y, z), loc)  # noqa: E731

    key("idle", [
        (1, {"RightArm": r(x=-10), "RightForeArm": r(x=-40), "LeftArm": r(x=5)}),
        (16, {"Hips": r(loc=(0, -0.03, 0)), "Spine": r(x=3), "RightArm": r(x=-12), "RightForeArm": r(x=-44), "LeftArm": r(x=8)}),
        (31, {"RightArm": r(x=-10), "RightForeArm": r(x=-40), "LeftArm": r(x=5)}),
    ])

    def stride(sign, lift):
        return {
            "Hips": r(loc=(0, lift, 0)),
            "LeftUpLeg": r(x=30 * sign), "LeftLeg": r(x=-25 if sign < 0 else -5),
            "RightUpLeg": r(x=-30 * sign), "RightLeg": r(x=-25 if sign > 0 else -5),
            "LeftArm": r(x=-25 * sign), "RightArm": r(x=20 * sign - 10), "RightForeArm": r(x=-40),
        }

    key("walk", [(1, stride(1, 0)), (9, stride(0, 0.04)), (17, stride(-1, 0)), (25, stride(0, 0.04)), (33, stride(1, 0))])

    key("attack", [
        (1, {"RightArm": r(x=-10), "RightForeArm": r(x=-40)}),
        (8, {"Spine": r(z=-25), "RightArm": r(x=-150, z=-20), "RightForeArm": r(x=-30), "LeftUpLeg": r(x=-15)}),
        (12, {"Spine": r(z=30), "RightArm": r(x=-60, z=40), "RightForeArm": r(x=-10), "LeftUpLeg": r(x=20), "RightUpLeg": r(x=-15)}),
        (18, {"Spine": r(z=20), "RightArm": r(x=-40, z=30), "RightForeArm": r(x=-20), "LeftUpLeg": r(x=15)}),
        (27, {"RightArm": r(x=-10), "RightForeArm": r(x=-40)}),
    ])
    data.action = None


if __name__ == "__main__":
    main()
