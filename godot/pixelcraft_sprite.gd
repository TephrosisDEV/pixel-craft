@tool
class_name PixelcraftSprite
extends AnimatedSprite2D
## Plays a pixel-craft sprite sheet. Set `sheet_json` to an exported `sheet.json`; `sheet.png`
## and `normal.png` next to it are loaded automatically. The normal map lets Godot's 2D lights
## (PointLight2D, DirectionalLight2D) light the sprite, Dead Cells style.
##
## The node's origin is the character's feet (the sheet's pivot), so place it on the ground.
## Animations are named `<action>_<direction>`, e.g. `walk_e`; flip_h gives the other side.

## The sheet.json written by `pixelcraft process`.
@export_file("*.json") var sheet_json: String:
	set(value):
		sheet_json = value
		if is_node_ready():
			build()

## Animations that play once instead of looping (matched on the action part of the name).
@export var play_once: PackedStringArray = ["attack", "death", "hurt"]


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	build()


## Rebuilds sprite_frames from the sheet. Called automatically when sheet_json changes.
func build() -> void:
	if sheet_json.is_empty():
		return
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(sheet_json))
	var folder := sheet_json.get_base_dir()
	var sheet := CanvasTexture.new()
	sheet.diffuse_texture = load(folder.path_join(data.meta.image))
	if ResourceLoader.exists(folder.path_join("normal.png")):
		sheet.normal_texture = load(folder.path_join("normal.png"))

	var frames := SpriteFrames.new()
	frames.remove_animation(&"default")
	for tag in data.meta.frameTags:
		var name: StringName = tag.name
		frames.add_animation(name)
		frames.set_animation_loop(name, not play_once.has(String(name).get_slice("_", 0)))
		frames.set_animation_speed(name, 1000.0 / data.frames[tag.from].duration)
		for index in range(tag.from, tag.to + 1):
			var rect: Dictionary = data.frames[index].frame
			var region := AtlasTexture.new()
			region.atlas = sheet
			region.region = Rect2(rect.x, rect.y, rect.w, rect.h)
			frames.add_frame(name, region)
	sprite_frames = frames
	centered = false
	offset = -Vector2(data.meta.pivot.x, data.meta.pivot.y)
	if frames.get_animation_names().size() > 0:
		animation = frames.get_animation_names()[0]
