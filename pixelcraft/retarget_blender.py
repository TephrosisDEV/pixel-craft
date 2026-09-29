"""Retarget an animation from one humanoid armature onto another, inside Blender.

Bones are matched by role (hips, spine, arms, legs…) across Mixamo and Unreal-style names, so
Mixamo downloads and CC0 packs such as Quaternius' Universal Animation Library work on any rig
with either naming. Each source bone's rotation away from its rest pose is replayed in world space
on the target, after bending the target's rest limbs onto the source's (T vs A pose), so rigs
whose facing, bone axes or rest poses differ still line up.
Fingers and other unmatched bones stay at rest; they don't show at sprite size.
"""

import re

import bpy
from mathutils import Matrix, Quaternion, Vector

# Canonical role -> accepted names after normalisation (lowercase, no separators, no mixamorig prefix).
ROLES = {
    "hips": ["hips", "pelvis"],
    "spine": ["spine", "spine01"],
    "spine1": ["spine1", "spine02"],
    "spine2": ["spine2", "spine03"],
    "neck": ["neck", "neck01"],
    "head": ["head"],
}
for side, s in (("left", "l"), ("right", "r")):
    ROLES.update({
        f"{side}shoulder": [f"{side}shoulder", f"clavicle{s}"],
        f"{side}arm": [f"{side}arm", f"upperarm{s}"],
        f"{side}forearm": [f"{side}forearm", f"lowerarm{s}"],
        f"{side}hand": [f"{side}hand", f"hand{s}"],
        f"{side}upleg": [f"{side}upleg", f"thigh{s}"],
        f"{side}leg": [f"{side}leg", f"calf{s}"],
        f"{side}foot": [f"{side}foot", f"foot{s}"],
        f"{side}toe": [f"{side}toebase", f"ball{s}"],
    })
REQUIRED = ("hips", "head", "leftupleg", "rightupleg")
ROTATION_CHANNEL = {"QUATERNION": "rotation_quaternion", "AXIS_ANGLE": "rotation_axis_angle"}

# Joint each role's limb points towards, first available wins; leaves reuse their parent's correction.
LIMB_CHILDREN = {
    "hips": ["spine", "spine1", "spine2", "neck", "head"],
    "spine": ["spine1", "spine2", "neck", "head"],
    "spine1": ["spine2", "neck", "head"],
    "spine2": ["neck", "head"],
    "neck": ["head"],
}
LEAF_PARENT = {"head": "neck"}
POSTURE = {"hips", "spine", "spine1", "spine2", "neck", "head"}
ARMS = {f"{side}{part}" for side in ("left", "right") for part in ("shoulder", "arm", "forearm", "hand")}
for side in ("left", "right"):
    LIMB_CHILDREN.update({
        f"{side}shoulder": [f"{side}arm"], f"{side}arm": [f"{side}forearm"], f"{side}forearm": [f"{side}hand"],
        f"{side}upleg": [f"{side}leg"], f"{side}leg": [f"{side}foot"], f"{side}foot": [f"{side}toe"],
    })
    LEAF_PARENT.update({f"{side}hand": f"{side}forearm", f"{side}toe": f"{side}foot"})


def roles(armature) -> dict[str, str]:
    """Role -> bone name for every recognised bone of a humanoid armature."""
    lookup = {alias: role for role, aliases in ROLES.items() for alias in aliases}
    found = {}
    for bone in armature.data.bones:
        key = re.sub(r"[^a-z0-9]", "", re.sub(r"^mixamorig\d*[:_]?", "", bone.name.lower()))
        if key in lookup:
            found.setdefault(lookup[key], bone.name)
    return found


def is_humanoid(armature) -> bool:
    return all(role in roles(armature) for role in REQUIRED)


def facing(armature) -> Vector:
    """World-space horizontal direction the character faces in its rest pose."""
    bones = roles(armature)
    left = armature.matrix_world @ armature.data.bones[bones["leftupleg"]].head_local
    right = armature.matrix_world @ armature.data.bones[bones["rightupleg"]].head_local
    forward = (left - right).cross(Vector((0, 0, 1)))
    forward.z = 0
    return forward.normalized()


def retarget(source, action, target, name, keep_posture=False, arm_motion=1.0):
    """Bake `action` (played on armature `source`) onto `target` as a new action called `name`.

    With `keep_posture`, the target's torso and head keep their own rest pose (a hunch, a lean)
    instead of being straightened onto the source's; limbs are still aligned. `arm_motion` scales
    how far the arms move away from their rest pose (below 1 for creatures with very long arms).
    """
    source_roles, target_roles = roles(source), roles(target)
    shared = [role for role in ROLES if role in source_roles and role in target_roles]
    scene = bpy.context.scene

    _play(source, action)
    src_rest = {r: _world_rest(source, source_roles[r]) for r in shared}
    tgt_rest = {r: _world_rest(target, target_roles[r]) for r in shared}

    # Rotation taking the source character's frame (left, forward, up) onto the target's.
    to_target = (_character_frame(target) @ _character_frame(source).inverted()).to_quaternion()
    # Per bone: rotation that brings the target's rest limb onto the source's rest limb (e.g. A-pose
    # arms up to T-pose), measured between joint positions because imported bone axes are guesses.
    corrections = {}
    for role in shared:
        child = next((c for c in LIMB_CHILDREN.get(role, []) if c in shared), None)
        if keep_posture and role in POSTURE:
            corrections[role] = Quaternion()
            continue
        if child is None:
            corrections[role] = corrections.get(LEAF_PARENT.get(role), Quaternion())
            continue
        source_limb = to_target @ (src_rest[child][0] - src_rest[role][0])
        target_limb = tgt_rest[child][0] - tgt_rest[role][0]
        corrections[role] = target_limb.rotation_difference(source_limb)
    # Hip motion scales with hip height above the feet; model origins aren't always at the feet.
    height_ratio = _hip_height(tgt_rest) / max(_hip_height(src_rest), 1e-6)

    target_action = bpy.data.actions.new(name)
    target_action.use_fake_user = True
    data = target.animation_data or target.animation_data_create()
    for track in data.nla_tracks:
        track.mute = True
    data.action = target_action
    by_bone = {target_roles[r]: r for r in shared}

    target_rotation = _rotation(target.matrix_world)
    target_inverse = target.matrix_world.inverted()
    start, end = (int(round(f)) for f in action.frame_range)
    for frame_number in range(start, end + 1):
        scene.frame_set(frame_number)
        armature_space = {}
        for pose_bone in _parents_first(target):
            bone = pose_bone.bone
            chain = (armature_space[bone.parent.name] @ bone.parent.matrix_local.inverted() @ bone.matrix_local
                     if bone.parent else bone.matrix_local.copy())
            role = by_bone.get(bone.name)
            if role is None:
                basis = Matrix.Identity(4)
            else:
                src_matrix = source.matrix_world @ source.pose.bones[source_roles[role]].matrix
                # The source bone's change from its rest pose, applied in the target's frame.
                change = _rotation(src_matrix) @ src_rest[role][1].inverted()
                if role in ARMS:
                    change = Quaternion().slerp(change, arm_motion)
                world_rotation = to_target @ change @ to_target.inverted() @ corrections[role] @ tgt_rest[role][1]
                head = chain.to_translation()
                if role == "hips":
                    moved = to_target @ (src_matrix.to_translation() - src_rest["hips"][0]) * height_ratio
                    head = target_inverse @ (tgt_rest["hips"][0] + moved)
                desired = Matrix.Translation(head) @ (target_rotation.inverted() @ world_rotation).to_matrix().to_4x4()
                basis = chain.inverted() @ desired
            armature_space[bone.name] = chain @ basis
            pose_bone.matrix_basis = basis
            if role is not None:
                # Key the channel the bone already uses, so the model's own actions keep working.
                pose_bone.keyframe_insert(ROTATION_CHANNEL.get(pose_bone.rotation_mode, "rotation_euler"), frame=frame_number)
                if role == "hips":
                    pose_bone.keyframe_insert("location", frame=frame_number)
    return target_action


def _hip_height(rest):
    feet = [rest[r][0].z for r in ("leftfoot", "rightfoot", "lefttoe", "righttoe") if r in rest]
    return rest["hips"][0].z - (min(feet) if feet else 0.0)


def _play(armature, action):
    data = armature.animation_data or armature.animation_data_create()
    for track in data.nla_tracks:
        track.mute = True
    data.action = action
    if hasattr(data, "action_slot") and data.action_slot is None and len(action.slots):
        data.action_slot = action.slots[0]


def _world_rest(armature, bone_name) -> tuple[Vector, Quaternion]:
    matrix = armature.matrix_world @ armature.data.bones[bone_name].matrix_local
    return matrix.to_translation(), _rotation(matrix)


def _rotation(matrix) -> Quaternion:
    """Rotation of a matrix that may carry the 0.01 scale FBX and glTF imports put on armatures."""
    return matrix.to_3x3().normalized().to_quaternion()


def _character_frame(armature) -> Matrix:
    forward = facing(armature)
    up = Vector((0, 0, 1))
    return Matrix((up.cross(forward), forward, up)).transposed()


def _parents_first(armature):
    ordered, pending = [], [b for b in armature.pose.bones if b.parent is None]
    while pending:
        bone = pending.pop(0)
        ordered.append(bone)
        pending.extend(bone.children)
    return ordered


def plant_feet(armature, action):
    """Pin both feet of a humanoid to where they stand on the action's first frame, re-solving
    each leg (thigh + shin, two-bone IK) on every frame. For attacks and idles on creatures whose
    legs differ from the source rig's, where retargeted leg motion would make the feet skate."""
    bones = roles(armature)
    legs = [(bones[f"{s}upleg"], bones[f"{s}leg"], bones.get(f"{s}foot")) for s in ("left", "right")
            if f"{s}upleg" in bones and f"{s}leg" in bones]
    scene = bpy.context.scene
    _play(armature, action)
    start, end = (int(round(f)) for f in action.frame_range)
    scene.frame_set(start)
    pose = armature.pose.bones
    # Everything planted comes from the first frame: ankle position, knee bend direction, foot angle.
    targets = {thigh: pose[shin].tail.copy() for thigh, shin, _ in legs}
    # Straight legs have no bend direction: knees then bend towards where the character faces.
    forward = (armature.matrix_world.inverted().to_3x3() @ facing(armature)).normalized()
    bends = {thigh: _bend(pose[thigh].head, pose[shin].head, pose[shin].tail) or forward for thigh, shin, _ in legs}
    foot_rotations = {thigh: pose[foot].matrix.to_quaternion() for thigh, _, foot in legs if foot}
    for frame_number in range(start, end + 1):
        scene.frame_set(frame_number)
        for thigh, shin, foot in legs:
            foot_rotation = foot_rotations.get(thigh)
            _solve_leg(pose[thigh], pose[shin], targets[thigh], bends[thigh])
            if foot:
                matrix = pose[foot].matrix
                pose[foot].matrix = Matrix.Translation(matrix.to_translation()) @ foot_rotation.to_matrix().to_4x4()
                bpy.context.view_layer.update()
            for name in (thigh, shin, foot):
                if name:
                    pose[name].keyframe_insert(ROTATION_CHANNEL.get(pose[name].rotation_mode, "rotation_euler"), frame=frame_number)


def _bend(hip, knee, ankle):
    """Direction the knee points away from the hip-ankle line, or None for a straight leg."""
    along = (ankle - hip).normalized()
    offset = (knee - hip) - along * (knee - hip).dot(along)
    return offset.normalized() if offset.length > 1e-4 * (ankle - hip).length else None


def _solve_leg(thigh, shin, target, bend):
    """Bend thigh and shin (armature space) so the ankle reaches `target` with the knee pointing along `bend`."""
    hip, knee = thigh.head.copy(), shin.head.copy()
    upper, lower = (knee - hip).length, (shin.tail - knee).length
    reach = target - hip
    distance = min(reach.length, (upper + lower) * 0.999)
    along = reach.normalized()
    bend = bend - along * bend.dot(along)
    if bend.length < 1e-6:
        return
    a = (upper ** 2 - lower ** 2 + distance ** 2) / (2 * distance)
    new_knee = hip + along * a + bend.normalized() * max(upper ** 2 - a ** 2, 0) ** 0.5
    _rotate_bone(thigh, (knee - hip).rotation_difference(new_knee - hip))
    _rotate_bone(shin, (shin.tail - shin.head).rotation_difference(target - shin.head))


def _rotate_bone(pose_bone, rotation):
    head = pose_bone.head.copy()
    pose_bone.matrix = Matrix.Translation(head) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pose_bone.matrix
    bpy.context.view_layer.update()
