"""Rebuild generated meshes as one clean surface with smooth colour, inside Blender.

Image-to-3D output is thousands of small, overlapping fragments, each mapped to its own patch of
texture. At sprite size every pixel lands on a different fragment from frame to frame, so the
sprite shimmers. Voxel remeshing fuses the fragments into one surface; the texture is baked
into per-vertex colour and smoothed, so colour varies smoothly over the body. Skin weights are
copied from the nearest original vertices, so an existing rig keeps working.
"""

import bpy
import numpy as np
from mathutils.kdtree import KDTree

COLOUR = "pixelcraft_colour"


def remesh(obj, voxel_size, smooth_iterations=4, linear_textures=False, surface_smoothing=3):
    """Replace `obj`'s mesh with a voxel remesh carrying baked, smoothed vertex colour and skin weights.

    The surface is also relaxed `surface_smoothing` times and shaded smooth: voxel grain would
    otherwise make the toon light bands flicker as the model moves.
    """
    source = obj.data
    source_positions = np.array([v.co for v in source.vertices])
    source_colours = _vertex_colours(source, linear_textures)
    source_weights = _vertex_weights(obj, len(source.vertices))

    deforming = [m for m in obj.modifiers if m.show_viewport]
    for modifier in deforming:
        modifier.show_viewport = False
    voxel = obj.modifiers.new("pixelcraft_remesh", "REMESH")
    voxel.mode, voxel.voxel_size = "VOXEL", voxel_size
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    obj.modifiers.remove(voxel)
    for modifier in deforming:
        modifier.show_viewport = True

    positions = np.array([v.co for v in mesh.vertices])
    tree = KDTree(len(source_positions))
    for index, position in enumerate(source_positions):
        tree.insert(position, index)
    tree.balance()
    nearest = np.array([[i for _, i, _ in tree.find_n(p, 4)] for p in positions])

    colours = _smooth(mesh, source_colours[nearest].mean(1), smooth_iterations)
    relaxed = _smooth(mesh, positions, surface_smoothing)
    mesh.vertices.foreach_set("co", relaxed.ravel())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), dtype=bool))
    mesh.update()
    attribute = mesh.color_attributes.new(COLOUR, "FLOAT_COLOR", "POINT")
    attribute.data.foreach_set("color", np.hstack([colours, np.ones((len(colours), 1))]).ravel())
    mesh.materials.clear()
    mesh.materials.append(_colour_material())
    obj.data = mesh

    weights = source_weights[nearest].mean(1)
    for group in obj.vertex_groups:
        for index in np.nonzero(weights[:, group.index] > 0.01)[0]:
            group.add([int(index)], float(weights[index, group.index]), "REPLACE")
    return len(mesh.vertices)


def _vertex_colours(mesh, linear_textures):
    """Linear RGB per vertex: the base colour texture sampled at each of its UV corners, averaged."""
    image = next((n.image for m in mesh.materials if m and m.use_nodes for n in m.node_tree.nodes
                  if n.type == "TEX_IMAGE" and n.image is not None), None)
    if image is None or not mesh.uv_layers:
        return np.full((len(mesh.vertices), 3), 0.5)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(height, width, 4)[..., :3]
    if not linear_textures and image.colorspace_settings.name == "sRGB":
        pixels = np.where(pixels <= 0.04045, pixels / 12.92, ((pixels + 0.055) / 1.055) ** 2.4)
    uvs = np.zeros(len(mesh.loops) * 2)
    mesh.uv_layers.active.data.foreach_get("uv", uvs)
    uvs = uvs.reshape(-1, 2) % 1.0
    corner_colours = pixels[(uvs[:, 1] * (height - 1)).round().astype(int), (uvs[:, 0] * (width - 1)).round().astype(int)]
    corner_vertices = np.zeros(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", corner_vertices)
    totals = np.zeros((len(mesh.vertices), 3))
    np.add.at(totals, corner_vertices, corner_colours)
    counts = np.bincount(corner_vertices, minlength=len(mesh.vertices))[:, None]
    return totals / np.maximum(counts, 1)


def _vertex_weights(obj, count):
    weights = np.zeros((count, max(len(obj.vertex_groups), 1)))
    for vertex in obj.data.vertices:
        for membership in vertex.groups:
            weights[vertex.index, membership.group] = membership.weight
    return weights


def _smooth(mesh, colours, iterations):
    """Average each vertex value (colour, position) with its edge neighbours, `iterations` times."""
    edges = np.zeros(len(mesh.edges) * 2, dtype=np.int64)
    mesh.edges.foreach_get("vertices", edges)
    a, b = edges[0::2], edges[1::2]
    for _ in range(iterations):
        totals, counts = colours.copy(), np.ones(len(colours))
        np.add.at(totals, a, colours[b])
        np.add.at(totals, b, colours[a])
        np.add.at(counts, a, 1)
        np.add.at(counts, b, 1)
        colours = totals / counts[:, None]
    return colours


def _colour_material():
    material = bpy.data.materials.get("pixelcraft_vertex_colour")
    if material is not None:
        return material
    material = bpy.data.materials.new("pixelcraft_vertex_colour")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    attribute = tree.nodes.new("ShaderNodeAttribute")
    attribute.attribute_type, attribute.attribute_name = "GEOMETRY", COLOUR
    emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(attribute.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material
