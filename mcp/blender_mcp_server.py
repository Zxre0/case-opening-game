"""Headless Blender MCP server. Runs bpy in-process and exposes tools over stdio."""
import os, sys, io, contextlib, traceback, time

# Blender writes to fd 1 from C code; keep the real stdout for JSON-RPC only.
_rpc_fd = os.dup(1)
os.dup2(2, 1)
sys.stdout = os.fdopen(_rpc_fd, "w", buffering=1)

import bpy
from mcp.server.fastmcp import FastMCP, Image

OUT_DIR = os.environ.get("BLENDER_MCP_OUT", "/tmp/blender-mcp")
os.makedirs(OUT_DIR, exist_ok=True)
mcp = FastMCP("blender")
_ns = {"bpy": bpy}


@mcp.tool()
def scene_info() -> str:
    """List objects in the current scene with type, location and materials, plus render settings."""
    sc = bpy.context.scene
    lines = [f"Blender {bpy.app.version_string} | scene '{sc.name}' | engine {sc.render.engine} | "
             f"{sc.render.resolution_x}x{sc.render.resolution_y} | camera {sc.camera.name if sc.camera else None}"]
    for o in sc.objects:
        mats = [s.material.name for s in getattr(o, "material_slots", []) if s.material]
        lines.append(f"- {o.name} ({o.type}) loc={tuple(round(v, 3) for v in o.location)} mats={mats}")
    return "\n".join(lines)


@mcp.tool()
def run_python(code: str) -> str:
    """Execute Python code inside Blender (bpy is imported; state persists between calls).
    Set a variable named `result` to return a value. Printed output is returned too."""
    buf = io.StringIO()
    _ns.pop("result", None)
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, _ns)
    except Exception:
        return buf.getvalue() + "\nERROR:\n" + traceback.format_exc()
    out = buf.getvalue()
    if "result" in _ns:
        out += f"\nresult = {_ns['result']!r}"
    return out or "OK"


@mcp.tool()
def render(filename: str = "render.png", samples: int = 64, width: int = 0, height: int = 0,
           engine: str = "CYCLES") -> list:
    """Render the scene's active camera to OUT_DIR/filename and return the image.
    engine: CYCLES (CPU) or BLENDER_EEVEE_NEXT. width/height 0 keeps the scene setting."""
    sc = bpy.context.scene
    if not sc.camera:
        return ["No active camera. Add one with run_python first."]
    sc.render.engine = engine
    if engine == "CYCLES":
        sc.cycles.device = "CPU"
        sc.cycles.samples = samples
    if width: sc.render.resolution_x = width
    if height: sc.render.resolution_y = height
    path = os.path.join(OUT_DIR, os.path.basename(filename))
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return [f"Saved {path} in {time.time() - t:.1f}s", Image(path=path)]


@mcp.tool()
def reset_scene() -> str:
    """Clear everything and start from an empty scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return "Empty scene ready."


@mcp.tool()
def save_blend(filename: str = "scene.blend") -> str:
    """Save the current scene as a .blend file in OUT_DIR."""
    path = os.path.join(OUT_DIR, os.path.basename(filename))
    bpy.ops.wm.save_as_mainfile(filepath=path)
    return f"Saved {path}"


@mcp.tool()
def open_blend(path: str) -> str:
    """Open an existing .blend file."""
    bpy.ops.wm.open_mainfile(filepath=path)
    return scene_info()


@mcp.tool()
def import_model(path: str) -> str:
    """Import a model file (.glb/.gltf, .fbx, .obj, .stl, .ply) into the scene."""
    ext = os.path.splitext(path)[1].lower()
    ops = {".glb": bpy.ops.import_scene.gltf, ".gltf": bpy.ops.import_scene.gltf, ".fbx": bpy.ops.import_scene.fbx,
           ".obj": bpy.ops.wm.obj_import, ".stl": bpy.ops.wm.stl_import, ".ply": bpy.ops.wm.ply_import}
    if ext not in ops:
        return f"Unsupported format {ext}"
    ops[ext](filepath=path)
    return scene_info()


if __name__ == "__main__":
    mcp.run()
