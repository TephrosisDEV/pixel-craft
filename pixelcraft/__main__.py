"""pixelcraft render|process|run|glb CONFIG

render   run Blender on the config (PIXELCRAFT_BLENDER: Blender binary, or a python with the bpy module)
process  shade, palette, outline and pack an existing render
run      both
glb      export the prepared, animated model as <output>/<name>.glb (for GodotPixelRenderer or Godot)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .process import process


def render(config: Path, *extra: str) -> None:
    script = Path(__file__).with_name("render_blender.py")
    executable = os.environ.get("PIXELCRAFT_BLENDER", "blender")
    command = (
        [executable, str(script), str(config), *extra] if Path(executable).name.startswith("python")
        else [executable, "-b", "--factory-startup", "-P", str(script), "--", str(config), *extra]
    )
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="pixelcraft", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["render", "process", "run", "glb"])
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = args.config.resolve()
    if args.command == "glb":
        render(config, "--glb-only")
    if args.command in ("render", "run"):
        render(config)
    if args.command in ("process", "run"):
        print(process(config))


if __name__ == "__main__":
    sys.exit(main())
