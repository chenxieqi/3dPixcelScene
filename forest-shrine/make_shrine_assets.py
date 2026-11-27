"""Procedural low-poly assets for the forest shrine diorama -> torii.glb, fern.glb (+ preview.html).

numpy only. Run:  python make_shrine_assets.py
Y-up, meters, origin at the base. Flat shaded, named materials (the scene keys off the names):
  torii: wood (weathered vermilion), cap (dark kasagi top), base (black pillar feet), moss
  fern:  frond, frond_lit (lighter tips)
"""
import base64, json, math, struct, sys
from pathlib import Path
import numpy as np

rng = np.random.default_rng(11)
UP = np.array([0.0, 1.0, 0.0])
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
TEMPLATE = Path.home() / ".claude/skills/pixel-diorama/assets/model-preview-template.html"


def norm(v):
    return v / np.linalg.norm(v)


class Mesh:
    def __init__(self, names):
        self.tris = {k: [] for k in names}

    def tri(self, b, a, c, d):
        self.tris[b].append((np.array(a, float), np.array(c, float), np.array(d, float)))

    def quad(self, b, a, c, d, e):
        self.tri(b, a, c, d); self.tri(b, a, d, e)

    def box(self, b, c, size, yaw=0.0, tilt=0.0):
        """oriented box: center c, size (sx, sy, sz); tilt = rotation about z (pillar lean)."""
        sx, sy, sz = (s / 2 for s in size)
        cy, sy_ = math.cos(yaw), math.sin(yaw)
        ct, st = math.cos(tilt), math.sin(tilt)
        def P(x, y, z):
            x, y = x * ct - y * st, x * st + y * ct
            x, z = x * cy + z * sy_, -x * sy_ + z * cy
            return np.array(c) + [x, y, z]
        v = [P(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            self.quad(b, *[v[i] for i in f])

    def cyl(self, b, p0, p1, r0, r1, sides=8, cap=True):
        a = norm(np.array(p1, float) - p0)
        h = UP if abs(a @ UP) < 0.9 else np.array([1.0, 0, 0])
        u = norm(np.cross(a, h)); w = np.cross(a, u)
        ring = lambda p, r: [np.array(p) + r * (math.cos(2 * math.pi * s / sides) * u + math.sin(2 * math.pi * s / sides) * w) for s in range(sides)]
        A, B = ring(p0, r0), ring(p1, r1)
        for s in range(sides):
            n = (s + 1) % sides
            self.quad(b, A[s], A[n], B[n], B[s])
        if cap:
            for s in range(sides):
                self.tri(b, B[s], B[(s + 1) % sides], p1)


# ================= torii =================
torii = Mesh(["wood", "cap", "base", "moss"])
W = 0.36           # half distance between pillars at the ground
H = 0.74           # pillar height (to under the shimaki)
LEAN = math.radians(3.0)
for sgn in (-1, 1):
    x0 = sgn * W
    top = np.array([x0 - sgn * H * math.tan(LEAN), H, 0])
    torii.cyl("wood", np.array([x0, 0.06, 0]), top, 0.034, 0.03, 8)
    torii.cyl("base", np.array([x0, -0.02, 0]), np.array([x0, 0.065, 0]), 0.042, 0.04, 8)  # kamaki
# nuki (lower tie beam) passes through the pillars and sticks out a little
torii.box("wood", (0, 0.57, 0), (2 * W + 0.16, 0.045, 0.035))
# gakuzuka (center strut)
torii.box("wood", (0, 0.64, 0), (0.05, 0.1, 0.03))
# shimaki (upper beam, red) + kasagi (top beam, dark) with upturned ends
def curved_beam(mesh, mat, y, half, thick, depth, lift, seg=8):
    pts = []
    for i in range(seg + 1):
        t = -1 + 2 * i / seg
        pts.append((t * half, y + lift * t ** 4))
    for i in range(seg):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        za, zb = depth / 2, -depth / 2
        a0, a1 = [xa, ya, za], [xa, ya + thick, za]
        b0, b1 = [xb, yb, za], [xb, yb + thick, za]
        c0, c1 = [xa, ya, zb], [xa, ya + thick, zb]
        d0, d1 = [xb, yb, zb], [xb, yb + thick, zb]
        mesh.quad(mat, a0, b0, b1, a1)        # front
        mesh.quad(mat, d0, c0, c1, d1)        # back
        mesh.quad(mat, a1, b1, d1, c1)        # top
        mesh.quad(mat, c0, d0, b0, a0)        # bottom
    for (x, yy), s in ((pts[0], -1), (pts[-1], 1)):
        e = [[x, yy, depth / 2], [x, yy + thick, depth / 2], [x, yy + thick, -depth / 2], [x, yy, -depth / 2]]
        mesh.quad(mat, *(e if s > 0 else e[::-1]))
    return pts

curved_beam(torii, "wood", H, W + 0.13, 0.04, 0.05, 0.0)
kas = curved_beam(torii, "cap", H + 0.04, W + 0.21, 0.045, 0.07, 0.035)
# moss: lumpy tufts on top of the kasagi (as in the reference, it's been there a while)
for i in range(30):
    t = rng.uniform(-0.92, 0.92)
    x = t * (W + 0.21)
    y = H + 0.04 + 0.045 + 0.035 * t ** 4
    r = rng.uniform(0.018, 0.034)
    c = np.array([x, y + r * 0.2, rng.uniform(-0.03, 0.03)])
    # flattened octahedron tuft
    v = [c + [r, 0, 0], c + [0, 0, r * 0.9], c + [-r, 0, 0], c + [0, 0, -r * 0.9]]
    top = c + [0, r * 0.8, 0]; bot = c - [0, r * 0.25, 0]
    for k in range(4):
        torii.tri("moss", v[k], v[(k + 1) % 4], top)
        torii.tri("moss", v[(k + 1) % 4], v[k], bot)
# moss creeping on the pillar feet
for sgn in (-1, 1):
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        c = np.array([sgn * W + 0.04 * math.cos(a), 0.03 + 0.03 * k, 0.04 * math.sin(a)])
        r = 0.018
        v = [c + [r, 0, 0], c + [0, 0, r], c + [-r, 0, 0], c + [0, 0, -r]]
        tp = c + [0, r, 0]
        for j in range(4):
            torii.tri("moss", v[j], v[(j + 1) % 4], tp)

# ================= fern =================
fern = Mesh(["frond", "frond_lit"])
N_FROND = 9
for f in range(N_FROND):
    psi = 2 * math.pi * f / N_FROND + rng.uniform(-0.2, 0.2)
    out = np.array([math.cos(psi), 0, math.sin(psi)])
    side = np.array([-out[2], 0, out[0]])
    L = rng.uniform(0.26, 0.36)
    rise = rng.uniform(0.55, 0.8)                        # how upright it starts
    SEG = 7
    pts = []
    for s in range(SEG + 1):
        t = s / SEG
        # arching: up first, then out and drooping
        p = out * (L * t) + UP * (L * rise * math.sin(math.pi * t * 0.75) - L * 0.25 * t * t)
        pts.append(p)
    for s in range(SEG):
        t = (s + 0.5) / SEG
        mat = "frond_lit" if t > 0.55 else "frond"
        a, b = pts[s], pts[s + 1]
        w = 0.055 * math.sin(math.pi * (0.15 + 0.8 * t)) + 0.006   # leaflet length
        tang = norm(b - a)
        nrm = norm(np.cross(tang, side))
        for sg in (-1, 1):
            tip = (a + b) / 2 + side * sg * w + nrm * w * 0.25 - UP * w * 0.25
            fern.tri(mat, a, b, tip) if sg > 0 else fern.tri(mat, b, a, tip)
        # midrib sliver so the frond reads at low res
        fern.tri("frond", a + side * 0.004, b + side * 0.003, b - side * 0.003)
        fern.tri("frond", a + side * 0.004, b - side * 0.003, a - side * 0.004)


# ================= GLB writer =================
def srgb2lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def write_glb(mesh, mats, name, path):
    bin_data = bytearray()
    bvs, accs, prims, materials = [], [], [], []
    total = 0
    for mi, (mname, (hexc, ds)) in enumerate(mats.items()):
        materials.append({"name": mname, "doubleSided": ds,
                          "pbrMetallicRoughness": {"baseColorFactor": srgb2lin(hexc),
                                                   "metallicFactor": 0.0, "roughnessFactor": 0.9}})
        T = np.array(mesh.tris[mname], dtype=np.float32)
        total += len(T)
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        pos = T.reshape(-1, 3)
        nor = np.repeat(n, 3, axis=0).astype(np.float32)
        attrs = {}
        for key, arr in (("POSITION", pos), ("NORMAL", nor)):
            raw = arr.astype(np.float32).tobytes()
            bvs.append({"buffer": 0, "byteOffset": len(bin_data), "byteLength": len(raw), "target": 34962})
            bin_data += raw
            acc = {"bufferView": len(bvs) - 1, "componentType": 5126, "count": len(arr), "type": "VEC3"}
            if key == "POSITION":
                acc["min"] = arr.min(axis=0).tolist(); acc["max"] = arr.max(axis=0).tolist()
            accs.append(acc); attrs[key] = len(accs) - 1
        prims.append({"attributes": attrs, "material": mi, "mode": 4})
    gltf = {"asset": {"version": "2.0", "generator": "make_shrine_assets.py"},
            "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"name": name, "mesh": 0}],
            "meshes": [{"name": name, "primitives": prims}], "materials": materials,
            "accessors": accs, "bufferViews": bvs, "buffers": [{"byteLength": len(bin_data)}]}
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    bin_data += b"\0" * ((4 - len(bin_data) % 4) % 4)
    glb = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_data))
           + struct.pack("<II", len(js), 0x4E4F534A) + js
           + struct.pack("<II", len(bin_data), 0x004E4942) + bytes(bin_data))
    path.write_bytes(glb)
    print(f"{path.name}: {total} tris, {len(glb)} bytes")
    return glb


glb = write_glb(torii, {"wood": ("#B23A22", True), "cap": ("#3A2621", True),
                        "base": ("#1E1B1A", True), "moss": ("#6F8F36", True)}, "Torii", OUT / "torii.glb")
write_glb(fern, {"frond": ("#3F6A2C", True), "frond_lit": ("#6E8F3A", True)}, "Fern", OUT / "fern.glb")
if TEMPLATE.exists():
    (OUT / "preview.html").write_text(TEMPLATE.read_text(encoding="utf-8")
                                      .replace("__GLB_BASE64__", base64.b64encode(glb).decode()), encoding="utf-8")
