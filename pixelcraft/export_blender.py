"""Export the prepared model (cleaned, remeshed, rigged, with its retargeted actions) as one GLB.

For trying looks live in GodotPixelRenderer or Godot itself: everything the render step fixed
(ground, specks, shimmer, posture, planted feet) is baked in. Materials are swapped for a plain
base-colour material during export, since the render step's emission materials don't travel.
"""

import bpy

from remesh_blender import COLOUR


def export_glb(path, meshes, armature):
    originals = {obj: [slot.material for slot in obj.material_slots] for obj in meshes}
    for obj in meshes:
        for slot in obj.material_slots:
            if slot.material is not None:
                slot.material = _base_colour_material(slot.material)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in [*meshes, *([armature] if armature else [])]:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                              export_animations=True, export_animation_mode="ACTIONS")

    for obj, materials in originals.items():
        for slot, material in zip(obj.material_slots, materials):
            slot.material = material


def _base_colour_material(source):
    """A Principled material whose base colour comes from `source`'s colour attribute or texture."""
    material = bpy.data.materials.new(f"{source.name}_export")
    material.use_nodes = True
    tree = material.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 1.0
    nodes = source.node_tree.nodes if source.use_nodes else []
    attribute = next((n for n in nodes if n.type == "ATTRIBUTE" and n.attribute_name == COLOUR), None)
    image = next((n.image for n in nodes if n.type == "TEX_IMAGE" and n.image is not None), None)
    if attribute is not None:
        colour = tree.nodes.new("ShaderNodeVertexColor")
        colour.layer_name = COLOUR
        tree.links.new(colour.outputs["Color"], bsdf.inputs["Base Color"])
    elif image is not None:
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image, texture.interpolation = image, "Closest"
        tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        emission = next((n for n in nodes if n.type == "EMISSION"), None)
        if emission is not None:
            bsdf.inputs["Base Color"].default_value = emission.inputs["Color"].default_value
    return material
