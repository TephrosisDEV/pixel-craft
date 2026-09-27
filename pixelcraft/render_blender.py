"""Render a rigged model into per-frame albedo and normal passes for pixel sprites.

Runs inside Blender:  blender -b -P pixelcraft/render_blender.py -- config.json
or with the bpy module: python pixelcraft/render_blender.py config.json

Output (under config.output/render/):
  manifest.json
  <action>/<direction>/<frame>_albedo.png   flat colour, sRGB, binary alpha
  <action>/<direction>/<frame>_normal.png   camera-space normal (x right, y up, z towards viewer), rgb = n * 0.5 + 0.5

Every pixel is sampled once at its centre with no filtering, so edges stay hard.
Lighting is not rendered: `pixelcraft process` toon-shades from the normal pass,
the same split Dead Cells used.
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

# Facing angle measured in screen terms: 0 = towards the viewer, 90 = screen right.
FACING_NAMES = {round(i * 22.5, 1): name for i, name in enumerate(
    ["s", "sse", "se", "ese", "e", "ene", "ne", "nne", "n", "nnw", "nw", "wnw", "w", "wsw", "sw", "ssw"]
)}
FRONT_AXIS_ANGLE = {"-Y": 270.0, "+Y": 90.0, "+X": 0.0, "-X": 180.0}

DEFAULTS = {
    "height": 64,
    "directions": 8,
    "start_angle": None,
    "pitch": 30.0,
    "front_axis": "-Y",
    "frame_step": 2,
    "padding": 2,
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    config_path = Path(argv[0]).resolve()
    config = json.loads(config_path.read_text())
    base = config_path.parent
    opts = {**DEFAULTS, **config.get("render", {})}
    out_dir = (base / config["output"] / "render").resolve()

    load_scene(base / config["model"], {name: base / path for name, path in config.get("animations", {}).items()})
    scene = bpy.context.scene
    armature = next((o for o in scene.objects if o.type == "ARMATURE"), None)
    meshes = [o for o in scene.objects if o.type == "MESH" and not o.hide_render]
    if not meshes:
        sys.exit("render: no mesh objects in the scene")

    actions = collect_actions(armature, config.get("animations"), opts["frame_step"])
    directions = direction_list(opts["directions"], opts["start_angle"])
    pitch = min(max(float(opts["pitch"]), 0.0), 89.0)

    camera = setup_camera(scene)
    setup_render(scene)
    albedo_materials(meshes)
    normal_material = make_normal_material()

    unit = world_height(scene, armature, meshes, actions) / opts["height"]
    bases = {d["name"]: camera_basis(d["angle"], opts["front_axis"], pitch) for d in directions}
    x0, x1, y0, y1 = canvas_bounds(scene, armature, meshes, actions, bases.values(), unit, opts["padding"])
    width, height = x1 - x0, y1 - y0
    scene.render.resolution_x, scene.render.resolution_y = width, height
    camera.data.ortho_scale = max(width, height) * unit

    view_layer = bpy.context.view_layer
    for action in actions:
        assign_action(armature, action)
        for direction in directions:
            right, up, forward = bases[direction["name"]]
            place_camera(camera, right, up, forward, ((x0 + x1) / 2 * unit, (y0 + y1) / 2 * unit), unit * 1000)
            for index, frame in enumerate(action["frames"]):
                scene.frame_set(frame)
                stem = out_dir / action["name"] / direction["name"] / f"{index:04d}"
                view_layer.material_override = None
                scene.view_settings.view_transform = "Standard"
                render_to(scene, f"{stem}_albedo.png")
                view_layer.material_override = normal_material
                scene.view_settings.view_transform = "Raw"
                render_to(scene, f"{stem}_normal.png")

    manifest = {
        "canvas": [width, height],
        "pivot": [-x0, y1],
        "unit": unit,
        "pitch": pitch,
        "fps": scene.render.fps / opts["frame_step"],
        "directions": directions,
        "actions": [{"name": a["name"], "frames": len(a["frames"])} for a in actions],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"render: {len(actions)} actions x {len(directions)} directions, canvas {width}x{height} -> {out_dir}")


def load_scene(model_path, animation_paths):
    """Open or import the model, then pull each animation file's action onto it, named after its key."""
    if model_path.suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(model_path))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        import_file(model_path)

    for name, path in animation_paths.items():
        before_objects = set(bpy.data.objects)
        before_actions = set(bpy.data.actions)
        import_file(path)
        new_actions = [a for a in bpy.data.actions if a not in before_actions]
        if not new_actions:
            sys.exit(f"render: no animation found in {path}")
        new_actions[0].name = name
        new_actions[0].use_fake_user = True
        for obj in set(bpy.data.objects) - before_objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def import_file(path):
    suffix = path.suffix.lower()
    if suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        sys.exit(f"render: unsupported file type {path}")


def collect_actions(armature, wanted, frame_step):
    """Actions to render with their sampled frames, last frame excluded: loops end on their first pose.

    A model without an armature renders one still frame.
    """
    if armature is None or not bpy.data.actions:
        return [{"name": "static", "action": None, "frames": [bpy.context.scene.frame_start]}]
    names = list(wanted) if wanted else [a.name for a in bpy.data.actions]
    actions = []
    for name in names:
        action = bpy.data.actions[name]
        start, end = (int(round(f)) for f in action.frame_range)
        actions.append({"name": name, "action": action, "frames": list(range(start, end, frame_step)) or [start]})
    return actions


def assign_action(armature, action):
    if action["action"] is None:
        return
    data = armature.animation_data or armature.animation_data_create()
    data.action = action["action"]
    if hasattr(data, "action_slot") and data.action_slot is None and len(action["action"].slots):
        data.action_slot = action["action"].slots[0]


def direction_list(count, start_angle):
    """Evenly spaced facing angles. Two directions default to side view (east, west)."""
    start = start_angle if start_angle is not None else (90.0 if count == 2 else 0.0)
    directions = []
    for i in range(count):
        angle = round((start + i * 360.0 / count) % 360.0, 1)
        directions.append({"name": FACING_NAMES.get(angle, f"a{int(round(angle)):03d}"), "angle": angle})
    return directions


def camera_basis(facing, front_axis, pitch):
    """Right, up and forward vectors of a camera that sees the model facing `facing` degrees."""
    azimuth = math.radians(FRONT_AXIS_ANGLE[front_axis] - facing)
    elevation = math.radians(pitch)
    forward = -Vector((
        math.cos(elevation) * math.cos(azimuth),
        math.cos(elevation) * math.sin(azimuth),
        math.sin(elevation),
    ))
    right = forward.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(forward).normalized()
    return right, up, forward


def place_camera(camera, right, up, forward, centre, distance):
    rotation = Matrix((right, up, -forward)).transposed().to_4x4()
    location = right * centre[0] + up * centre[1] - forward * distance
    camera.matrix_world = Matrix.Translation(location) @ rotation
    camera.data.clip_end = distance * 2


def sampled_corners(scene, armature, meshes, actions):
    """World-space bounding-box corners of every mesh on every sampled frame of every action."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for action in actions:
        assign_action(armature, action)
        for frame in action["frames"]:
            scene.frame_set(frame)
            for obj in meshes:
                evaluated = obj.evaluated_get(depsgraph)
                for corner in evaluated.bound_box:
                    yield evaluated.matrix_world @ Vector(corner)


def world_height(scene, armature, meshes, actions):
    """Model height at the first frame of the first action: the size that `height` pixels maps to."""
    zs = [c.z for c in sampled_corners(scene, armature, meshes, [{**actions[0], "frames": actions[0]["frames"][:1]}])]
    return max(zs) - min(zs)


def canvas_bounds(scene, armature, meshes, actions, bases, unit, padding):
    """One pixel-aligned canvas that fits every frame from every direction, origin on a pixel corner."""
    corners = list(sampled_corners(scene, armature, meshes, actions))
    xs, ys = [], []
    for right, up, _ in bases:
        xs += [c.dot(right) / unit for c in corners]
        ys += [c.dot(up) / unit for c in corners]
    return (
        math.floor(min(xs)) - padding, math.ceil(max(xs)) + padding,
        math.floor(min(ys)) - padding, math.ceil(max(ys)) + padding,
    )


def setup_camera(scene):
    data = bpy.data.cameras.new("pixelcraft")
    data.type = "ORTHO"
    data.sensor_fit = "AUTO"
    camera = bpy.data.objects.new("pixelcraft", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def setup_render(scene):
    """One centre sample per pixel, no filtering, no dithering: every pixel is fully one surface or empty.

    Persistent data stays off: with it on, switching the material override between passes
    renders some materials black on later frames.
    """
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.cycles.filter_width = 0.01
    scene.cycles.max_bounces = 0
    scene.cycles.device = "CPU"
    scene.render.film_transparent = True
    scene.render.dither_intensity = 0.0
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def render_to(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def albedo_materials(meshes):
    """Rewire every material to emit its flat base colour, with nearest-neighbour texture sampling."""
    for material in {slot.material for obj in meshes for slot in obj.material_slots if slot.material}:
        if not material.use_nodes:
            colour = material.diffuse_color
            material.use_nodes = True
            nodes = material.node_tree.nodes
            nodes.clear()
            emit_colour(material, None, colour)
            continue
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                node.interpolation = "Closest"
        shader = next((n for n in material.node_tree.nodes if n.type in ("BSDF_PRINCIPLED", "BSDF_DIFFUSE")), None)
        if shader is None:
            continue
        base = shader.inputs["Base Color" if shader.type == "BSDF_PRINCIPLED" else "Color"]
        alpha = shader.inputs.get("Alpha")
        emit_colour(
            material,
            base.links[0].from_socket if base.is_linked else None,
            base.default_value,
            alpha.links[0].from_socket if alpha is not None and alpha.is_linked else None,
        )


def emit_colour(material, colour_socket, colour_value, alpha_socket=None):
    tree = material.node_tree
    output = next((n for n in tree.nodes if n.type == "OUTPUT_MATERIAL"), None) or tree.nodes.new("ShaderNodeOutputMaterial")
    emission = tree.nodes.new("ShaderNodeEmission")
    if colour_socket is not None:
        tree.links.new(colour_socket, emission.inputs["Color"])
    else:
        emission.inputs["Color"].default_value = colour_value
    surface = emission.outputs["Emission"]
    if alpha_socket is not None:
        mix = tree.nodes.new("ShaderNodeMixShader")
        transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
        tree.links.new(alpha_socket, mix.inputs["Fac"])
        tree.links.new(transparent.outputs["BSDF"], mix.inputs[1])
        tree.links.new(surface, mix.inputs[2])
        surface = mix.outputs["Shader"]
    tree.links.new(surface, output.inputs["Surface"])


def make_normal_material():
    """Emits the camera-space shading normal encoded as colour; rendered with the Raw view transform."""
    material = bpy.data.materials.new("pixelcraft_normal")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    transform = tree.nodes.new("ShaderNodeVectorTransform")
    transform.vector_type = "NORMAL"
    transform.convert_from = "WORLD"
    transform.convert_to = "CAMERA"
    encode = tree.nodes.new("ShaderNodeVectorMath")
    encode.operation = "MULTIPLY_ADD"
    # Cycles camera space has +Z pointing into the scene; flip it so camera-facing normals have +Z.
    encode.inputs[1].default_value = (0.5, 0.5, -0.5)
    encode.inputs[2].default_value = (0.5, 0.5, 0.5)
    emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(geometry.outputs["Normal"], transform.inputs["Vector"])
    tree.links.new(transform.outputs["Vector"], encode.inputs[0])
    tree.links.new(encode.outputs["Vector"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


if __name__ == "__main__":
    main()
