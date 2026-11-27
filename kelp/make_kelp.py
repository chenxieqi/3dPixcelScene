"""Procedural low-poly giant kelp frond (巨藻 / 褐藻, Macrocystis) -> kelp.glb (+ preview.html).

numpy only. Run:  python make_kelp.py [out_dir] [seed]
A 4.4 m stipe rising from a root-like holdfast, carrying ~40 long golden-brown blades, each on a
small gas bladder. Blades have ruffled wavy edges and a slight twist (see the reference photo of
kelp blades), stream upward and bend out to one side. Y-up, meters, origin at the holdfast.
Named materials: stipe, holdfast, bladder, blade, blade_tip
"""
import base64, json, math, struct, sys
from pathlib import Path
import numpy as np

SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 7
rng = np.random.default_rng(SEED)
UP = np.array([0.0, 1.0, 0.0])
XA = np.array([1.0, 0.0, 0.0])
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
TEMPLATE = Path.home() / ".claude/skills/pixel-diorama/assets/model-preview-template.html"
GOLDEN = math.radians(137.5)


def norm(v):
    return v / np.linalg.norm(v)


def frame(a):
    """two unit vectors perpendicular to a"""
    h = UP if abs(a @ UP) < 0.9 else XA
    u = norm(np.cross(a, h))
    return u, np.cross(a, u)


class Mesh:
    def __init__(self, names):
        self.tris = {k: [] for k in names}

    def tri(self, m, a, b, c):
        self.tris[m].append((np.array(a, float), np.array(b, float), np.array(c, float)))

    def quad(self, m, a, b, c, d):
        self.tri(m, a, b, c); self.tri(m, a, c, d)

    def tube(self, m, pts, radii, sides=5):
        """tapered tube along a polyline"""
        rings = []
        for i, p in enumerate(pts):
            t = norm(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
            u, w = frame(t)
            rings.append([p + radii[i] * (math.cos(2 * math.pi * s / sides) * u + math.sin(2 * math.pi * s / sides) * w)
                          for s in range(sides)])
        for A, B in zip(rings, rings[1:]):
            for s in range(sides):
                n = (s + 1) % sides
                self.quad(m, A[s], A[n], B[n], B[s])

    def lathe(self, m, p0, axis, prof, sides=6, spin=0.0):
        """solid of revolution; prof = [(t along axis, radius)], radius 0 = a pole"""
        a = norm(axis); u, w = frame(a)
        rings = []
        for t, r in prof:
            c = p0 + a * t
            rings.append(c if r == 0 else
                         [c + r * (math.cos(2 * math.pi * s / sides + spin) * u + math.sin(2 * math.pi * s / sides + spin) * w)
                          for s in range(sides)])
        for A, B in zip(rings, rings[1:]):
            for s in range(sides):
                n = (s + 1) % sides
                if isinstance(A, np.ndarray):
                    self.tri(m, A, B[n], B[s])
                elif isinstance(B, np.ndarray):
                    self.tri(m, A[s], A[n], B)
                else:
                    self.quad(m, A[s], A[n], B[n], B[s])


M = Mesh(["stipe", "holdfast", "bladder", "blade", "blade_tip"])


# ---------------- organs ----------------
def blade(base, out, L, W, ph):
    """long lance blade with ruffled (wavy) edges and a slight twist, streaming up and out.
    Three lines along its length: left edge, midrib, right edge; the edges ripple up and down."""
    d0 = norm(out * 0.5 + UP * 0.87)
    side0 = norm(np.cross(UP, out))
    SEG = 14
    rows = []
    for i in range(SEG + 1):
        t = i / SEG
        p = (base + d0 * L * t + out * L * 0.32 * t * t          # bends outward as it grows
             + side0 * L * 0.09 * math.sin(math.pi * 1.4 * t + ph * 0.3) * t)   # soft S-curve: streaming in the current
        tw = 0.7 * math.sin(math.pi * t * 1.2 + ph) * t           # slow ribbon twist
        tang = norm(d0 + out * 0.64 * t)
        sd = norm(side0 * math.cos(tw) + np.cross(tang, side0) * math.sin(tw))
        nrm = norm(np.cross(tang, sd))
        hw = W * (0.3 + 0.7 * math.sin(math.pi * min(1.0, 0.12 + 0.95 * t) ** 0.8)) * (1.0 - 0.75 * max(0.0, t - 0.75) / 0.25) if t < 0.99 else W * 0.06
        ruf = W * 0.3 * math.sin(t * 7.0 * math.pi + ph) * (0.3 + 0.7 * t)        # ruffled edge
        ruf2 = W * 0.3 * math.sin(t * 7.0 * math.pi + ph + 1.9) * (0.3 + 0.7 * t)
        rows.append((p + sd * hw + nrm * ruf, p, p - sd * hw + nrm * ruf2))
    for i in range(SEG):
        mat = "blade_tip" if i >= SEG * 0.6 else "blade"
        (l0, m0, r0), (l1, m1, r1) = rows[i], rows[i + 1]
        M.quad(mat, l0, m0, m1, l1)
        M.quad(mat, m0, r0, r1, m1)


def bladder(c, axis, r):
    M.lathe("bladder", c - axis * r, axis, [(0, 0), (r * 0.8, r * 0.9), (r * 1.6, r * 0.75), (r * 2.2, 0)], sides=4,
            spin=rng.uniform(0, 6))


# ---------------- assemble: one giant kelp frond, holdfast to well above the frame ----------------
H = 4.4
N = 34
stem = []
for i in range(N + 1):
    y = H * i / N
    stem.append(np.array([0.07 * math.sin(y * 0.7 + 0.4) + 0.03 * math.sin(y * 2.1),
                          y, 0.05 * math.sin(y * 0.5 + 1.3)]))
M.tube("stipe", stem, list(np.linspace(0.013, 0.008, len(stem))), sides=4)
# holdfast: a knot of root-like lumps
for k in range(6):
    a = k * 1.05 + rng.uniform(-0.2, 0.2)
    o = np.array([math.cos(a), 0.0, math.sin(a)])
    M.tube("holdfast", [np.array([0, 0.05, 0]), o * 0.05 + UP * 0.02, o * 0.09 - UP * 0.01], [0.012, 0.009, 0.006], sides=3)

# blades every ~11 cm, mostly streaming to one side (current) with some spread
y = 0.28
k = 0
while y < H - 0.1:
    i = min(int(y / H * N), N - 1)
    p = stem[i] + (stem[i + 1] - stem[i]) * ((y / H * N) - i)
    a = 0.6 + (1 if k % 2 else -1) * rng.uniform(0.6, 1.4) + rng.uniform(-0.3, 0.3)
    out = np.array([math.cos(a), 0.0, math.sin(a)])
    bc = p + out * 0.022 + UP * 0.01
    bladder(bc, norm(out + UP * 0.8), 0.011)
    L = rng.uniform(0.68, 1.0) * (0.75 + 0.25 * min(1.0, y / 1.0))
    blade(bc + norm(out + UP * 0.8) * 0.02, out, L, rng.uniform(0.1, 0.13), rng.uniform(0, 6))
    y += rng.uniform(0.15, 0.21)        # longer blades -> spaced further apart
    k += 1


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
                                                   "metallicFactor": 0.0, "roughnessFactor": 0.85}})
        T = np.array(mesh.tris[mname], dtype=np.float32)
        if len(T) == 0:          # unused material: keep it, emit no primitive
            continue
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
    gltf = {"asset": {"version": "2.0", "generator": "make_kelp.py"},
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


OUT.mkdir(parents=True, exist_ok=True)
glb = write_glb(M, {"stipe": ("#5E4A1E", True), "holdfast": ("#4A3A1C", True), "bladder": ("#9A7628", True),
                    "blade": ("#8E6A24", True), "blade_tip": ("#B08A34", True)},
                "Kelp", OUT / "kelp.glb")
if TEMPLATE.exists():
    html = (TEMPLATE.read_text(encoding="utf-8").replace("__GLB_BASE64__", base64.b64encode(glb).decode())
            .replace("cam.position.set(0.5, 0.45, 0.7);", "cam.position.set(2.2, 1.6, 3.2);")
            .replace("ctl.target.set(0, 0.3, 0);", "ctl.target.set(0, 1.6, 0);")
            .replace("Spider Lily Preview", "Kelp Preview"))
    (OUT / "preview.html").write_text(html, encoding="utf-8")
