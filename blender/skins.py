"""Renders every knife skin in the game (Rare Special items) for the website.

Reads the gold items from index.html, builds the matching knife from knives.py, applies a
procedural finish to the blade steel, renders on a transparent background at the 5:2 aspect
the game's item cards use, and writes:
  renders/skins/<skin id>.webp     one image per skin
  renders/skins/manifest.js        the list of rendered skin ids, loaded by index.html

Usage:
  /opt/blender-env/bin/python blender/skins.py [--samples 32] [--width 750] [skin ids...]
The finishes are stylized procedural stand-ins named after the game's finishes.
"""
import bpy, json, math, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knives as K

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "renders", "skins")

WEAPON_KEY = {
    "Karambit": "karambit", "M9 Bayonet": "m9_bayonet", "Bayonet": "bayonet", "Flip Knife": "flip",
    "Gut Knife": "gut", "Butterfly Knife": "butterfly", "Talon Knife": "talon", "Ursus Knife": "ursus",
    "Stiletto Knife": "stiletto", "Navaja Knife": "navaja", "Skeleton Knife": "skeleton", "Nomad Knife": "nomad",
    "Survival Knife": "survival", "Paracord Knife": "paracord", "Falchion Knife": "falchion", "Bowie Knife": "bowie",
    "Huntsman Knife": "huntsman", "Shadow Daggers": "shadow_daggers", "Kukri Knife": "kukri",
}
# card framing: near-horizontal, tip to the right
CELL_ROT = {"karambit": -6, "talon": -4, "kukri": 8, "falchion": -8}


def game_skins():
    html = open(os.path.join(ROOT, "index.html"), encoding="utf8").read()
    out = []
    for m in re.finditer(r"\{id:'(\w+)'.*?gold:(\[\[.*?\]\])\}\}", html, re.S):
        case_id, gold = m.group(1), json.loads(m.group(2))
        for i, row in enumerate(gold):
            weapon = row[0].replace("★", "").strip()
            if weapon in WEAPON_KEY:
                out.append(dict(id="%s-gold%d" % (case_id, i), knife=WEAPON_KEY[weapon], finish=row[1]))
    return out


# ---------------------------------------------------------------- finishes
def _tex(nt, spec, coord):
    N, L = nt.nodes, nt.links
    kind = spec[0]
    tc = N.new("ShaderNodeTexCoord")
    if kind == "gradient":
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0]); return sep.outputs["X"]
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = coord
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    if kind == "noise":
        t = N.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = spec[1]
        t.inputs["Distortion"].default_value = spec[2]; t.inputs["Detail"].default_value = spec[3]; out = t.outputs["Fac"]
    elif kind == "wave":
        t = N.new("ShaderNodeTexWave"); t.wave_type = spec[1]
        if spec[1] == "BANDS": t.bands_direction = spec[2]
        else: t.rings_direction = spec[2]
        t.inputs["Scale"].default_value = spec[3]; t.inputs["Distortion"].default_value = spec[4]
        t.inputs["Detail"].default_value = spec[5]; out = t.outputs["Fac"]
    elif kind == "edges":
        t = N.new("ShaderNodeTexVoronoi"); t.feature = 'DISTANCE_TO_EDGE'; t.inputs["Scale"].default_value = spec[1]
        out = t.outputs["Distance"]
    elif kind == "cells":
        t = N.new("ShaderNodeTexVoronoi"); t.inputs["Scale"].default_value = spec[1]; out = t.outputs["Distance"]
    L.new(mp.outputs["Vector"], t.inputs["Vector"])
    return out


def _ramp(nt, fac, stops, constant=False):
    r = nt.nodes.new("ShaderNodeValToRGB"); el = r.color_ramp.elements
    if constant: r.color_ramp.interpolation = 'CONSTANT'
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
    el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, col in stops[1:-1]: el.new(pos).color = (*col, 1)
    nt.links.new(fac, r.inputs["Fac"]); return r.outputs["Color"]


def finish_material(name, tex, stops, metal=0.9, rough=0.22, coat=0.4, coord=(0.3, 0.3, 0.3), over=None, constant=False):
    m = bpy.data.materials.new("Finish_" + name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    col = _ramp(nt, _tex(nt, tex, coord), stops, constant)
    if over:  # (tex, stops, coord) multiplied on top, for lines and webs
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        nt.links.new(col, mix.inputs[6]); nt.links.new(_ramp(nt, _tex(nt, over[0], over[2]), over[1]), mix.inputs[7])
        col = mix.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.08
    return m


W = (1, 1, 1)
FINISHES = {
    "fade": lambda: finish_material("fade", ("gradient",), [(0.0, (1.0, 0.78, 0.12)), (0.45, (1.0, 0.25, 0.5)), (1.0, (0.4, 0.12, 0.85))], 0.6, 0.18, 0.7),
    "doppler": lambda: finish_material("doppler", ("noise", 2.5, 3.0, 8), [(0.3, (0.03, 0.0, 0.06)), (0.45, (0.6, 0.05, 0.5)), (0.58, (0.15, 0.12, 0.85)), (0.72, (0.95, 0.45, 0.9))], 0.7, 0.16, 0.7),
    "gamma_doppler": lambda: finish_material("gamma", ("noise", 1.6, 1.4, 9), [(0.3, (0.004, 0.08, 0.03)), (0.42, (0.02, 0.55, 0.1)), (0.52, (0.03, 0.75, 0.65)), (0.62, (0.06, 0.4, 1.0)), (0.74, (0.55, 1.0, 0.95))], 0.8, 0.18, 0.7, (0.14, 0.14, 0.14)),
    "marble_fade": lambda: finish_material("marble", ("noise", 1.4, 5.0, 6), [(0.3, (0.9, 0.05, 0.03)), (0.45, (1.0, 0.75, 0.1)), (0.6, (0.1, 0.3, 0.95)), (0.75, (0.9, 0.05, 0.03))], 0.7, 0.16, 0.7),
    "tiger_tooth": lambda: finish_material("tiger", ("wave", "BANDS", "X", 3.5, 9, 3), [(0.25, (1.0, 0.62, 0.1)), (0.5, (0.85, 0.28, 0.02)), (0.75, (1.0, 0.7, 0.15))], 1, 0.18, 0.5),
    "damascus_steel": lambda: finish_material("damascus", ("wave", "BANDS", "Y", 6, 14, 5), [(0.2, (0.22, 0.23, 0.25)), (0.5, (0.6, 0.62, 0.65)), (0.8, (0.3, 0.31, 0.33))], 1, 0.3, 0.2),
    "rust_coat": lambda: finish_material("rust", ("noise", 6, 1, 10), [(0.35, (0.12, 0.05, 0.02)), (0.5, (0.45, 0.17, 0.05)), (0.65, (0.25, 0.1, 0.04))], 0.3, 0.8, 0),
    "ultraviolet": lambda: finish_material("uv", ("noise", 3, 1, 6), [(0.35, (0.05, 0.025, 0.1)), (0.65, (0.2, 0.09, 0.32))], 0.5, 0.5, 0.1),
    "crimson_web": lambda: finish_material("web", ("noise", 3, 0, 2), [(0.0, (0.5, 0.0, 0.01)), (1.0, (0.62, 0.02, 0.03))], 0.3, 0.4, 0.3,
                                           over=(("edges", 1.1), [(0.0, (0.02, 0.0, 0.0)), (0.018, (0.02, 0.0, 0.0)), (0.035, W)], (0.35, 0.35, 0.35))),
    "case_hardened": lambda: finish_material("ch", ("noise", 2, 2, 6), [(0.3, (0.06, 0.18, 0.55)), (0.5, (0.55, 0.45, 0.25)), (0.7, (0.85, 0.65, 0.25))], 1, 0.25, 0.2),
    "slaughter": lambda: finish_material("slaughter", ("noise", 2, 1.5, 6), [(0.35, (0.6, 0.02, 0.02)), (0.5, (0.9, 0.25, 0.25)), (0.65, (0.95, 0.75, 0.75))], 0.8, 0.2, 0.5, (0.1, 0.8, 0.3)),
    "night": lambda: finish_material("night", ("noise", 4, 0, 4), [(0.3, (0.04, 0.045, 0.06)), (0.7, (0.09, 0.1, 0.12))], 0.7, 0.45, 0.1),
    "blue_steel": lambda: finish_material("blue", ("noise", 2.5, 1.5, 6), [(0.35, (0.08, 0.15, 0.38)), (0.65, (0.42, 0.47, 0.57))], 1, 0.25, 0.2),
    "stained": lambda: finish_material("stained", ("noise", 1.5, 2, 6), [(0.3, (0.3, 0.12, 0.25)), (0.5, (0.35, 0.25, 0.12)), (0.7, (0.15, 0.25, 0.42))], 1, 0.3, 0.2),
    "safari_mesh": lambda: finish_material("safari", ("noise", 3, 0.5, 4), [(0.3, (0.38, 0.32, 0.2)), (0.7, (0.52, 0.45, 0.3))], 0.2, 0.7, 0,
                                           over=(("wave", "BANDS", "DIAGONAL", 9, 0, 0), [(0.0, (0.1, 0.09, 0.06)), (0.12, W)], (1, 1, 1))),
    "night_stripe": lambda: finish_material("nstripe", ("wave", "BANDS", "DIAGONAL", 4, 0, 0), [(0.0, (0.03, 0.03, 0.035)), (0.5, (0.03, 0.03, 0.035)), (0.55, (0.25, 0.26, 0.28)), (1.0, (0.25, 0.26, 0.28))], 0.6, 0.4, 0.2, constant=True),
    "lore": lambda: finish_material("lore", ("noise", 3, 1, 5), [(0.35, (0.75, 0.52, 0.18)), (0.65, (0.95, 0.72, 0.3))], 1, 0.22, 0.3,
                                    over=(("edges", 2.5), [(0.0, (0.15, 0.1, 0.04)), (0.03, (0.15, 0.1, 0.04)), (0.05, W)], (0.3, 0.3, 0.3))),
    "autotronic": lambda: finish_material("auto", ("cells", 1.6), [(0.0, (0.6, 0.02, 0.02)), (0.45, (0.6, 0.02, 0.02)), (0.5, (0.04, 0.04, 0.05)), (0.75, (0.04, 0.04, 0.05)), (0.8, (0.5, 0.5, 0.52))], 0.7, 0.3, 0.3, constant=True),
    "black_laminate": lambda: finish_material("lam", ("wave", "BANDS", "Y", 3, 6, 3), [(0.3, (0.015, 0.015, 0.018)), (0.7, (0.13, 0.13, 0.14))], 0.4, 0.3, 0.5),
    "bright_water": lambda: finish_material("water", ("wave", "RINGS", "SPHERICAL", 2, 4, 4), [(0.3, (0.02, 0.25, 0.6)), (0.7, (0.25, 0.65, 0.95))], 0.8, 0.2, 0.5),
    "freehand": lambda: finish_material("freehand", ("wave", "BANDS", "DIAGONAL", 2, 10, 2), [(0.0, (0.85, 0.85, 0.82)), (0.45, (0.85, 0.85, 0.82)), (0.5, (0.1, 0.3, 0.9)), (0.55, (0.85, 0.85, 0.82)), (0.82, (0.85, 0.85, 0.82)), (0.86, (0.95, 0.35, 0.65)), (0.9, (0.85, 0.85, 0.82))], 0.2, 0.35, 0.3),
}


def finish_key(name): return name.lower().replace(" ", "_").replace("-", "_")


def apply_finish(root, mat):
    for ob in root.children:
        if ob.type != 'MESH' or ob.hide_render or not ob.data.materials: continue
        so = ob.modifiers.get("Solid")
        if ob.data.materials[0].name.startswith("Steel") and so and so.thickness <= 0.34:
            ob.data.materials[0] = mat


def frame_wide(cam, root, aspect):
    import mathutils
    dg = bpy.context.evaluated_depsgraph_get(); xs, ys = [], []
    for ob in root.children:
        if ob.hide_render: continue
        ev = ob.evaluated_get(dg)
        for c in ev.bound_box:
            v = ev.matrix_world @ mathutils.Vector(c); xs.append(v.x); ys.append(v.y)
    cam.location = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 60)
    cam.data.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * aspect) * 1.05


def main():
    from PIL import Image
    args = sys.argv[1:]
    def opt(n, d):
        if n in args:
            i = args.index(n); v = args[i + 1]; del args[i:i + 2]; return v
        return d
    samples = int(opt("--samples", 32)); width = int(opt("--width", 750)); aspect = 2.5
    os.makedirs(OUT, exist_ok=True)
    skins = game_skins()
    todo = [s for s in skins if not args or s["id"] in args]
    for s in todo:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
        sc.render.resolution_x = width; sc.render.resolution_y = int(width / aspect)
        sc.render.film_transparent = True; sc.render.image_settings.color_mode = 'RGBA'
        sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
        M = K.make_materials(); cam = K.setup_scene()
        bpy.data.objects.remove(bpy.data.objects["Backdrop"])
        spec = dict(K.KNIVES[s["knife"]]); spec["mirror"] = False; spec["rot"] = CELL_ROT.get(s["knife"], 2)
        if s["knife"] == "shadow_daggers": spec["parts"] = K._dagger(0, 0, 0)
        saved = K.KNIVES[s["knife"]]; K.KNIVES[s["knife"]] = spec
        root = K.build_knife(s["knife"], M); K.KNIVES[s["knife"]] = saved
        fk = finish_key(s["finish"])
        if fk in FINISHES: apply_finish(root, FINISHES[fk]())
        frame_wide(cam, root, aspect)
        png = os.path.join(OUT, s["id"] + ".png"); sc.render.filepath = png
        t = time.time(); bpy.ops.render.render(write_still=True)
        Image.open(png).save(os.path.join(OUT, s["id"] + ".webp"), "WEBP", quality=82, method=6); os.remove(png)
        print("SKIN %-18s %-16s %-16s %.1fs" % (s["id"], s["knife"], s["finish"], time.time() - t), flush=True)
    done = sorted(f[:-5] for f in os.listdir(OUT) if f.endswith(".webp"))
    with open(os.path.join(OUT, "manifest.js"), "w") as f:
        f.write("window.SKIN_RENDERS = %s;\n" % json.dumps(done))
    print("manifest:", len(done), "renders")


if __name__ == "__main__":
    main()
