"""Original knife models based on real-world knife types, built and rendered with headless Blender.

Usage:
  /opt/blender-env/bin/python blender/knives.py                 # all knives
  /opt/blender-env/bin/python blender/knives.py karambit bowie  # some knives
Options: --samples N (default 48), --size PX (default 900), --out DIR (default renders/knives)

Each knife is a side profile (x toward the tip, y toward the spine, units ~cm) made of parts:
  part:  outline points, z offset, half-thickness, bevel, material, optional holes
  edge:  a polyline along the cutting edge; a lighter ground-edge strip is built from it
  screw: (x, y, radius)
In an outline, a point wrapped with C() is a sharp corner; the rest are smoothed.
"""
import bpy, bmesh, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- geometry helpers
def C(p): return [p, p]

def flat(pts):
    out = []
    for p in pts:
        if isinstance(p, list): out.extend(p)
        else: out.append(p)
    return out

def _cr_seg(p0, p1, p2, p3, n):
    pts = []
    for k in range(n):
        t = k / n; t2 = t * t; t3 = t2 * t
        pts.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    return pts

def dedupe(pts, closed=True):
    out = [pts[0]]
    for q in pts[1:]:
        if abs(q[0] - out[-1][0]) + abs(q[1] - out[-1][1]) > 1e-4: out.append(q)
    if closed and len(out) > 2 and abs(out[0][0] - out[-1][0]) + abs(out[0][1] - out[-1][1]) < 1e-4: out.pop()
    return out

def cr_closed(pts, n=10):
    pts = flat(pts); N = len(pts); out = []
    for i in range(N):
        out += _cr_seg(pts[i - 1], pts[i], pts[(i + 1) % N], pts[(i + 2) % N], n)
    return dedupe(out)

def cr_open(pts, n=10):
    pts = flat(pts); P = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        out += _cr_seg(P[i - 1], P[i], P[i + 1], P[i + 2], n)
    out.append(pts[-1])
    return dedupe(out, closed=False)

def circle(cx, cy, r, ry=None, n=40):
    ry = r if ry is None else ry
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]

def rrect(cx, cy, w, h, r, n=8):
    pts = []
    for (qx, qy, a0) in [(cx + w / 2 - r, cy + h / 2 - r, 0), (cx - w / 2 + r, cy + h / 2 - r, 90),
                         (cx - w / 2 + r, cy - h / 2 + r, 180), (cx + w / 2 - r, cy - h / 2 + r, 270)]:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((qx + r * math.cos(a), qy + r * math.sin(a)))
    return pts

def teeth(x0, x1, n, ylo, yhi):
    step = (x1 - x0) / n; pts = []
    for i in range(n):
        x = x0 + step * i
        pts += [C((x, ylo)), C((x + step * 0.65, yhi))]
    return pts

def xform(pts, dx=0, dy=0, rot=0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    def f(p): return (p[0] * c - p[1] * s + dx, p[0] * s + p[1] * c + dy)
    return [[f(q) for q in p] if isinstance(p, list) else f(p) for p in pts]

def shift(pts, dx): return xform(pts, dx=dx)

# ---------------------------------------------------------------- knife definitions
def P(pts, z=0.0, t=0.12, bev=0.04, mat="steel", holes=(), smooth=True):
    return {"pts": pts, "z": z, "t": t, "bev": bev, "mat": mat, "holes": list(holes), "smooth": smooth}
def E(pts, w=0.3, side=1, z=0.12): return {"edge": pts, "w": w, "side": side, "z": z}
def S(x, y, r=0.2, mat="dark"): return {"screw": (x, y, r), "mat": mat}

KNIVES = {}

KNIVES["karambit"] = dict(name="Karambit", rot=-8, parts=[
    P([(9.4, 1.9), (11.5, 2.1), (13.6, 1.7), (15.4, 0.6), (16.6, -1.0), C((17.3, -2.9)),
       (16.2, -1.5), (14.9, -0.4), (13.2, 0.4), (11.4, 0.6), (10.0, 0.4), (9.4, 0.3)]),
    E([(10.0, 0.45), (11.4, 0.62), (13.2, 0.42), (14.9, -0.38), (16.2, -1.45), (17.25, -2.85)], w=0.32),
    P([(1.2, 1.35), (3, 1.3), (5.5, 1.4), (8, 1.65), (10.2, 1.95), (10.6, 0.6), (10.2, -0.9), (8.4, -0.9), (7.3, -1.35),
       (6.2, -0.95), (5, -1.35), (3.9, -0.95), (2.6, -1.15), (1.3, -1.25)], t=0.36, bev=0.08, mat="g10"),
    P(circle(0.1, 0.05, 1.8), t=0.3, bev=0.08, holes=[circle(0.1, 0.05, 1.12)]),
    S(9.6, 0.6, 0.3), S(3.4, 0.15), S(7.2, 0.3),
])

KNIVES["m9_bayonet"] = dict(name="M9 Bayonet", rot=22, parts=[
    P([(0, 0.95), C((3, 1.0))] + teeth(3, 10.5, 12, 1.0, 1.28) +
      [C((10.8, 1.0)), (13.5, 0.88), (16, 0.52), C((18.2, 0.0)), (16.8, -0.75), (14.5, -1.2), (11, -1.35), (6, -1.32),
       (1.6, -1.27), C((0, -1.2))], t=0.14, holes=[circle(3.3, 0.0, 0.95, 0.38)]),
    E([(1.2, -1.26), (6, -1.3), (11, -1.33), (14.5, -1.18), (16.8, -0.72), (18.1, -0.02)], w=0.38, z=0.14),
    P([C((-0.75, 2.3)), C((0.15, 2.3)), C((0.15, -2.3)), C((-0.75, -2.3))], t=0.42, bev=0.12, smooth=False),
    P(circle(-0.3, 2.95, 0.95), t=0.36, bev=0.1, holes=[circle(-0.3, 2.95, 0.6)]),
    P([(-0.75, 1.25), (-2.5, 1.1), (-4, 1.32), (-5.5, 1.1), (-7, 1.32), (-8.5, 1.1), (-10, 1.32), (-11.2, 1.25),
       (-11.2, -1.3), (-10, -1.42), (-8.5, -1.15), (-7, -1.42), (-5.5, -1.15), (-4, -1.42), (-2.5, -1.15), (-0.75, -1.25)],
      t=0.55, bev=0.15, mat="rubber"),
    P([(-11.1, 1.3), (-12.4, 1.2), (-13.0, 0.4), (-13.0, -0.6), (-12.4, -1.3), (-11.1, -1.38)], t=0.5, bev=0.12,
      holes=[circle(-12.2, -0.15, 0.32)]),
    S(-11.8, 0.85, 0.22),
])

KNIVES["bayonet"] = dict(name="Bayonet", rot=22, parts=[
    P([(0, 0.85), (10, 0.85), (13, 0.74), (15.5, 0.4), C((17.6, 0.0)), (15.5, -0.55), (12, -0.9), (6, -0.95), (1, -0.95),
       C((0, -0.9))], t=0.13),
    P([C((1.5, 0.3)), C((10.4, 0.3)), (10.8, 0.12), C((10.4, -0.06)), C((1.5, -0.06))], z=0.06, t=0.08, bev=0.03, mat="fuller"),
    E([(1, -0.94), (6, -0.95), (12, -0.88), (15.5, -0.53), (17.5, -0.02)], w=0.32, z=0.13),
    P([C((-0.6, 1.75)), C((0.1, 1.75)), C((0.1, -1.6)), C((-0.6, -1.6))], t=0.4, bev=0.12, smooth=False),
    P(circle(-0.25, 2.3, 0.78), t=0.34, bev=0.09, holes=[circle(-0.25, 2.3, 0.46)]),
    P([(-0.6, 1.1), (-3, 1.2), (-6, 1.22), (-9, 1.2), (-10.6, 1.12), (-10.6, -1.15), (-9, -1.25), (-6, -1.28), (-3, -1.25),
       (-0.6, -1.12)], t=0.5, bev=0.14, mat="g10"),
    P([(-10.5, 1.2), (-11.7, 1.1), (-12.1, 0.0), (-11.7, -1.12), (-10.5, -1.22)], t=0.46, bev=0.12),
    S(-3, 0, 0.2), S(-8, 0, 0.2),
])

KNIVES["flip"] = dict(name="Flip Knife", rot=24, parts=[
    P([(0, 0.9), (3, 1.15), (6, 1.25), (8.5, 1.0), C((10.6, 0.15)), (9.2, -0.55), (6.5, -0.9), (3, -0.95), (0.9, -0.9),
       (0.4, -0.6), (0.1, -0.75), C((-0.3, -0.8))], t=0.12),
    E([(0.9, -0.9), (3, -0.94), (6.5, -0.88), (9.2, -0.52), (10.5, 0.12)], w=0.3),
    P([(-0.7, -0.5), (0.3, -0.6), (0.15, -1.55), (-0.35, -1.8), (-0.9, -1.0)], t=0.12, bev=0.05),
    P([(0.75, 1.08), (-3, 1.02), (-7, 0.97), (-10.5, 0.92), (-11.25, 0.3), (-11.25, -0.62), (-10.5, -1.12), (-7, -1.12),
       (-4, -1.02), (-2, -1.27), (0.75, -0.97)], t=0.3, bev=0.06),
    P([(0.45, 0.92), (-3, 0.88), (-7, 0.83), (-10.4, 0.78), (-11.0, 0.25), (-11.0, -0.5), (-10.4, -0.98), (-7, -0.98),
       (-4, -0.88), (-2, -1.12), (0.45, -0.83)], z=0.04, t=0.34, bev=0.08, mat="g10"),
    S(0, 0.08, 0.34), S(-10.2, -0.1), S(-5, -0.05),
])

KNIVES["gut"] = dict(name="Gut Knife", rot=20, parts=[
    P([(0, 0.95), (2.5, 1.1), (4.4, 1.28), (4.85, 1.05), (5.35, 0.82), (5.85, 0.95), (6.05, 1.2), C((5.5, 1.48)),
       (6.4, 1.62), (7.6, 1.42), (9.6, 0.9), C((11.0, 0.1)), (9.8, -0.7), (7, -1.05), (3.5, -1.1), (0.8, -1.0),
       C((0, -0.95))], t=0.13),
    E([(0.8, -1.0), (3.5, -1.08), (7, -1.03), (9.8, -0.68), (10.9, 0.08)], w=0.3, z=0.13),
    P([(0.3, 1.12), (-1.5, 1.06), (-5, 1.12), (-9, 1.16), (-10.3, 0.9), (-10.55, -0.3), (-10.2, -1.2), (-9, -1.42),
       (-5, -1.22), (-2, -1.3), (-0.7, -1.62), (-0.15, -2.05), (0.35, -1.6), (0.35, -1.0)], t=0.48, bev=0.14,
      mat="rubber", holes=[circle(-9.6, -0.3, 0.28)]),
    P([C((0.4, 1.18)), C((-0.7, 1.18)), C((-0.7, -1.3)), C((0.4, -1.3))], z=0.06, t=0.5, bev=0.1, smooth=False),
])

KNIVES["butterfly"] = dict(name="Butterfly Knife", rot=24, parts=[
    P([(0, 0.72), (7.5, 0.76), (9.3, 0.55), C((11.2, -0.1)), (9.8, -0.65), (6, -0.8), (1.2, -0.8), (0.6, -0.55),
       (0.3, -0.8), C((0, -0.75))], t=0.11),
    E([(1.2, -0.8), (6, -0.79), (9.8, -0.62), (11.1, -0.08)], w=0.26, z=0.11),
    P([C((-0.2, 0.95)), C((-11.5, 0.95)), C((-11.8, 0.62)), C((-11.8, -0.62)), C((-11.5, -0.95)), C((-0.2, -0.95)),
       C((0.15, -0.6)), C((0.15, 0.6))], t=0.42, bev=0.12, smooth=False,
      holes=[rrect(x, 0, 1.6, 0.9, 0.42) for x in (-2.1, -4.2, -6.3, -8.4)] + [circle(-10.4, 0, 0.3)]),
    P([C((-11.6, 0.18)), (-12.6, 0.42), (-13.3, 0.32), (-13.4, 0.05), C((-11.6, -0.16))], z=0.3, t=0.1, bev=0.04, mat="dark"),
    S(-0.35, 0.52, 0.2, "steel"), S(-0.35, -0.52, 0.2, "steel"), S(-11.4, 0, 0.18, "steel"),
])

KNIVES["talon"] = dict(name="Talon Knife", rot=-4, parts=[
    P([(0, 1.2), (3, 1.62), (6, 1.62), (8.8, 0.92), (10.8, -0.5), C((12.2, -2.4)), (10.6, -1.4), (8.4, -0.5),
       (5.8, -0.2), (3, -0.4), (1, -0.6), C((0, -0.7))], t=0.13),
    E([(1, -0.58), (3, -0.38), (5.8, -0.18), (8.4, -0.48), (10.6, -1.38), (12.1, -2.35)], w=0.34, z=0.13),
    P([(0.5, 1.28), (-3, 1.08), (-6, 0.78), (-8.6, 0.28), (-9.9, -0.5), (-9.7, -1.65), (-8.6, -1.98), (-7, -1.55),
       (-5, -1.75), (-3, -1.35), (-1, -1.3), (0.5, -0.85)], t=0.32, bev=0.06),
    P([(0.2, 1.12), (-3, 0.94), (-6, 0.64), (-8.5, 0.14), (-9.6, -0.5), (-9.45, -1.5), (-8.55, -1.78), (-7, -1.38),
       (-5, -1.58), (-3, -1.2), (-1, -1.15), (0.2, -0.72)], z=0.04, t=0.36, bev=0.08, mat="g10"),
    P(circle(-10.2, -1.05, 1.25), t=0.28, bev=0.08, holes=[circle(-10.2, -1.05, 0.78)]),
    S(0, 0.25, 0.36), S(-4, -0.3), S(-7.5, -0.6),
])

KNIVES["ursus"] = dict(name="Ursus Knife", rot=22, parts=[
    P([(0, 1.0), (3, 1.3), (6, 1.45), (8.6, 1.2), (10.6, 0.5), C((11.6, -0.1)), (10.2, -0.9), (7, -1.3), (3, -1.35),
       (1, -1.2), (0.5, -0.8), C((0.1, -1.0))], t=0.14),
    E([(1, -1.2), (3, -1.33), (7, -1.27), (10.2, -0.86), (11.5, -0.12)], w=0.36, z=0.14),
    P([(0.85, 1.32), (-3, 1.27), (-7, 1.22), (-10.1, 1.12), (-11.0, 0.42), (-11.0, -0.75), (-10.1, -1.42), (-7, -1.42),
       (-4, -1.32), (-2.2, -1.62), (-1, -2.02), (0.85, -1.5)], t=0.3, bev=0.06),
    P([(0.6, 1.2), (-3, 1.15), (-7, 1.1), (-10, 1.0), (-10.8, 0.4), (-10.8, -0.7), (-10, -1.3), (-7, -1.3), (-4, -1.2),
       (-2.2, -1.5), (-1, -1.9), (0.6, -1.4)], z=0.04, t=0.36, bev=0.08, mat="g10"),
    S(0, 0.1, 0.38), S(-10, 0.0, 0.22), S(-5, -0.1, 0.2), S(1.4, 0.75, 0.2, "steel"),
])

KNIVES["stiletto"] = dict(name="Stiletto Knife", rot=26, parts=[
    P([(0, 0.55), (7, 0.55), (9.5, 0.45), C((12.5, 0.0)), (9.5, -0.45), (7, -0.55), C((0, -0.55))], t=0.11),
    E([(0.5, -0.55), (7, -0.55), (9.5, -0.44), (12.4, -0.01)], w=0.2, z=0.11),
    E([(7, 0.55), (9.5, 0.44), (12.4, 0.01)], w=0.18, side=-1, z=0.11),
    P([C((0.4, 0.75)), C((-1.6, 0.75)), C((-1.6, -0.75)), C((0.4, -0.75))], t=0.36, bev=0.1, smooth=False),
    P([C((-0.2, -0.7)), C((0.3, -0.7)), (0.18, -1.45), C((-0.06, -1.5))], t=0.12, bev=0.05),
    P([C((-1.6, 0.68)), (-6, 0.72), C((-10, 0.66)), C((-10, -0.66)), (-6, -0.72), C((-1.6, -0.68))], t=0.34, bev=0.1, mat="horn"),
    P([C((-10, 0.75)), (-11.4, 0.75), (-11.85, 0.3), (-11.85, -0.3), (-11.4, -0.75), C((-10, -0.75))], t=0.36, bev=0.1),
    S(-0.6, 0.2, 0.22, "steel"), S(-11.0, 0.0, 0.16, "steel"),
])

KNIVES["navaja"] = dict(name="Navaja Knife", rot=18, parts=[
    P([(0, 0.65), (4, 0.75), (5.6, 0.6), C((7.4, 0.0)), (6.0, -0.6), (3, -0.75), (0.5, -0.7), C((0, -0.65))], t=0.1),
    E([(0.5, -0.7), (3, -0.74), (6, -0.58), (7.3, -0.02)], w=0.22, z=0.1),
    P([(0.3, 0.8), (-3, 0.75), (-6, 0.55), (-8, 0.1), (-8.8, -0.5), (-8.6, -1.0), (-7.8, -0.9), (-5.8, -0.6), (-3, -0.75),
       (0.3, -0.8)], t=0.32, bev=0.09, mat="wood"),
    P([C((0.3, 0.85)), C((-0.9, 0.85)), C((-0.9, -0.85)), C((0.3, -0.85))], t=0.34, bev=0.08, smooth=False),
    P([C((-7.4, 0.32)), (-8.85, -0.5), (-8.65, -1.05), (-7.8, -0.95), C((-7.0, -0.55))], t=0.34, bev=0.08),
    S(-0.3, 0.0, 0.2, "steel"),
])

KNIVES["skeleton"] = dict(name="Skeleton Knife", rot=22, parts=[
    P([(0, 0.8), (3, 1.0), (6, 1.05), (8.4, 0.75), C((10.2, 0.0)), (8.6, -0.65), (5.5, -0.95), (2, -0.95), (0.5, -0.85),
       C((0, -0.8))], t=0.13),
    E([(0.5, -0.85), (2, -0.94), (5.5, -0.93), (8.6, -0.62), (10.1, -0.02)], w=0.3, z=0.13),
    P([(0.2, 0.95), (-3, 0.95), (-6, 0.9), (-9, 0.85), (-10.4, 0.4), (-10.6, -0.5), (-10, -1.0), (-7.5, -1.0), (-5, -1.1),
       (-2.5, -1.0), (-1.0, -1.3), (0.2, -1.0)], t=0.2, bev=0.07,
      holes=[rrect(-2.4, -0.05, 1.5, 0.95, 0.42), rrect(-4.9, -0.05, 2.0, 1.05, 0.45), rrect(-7.5, -0.05, 2.0, 0.95, 0.42),
             circle(-9.7, -0.1, 0.3)]),
    P([C((0.4, 1.0)), C((-0.6, 1.0)), C((-0.6, -1.15)), C((0.4, -1.15))], z=0.05, t=0.24, bev=0.08, smooth=False, mat="dark"),
])

KNIVES["nomad"] = dict(name="Nomad Knife", rot=22, parts=[
    P([(0, 1.0), (2, 1.25), (5.5, 1.4), (8.5, 1.1), (10.8, 0.25), C((11.4, -0.15)), (9.5, -0.9), (6, -1.25), (2.5, -1.2),
       (1.2, -1.0), (0.7, -1.3), (0.2, -1.3), C((0, -1.0))], t=0.13),
    E([(1.2, -1.0), (2.5, -1.18), (6, -1.23), (9.5, -0.87), (11.3, -0.13)], w=0.34, z=0.13),
    P([(0.65, 1.28), (-4, 1.23), (-8, 1.13), (-10.35, 0.8), (-10.85, 0.0), (-10.35, -0.92), (-8, -1.28), (-4, -1.23),
       (-1.5, -1.12), (0.65, -1.23)], t=0.3, bev=0.06),
    P([(0.4, 1.15), (-4, 1.1), (-8, 1.0), (-10.2, 0.7), (-10.6, 0.0), (-10.2, -0.8), (-8, -1.15), (-4, -1.1), (-1.5, -1.0),
       (0.4, -1.1)], z=0.04, t=0.36, bev=0.08, mat="g10"),
    S(0, 0.15, 0.36), S(-9.8, 0.0), S(-4.8, 0.0),
])

KNIVES["survival"] = dict(name="Survival Knife", rot=22, parts=[
    P([(0, 0.85), C((2, 0.9))] + teeth(2, 7, 8, 0.9, 1.15) +
      [C((7.4, 0.95)), (10, 0.85), (12.2, 0.4), C((13.6, -0.1)), (12, -0.8), (8, -1.1), (3, -1.1), (0.5, -1.05), C((0, -1.0))],
      t=0.14),
    E([(0.5, -1.05), (3, -1.09), (8, -1.08), (12, -0.78), (13.5, -0.12)], w=0.34, z=0.14),
    P([C((0.0, 1.6)), C((-0.6, 1.6)), C((-0.6, -1.9)), C((0.0, -1.9))], t=0.42, bev=0.12, smooth=False, mat="dark"),
    P([C((-0.6, 1.1)), (-6, 1.18), C((-11, 1.15)), C((-11, -1.2)), (-6, -1.24), C((-0.6, -1.15))], t=0.55, bev=0.16, mat="rubber"),
    P([(-11, 1.35), (-12.2, 1.3), (-12.45, 0), (-12.2, -1.35), (-11, -1.4)], t=0.56, bev=0.14, mat="dark",
      holes=[circle(-11.8, 0, 0.26)]),
])

KNIVES["paracord"] = dict(name="Paracord Knife", rot=22, parts=[
    P([(0, 0.75), (6, 0.8), (8.2, 0.7), (10, 0.3), C((11.2, -0.1)), (9.8, -0.75), (6, -0.95), (2, -0.95), (0.6, -0.9),
       C((0, -0.8))], t=0.13),
    E([(0.6, -0.9), (2, -0.94), (6, -0.93), (9.8, -0.72), (11.1, -0.12)], w=0.3, z=0.13),
    P([C((0.2, 0.78)), C((-9.5, 0.78)), C((-9.5, -0.86)), C((0.2, -0.86))], t=0.45, bev=0.18, smooth=False, mat="paracord"),
    P([C((-9.4, 0.6)), (-11.2, 0.55), (-11.65, 0), (-11.2, -0.65), C((-9.4, -0.7))], t=0.13, bev=0.04,
      holes=[circle(-10.6, -0.05, 0.33)]),
])

_FAL = 9.2
KNIVES["falchion"] = dict(name="Falchion Knife", rot=-28, mirror=True, parts=[
    P(shift([(8.6, 0.95), (11, 1.05), (13.5, 1.2), (15.8, 1.45), (17.6, 1.95), (19.1, 2.75), C((20.4, 3.7)), (19.6, 2.35),
             (18.3, 1.05), (16.4, 0.0), (14.0, -0.55), (11.5, -0.7), (10.0, -0.6), (9.6, -0.25), (9.2, -0.45),
             C((8.6, -0.5))], -_FAL), t=0.12),
    E(shift([(10.0, -0.6), (11.5, -0.68), (14.0, -0.53), (16.4, 0.02), (18.3, 1.07), (19.6, 2.37), (20.35, 3.65)], -_FAL),
      w=0.3),
    P(shift([(9.4, 1.0), (7.0, 0.95), (4.5, 0.75), (2.2, 0.35), (0.4, -0.25), (-0.5, -0.95), (-0.45, -1.65), (0.4, -1.95),
             (1.3, -1.6), (2.2, -1.25), (3.1, -1.7), (4.1, -1.45), (5.0, -1.85), (6.0, -1.55), (7.2, -1.2), (8.4, -1.0),
             (9.4, -0.75)], -_FAL), t=0.34, bev=0.08, mat="g10"),
    P(shift([(10.3, 1.08), (7.4, 1.05), (6.6, 0.6), (6.8, -0.6), (7.3, -1.25), (8.6, -1.05), (10.3, -0.7)], -_FAL),
      t=0.4, bev=0.06),
    P(shift([(1.0, -0.05), (0.4, -0.25), (-0.5, -0.95), (-0.45, -1.65), (0.4, -1.95), (0.9, -1.75), (0.2, -1.3)], -_FAL),
      t=0.4, bev=0.05),
    S(0, 0.15, 0.3), S(7.6 - _FAL, 0.55, 0.13), S(7.9 - _FAL, -0.75, 0.13), S(3.6 - _FAL, 0.15, 0.13),
])

KNIVES["bowie"] = dict(name="Bowie Knife", rot=22, parts=[
    P([(0, 1.1), (9, 1.2), (10.2, 1.18), (12.5, 0.9), (15, 0.3), C((17, -0.3)), (15.5, -1.1), (12, -1.6), (6, -1.7),
       (1, -1.65), C((0, -1.55))], t=0.15),
    E([(1, -1.65), (6, -1.69), (12, -1.58), (15.5, -1.07), (16.9, -0.32)], w=0.42, z=0.15),
    P([(10.2, 1.18), (12.5, 0.9), (15, 0.3), (16.6, -0.22), (15, 0.08), (12.5, 0.66), (10.2, 0.98)], z=0.12, t=0.03,
      bev=0.02, mat="edge"),
    P([C((0.0, 0.6)), (0.3, 1.8), (0.05, 2.45), (-0.6, 2.25), (-0.4, 1.45), C((-0.7, 0.95)), C((-0.7, -1.0)), (-0.4, -1.85),
       (-0.7, -2.65), (-0.1, -2.85), (0.3, -2.15), C((0.0, -1.0))], t=0.4, bev=0.12, mat="brass"),
    P([C((-0.7, 1.2)), (-5, 1.32), (-9, 1.25), C((-11, 1.35)), C((-11, -1.5)), (-9, -1.42), (-5, -1.52), C((-0.7, -1.4))],
      t=0.5, bev=0.16, mat="wood"),
    P([(-10.9, 1.45), (-12.2, 1.4), (-12.6, 0), (-12.2, -1.55), (-10.9, -1.6)], t=0.5, bev=0.14, mat="brass"),
    S(-3, 0, 0.2, "brass"), S(-8, 0, 0.2, "brass"),
])

KNIVES["huntsman"] = dict(name="Huntsman Knife", rot=22, parts=[
    P([(0, 1.0), C((1.5, 1.05))] + teeth(1.5, 7, 9, 1.05, 1.32) +
      [C((7.4, 1.1)), (10, 1.05), (12.5, 0.7), C((14.6, -0.1)), (13.2, -0.95), (10, -1.3), (5, -1.35), (1, -1.3), C((0, -1.2))],
      t=0.15),
    E([(1, -1.3), (5, -1.34), (10, -1.27), (13.2, -0.92), (14.5, -0.12)], w=0.38, z=0.15),
    P([C((0.15, 1.65)), C((-0.5, 1.65)), C((-0.5, -2.1)), (0.1, -2.45), C((0.4, -2.0))], t=0.42, bev=0.12, mat="dark"),
    P([C((-0.5, 1.15)), (-5, 1.22), C((-10, 1.25)), C((-10, -1.25)), (-8.5, -1.47), (-7.2, -1.1), (-5.8, -1.47),
       (-4.4, -1.1), (-3, -1.47), (-1.6, -1.15), C((-0.5, -1.3))], t=0.55, bev=0.16, mat="rubber"),
    P([(-9.9, 1.35), (-11.3, 1.2), (-11.55, 0), (-11.3, -1.3), (-9.9, -1.4)], t=0.52, bev=0.14,
      holes=[circle(-10.9, 0, 0.25)]),
])

def _dagger(dx, dy, rot):
    return [
        P(xform([C((0.1, 1.25)), (2, 1.18), (6, 0.8), C((9.2, 0)), (6, -0.8), (2, -1.18), C((0.1, -1.25))], dx, dy, rot), t=0.12),
        E(xform([(0.4, -1.22), (2, -1.16), (6, -0.78), (9.1, -0.01)], dx, dy, rot), w=0.28),
        E(xform([(0.4, 1.22), (2, 1.16), (6, 0.78), (9.1, 0.01)], dx, dy, rot), w=0.28, side=-1),
        P(xform([C((0.3, -3.3)), C((0.3, 3.3)), (-0.4, 3.7), (-1.3, 3.6), (-1.8, 2.7), (-1.5, 1.8), (-1.8, 0.9),
                 (-1.5, 0.0), (-1.8, -0.9), (-1.5, -1.8), (-1.8, -2.7), (-1.3, -3.6),
                 (-0.4, -3.7)], dx, dy, rot), t=0.5, bev=0.16, mat="rubber"),
    ]
KNIVES["shadow_daggers"] = dict(name="Shadow Daggers", rot=18, parts=_dagger(0, 5.2, 0) + _dagger(2.2, -5.2, 0))

KNIVES["kukri"] = dict(name="Kukri Knife", rot=12, parts=[
    P([(0, 0.9), (3, 1.1), (6, 0.8), (9, 0.0), (11.5, -1.0), (13.5, -2.2), C((15, -3.4)), (14.2, -3.9), (12.4, -3.9),
       (10.5, -3.3), (8.6, -2.6), (6.5, -2.1), (4.2, -1.8), (2.2, -1.3), C((1.2, -1.0)), (0.9, -0.72), C((0.6, -1.0)),
       C((0.3, -0.75)), C((0, -0.85))], t=0.16),
    E([(1.3, -1.02), (2.2, -1.28), (4.2, -1.78), (6.5, -2.08), (8.6, -2.58), (10.5, -3.28), (12.4, -3.88), (14.2, -3.88),
       (14.95, -3.42)], w=0.4, z=0.16),
    P([C((0.25, 1.15)), C((-1, 1.15)), C((-1, -1.25)), C((0.25, -1.25))], t=0.45, bev=0.12, smooth=False),
    P([(-1, 1.05), (-5, 0.98), (-8.5, 1.1), (-10.2, 1.62), (-10.85, 1.3), (-10.85, -1.42), (-10.2, -1.82), (-8.5, -1.2),
       (-5, -1.08), (-1, -1.18)], t=0.52, bev=0.16, mat="rubber"),
    P([C((-3.0, 1.1)), C((-3.5, 1.1)), C((-3.5, -1.2)), C((-3.0, -1.2))], z=0.05, t=0.53, bev=0.06, smooth=False),
    P([C((-6.5, 1.1)), C((-7.0, 1.1)), C((-7.0, -1.2)), C((-6.5, -1.2))], z=0.05, t=0.53, bev=0.06, smooth=False),
    P([(-10.3, 1.7), (-11.2, 1.4), (-11.2, -1.5), (-10.3, -1.9)], z=0.0, t=0.5, bev=0.12),
])

# ---------------------------------------------------------------- materials
def _principled(name, color, metallic=0.0, rough=0.5, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough; b.inputs["Coat Weight"].default_value = coat
    return m, b

def _bump(m, b, scale, strength, kind="noise"):
    nt = m.node_tree; N = nt.nodes
    if kind == "noise":
        tx = N.new("ShaderNodeTexNoise"); tx.inputs["Scale"].default_value = scale; tx.inputs["Detail"].default_value = 6
    else:
        tx = N.new("ShaderNodeTexWave"); tx.inputs["Scale"].default_value = scale
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength
    nt.links.new(tx.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return tx

def _ramp_color(m, b, tex_out, stops):
    nt = m.node_tree; r = nt.nodes.new("ShaderNodeValToRGB"); el = r.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
    el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, col in stops[1:-1]: el.new(pos).color = (*col, 1)
    nt.links.new(tex_out, r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])

def make_materials():
    M = {}
    M["steel"], b = _principled("Steel", (0.62, 0.63, 0.65), 1, 0.22); _bump(M["steel"], b, 400, 0.02)
    M["edge"], _ = _principled("Edge", (0.85, 0.86, 0.88), 1, 0.1)
    M["fuller"], _ = _principled("Fuller", (0.42, 0.43, 0.45), 1, 0.3)
    M["dark"], _ = _principled("BlackOxide", (0.07, 0.07, 0.075), 1, 0.38)
    M["brass"], _ = _principled("Brass", (0.85, 0.6, 0.25), 1, 0.25)
    M["g10"], b = _principled("G10", (0.025, 0.027, 0.03), 0, 0.55); _bump(M["g10"], b, 90, 0.25)
    M["rubber"], b = _principled("Rubber", (0.018, 0.018, 0.02), 0, 0.82); _bump(M["rubber"], b, 160, 0.3)
    m, b = _principled("Wood", (0.3, 0.13, 0.05), 0, 0.42, 0.35); M["wood"] = m
    tc = m.node_tree.nodes.new("ShaderNodeTexCoord"); w = m.node_tree.nodes.new("ShaderNodeTexWave")
    w.bands_direction = 'Y'; w.inputs["Scale"].default_value = 1.6; w.inputs["Distortion"].default_value = 9; w.inputs["Detail"].default_value = 6; w.inputs["Detail Scale"].default_value = 2
    m.node_tree.links.new(tc.outputs["Object"], w.inputs["Vector"])
    _ramp_color(m, b, w.outputs["Fac"], [(0.1, (0.05, 0.018, 0.006)), (0.5, (0.16, 0.06, 0.02)), (0.95, (0.3, 0.13, 0.05))])
    m, b = _principled("Horn", (0.05, 0.03, 0.02), 0, 0.22, 0.6); M["horn"] = m
    n = m.node_tree.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 1.5; n.inputs["Distortion"].default_value = 3
    _ramp_color(m, b, n.outputs["Fac"], [(0.35, (0.015, 0.01, 0.008)), (0.7, (0.16, 0.08, 0.03))])
    m, b = _principled("Paracord", (0.1, 0.12, 0.06), 0, 0.85); M["paracord"] = m
    tc = m.node_tree.nodes.new("ShaderNodeTexCoord"); mp = m.node_tree.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(35))
    w = m.node_tree.nodes.new("ShaderNodeTexWave"); w.inputs["Scale"].default_value = 3.2; w.wave_profile = 'SIN'
    m.node_tree.links.new(tc.outputs["Object"], mp.inputs["Vector"]); m.node_tree.links.new(mp.outputs["Vector"], w.inputs["Vector"])
    _ramp_color(m, b, w.outputs["Fac"], [(0.15, (0.02, 0.022, 0.015)), (0.6, (0.12, 0.14, 0.07)), (0.95, (0.2, 0.22, 0.12))])
    bp = m.node_tree.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
    m.node_tree.links.new(w.outputs["Fac"], bp.inputs["Height"]); m.node_tree.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return M

# ---------------------------------------------------------------- builders
def _mesh_obj(name, pts, z, t, bev, mat, parent, holes, mirror):
    sx = -1 if mirror else 1
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((sx * x, y, 0)) for x, y in pts]
    f = bm.faces.new(vs); bm.normal_update()
    if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location.z = z; ob.parent = parent
    bpy.context.scene.collection.objects.link(ob); me.materials.append(mat)
    so = ob.modifiers.new("Solid", 'SOLIDIFY'); so.thickness = t * 2; so.offset = 0
    for i, h in enumerate(holes):
        cut = _mesh_obj(name + "_cut%d" % i, h, z, t + 1.0, 0, mat, parent, [], mirror)
        cut.hide_render = True; cut.display_type = 'WIRE'
        bo = ob.modifiers.new("Hole%d" % i, 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'; bo.object = cut
    if bev > 0:
        bv = ob.modifiers.new("Bevel", 'BEVEL'); bv.width = bev; bv.segments = 4; bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(40)
    ob.modifiers.new("Tri", 'TRIANGULATE')
    return ob

def _edge_strip(pts, w, side):
    line = cr_open(pts, 8); n = len(line); inner = []
    for i, (x, y) in enumerate(line):
        a = line[max(i - 1, 0)]; b = line[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L * side, tx / L * side
        frac = i / (n - 1); taper = min(1.0, (1 - frac) / 0.12, frac / 0.04 + 0.3)
        inner.append((x + nx * w * taper, y + ny * w * taper))
    return dedupe(line + inner[::-1])

def build_knife(key, M):
    spec = KNIVES[key]; mirror = spec.get("mirror", False)
    root = bpy.data.objects.new(spec["name"], None); bpy.context.scene.collection.objects.link(root)
    for i, part in enumerate(spec["parts"]):
        nm = "%s_%02d" % (key, i)
        if "edge" in part:
            _mesh_obj(nm + "_edge", _edge_strip(part["edge"], part["w"], part["side"]), part["z"] + 0.005, 0.008, 0.006,
                      M["edge"], root, [], mirror)
        elif "screw" in part:
            x, y, r = part["screw"]
            bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=r, depth=0.14, location=((-x if mirror else x), y, 0.62))
            ob = bpy.context.object; ob.name = nm + "_screw"; ob.parent = root; ob.data.materials.append(M[part["mat"]])
            bv = ob.modifiers.new("Bevel", 'BEVEL'); bv.width = r * 0.3; bv.segments = 4
            bpy.ops.object.shade_smooth()
        else:
            pts = cr_closed(part["pts"]) if part["smooth"] else dedupe(flat(part["pts"]))
            holes = [dedupe(h) for h in part["holes"]]
            _mesh_obj(nm, pts, part["z"], part["t"], part["bev"], M[part["mat"]], root, holes, mirror)
    root.rotation_euler = (math.radians(12), math.radians(-6), math.radians(spec["rot"]))
    return root

def setup_scene():
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -8)); bd = bpy.context.object
    bm = bpy.data.materials.new("Backdrop"); bm.use_nodes = True; nt = bm.node_tree; nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 16, 1 / 16, 1)
    gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (0.006, 0.008, 0.011, 1); rp.color_ramp.elements[1].color = (0.03, 0.04, 0.05, 1)
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], gr.inputs["Vector"])
    nt.links.new(gr.outputs["Fac"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    bd.data.materials.append(bm); bd.visible_glossy = False; bd.visible_diffuse = False; bd.name = "Backdrop"

    def area(loc, rot, size, energy):
        bpy.ops.object.light_add(type='AREA', location=loc, rotation=rot); l = bpy.context.object
        l.data.size = size; l.data.energy = energy; l.visible_camera = False
    area((4, 6, 24), (math.radians(-10), math.radians(8), 0), 30, 1100)
    area((-12, 12, 12), (math.radians(-40), math.radians(-40), 0), 10, 2600)
    area((14, -10, 7), (math.radians(55), math.radians(40), 0), 6, 1300)
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.035, 0.04, 1)
    bpy.ops.object.camera_add(location=(0, 0, 60)); cam = bpy.context.object; cam.data.type = 'ORTHO'; sc.camera = cam
    return cam

def frame(cam, root):
    import mathutils
    dg = bpy.context.evaluated_depsgraph_get(); xs, ys = [], []
    for ob in root.children:
        if ob.hide_render: continue
        ev = ob.evaluated_get(dg)
        for c in ev.bound_box:
            v = ev.matrix_world @ mathutils.Vector(c); xs.append(v.x); ys.append(v.y)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    cam.location = (cx, cy, 60); cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.14

def main():
    args = sys.argv[1:]
    def opt(name, default):
        if name in args:
            i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
        return default
    samples = int(opt("--samples", 48)); size = int(opt("--size", 900))
    out = os.path.abspath(opt("--out", os.path.join(HERE, "..", "renders", "knives")))
    keys = args or list(KNIVES)
    os.makedirs(out, exist_ok=True)
    for key in keys:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
        sc.render.resolution_x = sc.render.resolution_y = size
        sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
        M = make_materials(); cam = setup_scene(); root = build_knife(key, M); frame(cam, root)
        sc.render.filepath = os.path.join(out, key + ".png")
        t = time.time(); bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, key + ".blend"))
        print("KNIFE %-16s %.1fs" % (key, time.time() - t), flush=True)

if __name__ == "__main__":
    main()
