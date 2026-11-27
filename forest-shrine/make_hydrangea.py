"""Procedural low-poly hydrangea (绣球花, Hydrangea macrophylla) -> hydrangea.glb (+ preview.html).

numpy only. Run:  python make_hydrangea.py [out_dir] [seed]
A small shrub: 5 stems with opposite broad ovate leaves, each topped by a mophead ball of 4-sepal
florets in mixed blue and violet. Y-up, meters, origin at the base, flat shaded. Named materials:
  stem, leaf, core (dark green ball under the florets), petal (blue), petal_tip (violet)
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


M = Mesh(["stem", "leaf", "core", "petal", "petal_tip"])


def bezier(p0, p1, p2, n):
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in np.linspace(0, 1, n)]


# ---------------- organs ----------------
def floret(c, face, r, spin, mat):
    """one 4-sepal floret: four rounded diamonds, slightly cupped outward"""
    u, w = frame(face)
    for k in range(4):
        a = spin + k * math.pi / 2
        d = math.cos(a) * u + math.sin(a) * w
        s = -math.sin(a) * u + math.cos(a) * w
        tip = c + d * r + face * r * 0.18
        m1 = c + d * r * 0.55 + s * r * 0.42 + face * r * 0.08
        m2 = c + d * r * 0.55 - s * r * 0.42 + face * r * 0.08
        M.tri(mat, c, m2, tip)
        M.tri(mat, c, tip, m1)


def mophead(c, R, purple):
    """a ball of florets on a dark-green core; colors mix blue and violet (purple = share of violet)"""
    M.lathe("core", c - UP * R * 0.75, UP, [(0, 0), (R * 0.45, R * 0.8), (R * 1.15, R * 0.8), (R * 1.6, 0)], sides=6)
    n = 44
    for i in range(n):
        # fibonacci sphere, upper ~80% only (the underside sits in leaves)
        y = 1 - 1.75 * (i + 0.5) / n
        rad = math.sqrt(max(0.0, 1 - y * y))
        a = i * GOLDEN
        dirv = np.array([math.cos(a) * rad, y, math.sin(a) * rad])
        p = c + dirv * R * rng.uniform(0.92, 1.05)
        # violet more likely on the sides and toward one flank, blue on the crown
        side = 0.5 + 0.5 * dirv[0]
        pv = purple * (0.55 + 0.6 * side) - 0.25 * max(0.0, y)
        mat = "petal_tip" if rng.random() < pv else "petal"
        floret(p, norm(dirv + rng.normal(0, 0.15, 3)), R * rng.uniform(0.38, 0.46), rng.uniform(0, 6), mat)


def leaf(base, out, L, W):
    """broad ovate leaf with a folded midrib, angled out and slightly down at the tip"""
    side = norm(np.cross(UP, out))
    d = norm(out + UP * 0.35)
    ts = (0, 0.18, 0.42, 0.7, 1.0)
    pts = [base + d * L * t - UP * L * 0.22 * t * t for t in ts]
    hw = [W * 0.15, W * 0.85, W * 1.0, W * 0.72, 0.0]          # broad ovate with a pointed tip
    fold = UP * W * 0.22
    for i in range(len(ts) - 1):
        a, b = pts[i], pts[i + 1]
        for sg in (-1, 1):
            ea, eb = a + side * sg * hw[i] - fold * (hw[i] / W), b + side * sg * hw[i + 1] - fold * (hw[i + 1] / W)
            M.quad("leaf", a, b, eb, ea) if sg > 0 else M.quad("leaf", b, a, ea, eb)


# ---------------- assemble: a small shrub of 5 stems, each topped by a mophead ----------------
heads = [(0.0, 0.0, 0.50, 0.085), (1.3, 0.11, 0.40, 0.075), (3.2, 0.13, 0.36, 0.072),
         (4.6, 0.10, 0.44, 0.078), (5.7, 0.14, 0.30, 0.066)]
purples = rng.uniform(0.15, 0.85, len(heads))
for (yaw, spread, h, R), pv in zip(heads, purples):
    out = np.array([math.cos(yaw), 0.0, math.sin(yaw)])
    top = out * spread + UP * h
    st = bezier(np.zeros(3) + out * 0.01, out * spread * 0.3 + UP * h * 0.55, top - UP * R * 0.6, 5)
    M.tube("stem", st, list(np.linspace(0.006, 0.0042, len(st))), sides=4)
    mophead(top, R, pv)
    # big opposite leaf pairs up the stem (hydrangea leaves are about as long as the flower head is wide)
    for j, t in enumerate((0.3, 0.6)):
        i = min(int(t * (len(st) - 1)), len(st) - 2)
        p = st[i] + (st[i + 1] - st[i]) * (t * (len(st) - 1) - i)
        for sg in (-1, 1):
            a = yaw + sg * math.pi / 2 + j * 0.9
            lo = np.array([math.cos(a), 0.0, math.sin(a)])
            leaf(p, lo, 0.2 * (1.0 - 0.1 * j), 0.068 * (1.0 - 0.1 * j))
    # a collar of leaves right under the flower head
    for k in range(4):
        a = yaw + k * math.pi / 2 + 0.4
        lo = np.array([math.cos(a), 0.0, math.sin(a)])
        leaf(top - UP * R * 0.85, lo, 0.17 * R / 0.08, 0.062 * R / 0.08)


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
    gltf = {"asset": {"version": "2.0", "generator": "make_hydrangea.py"},
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
glb = write_glb(M, {"stem": ("#4E6E36", True), "leaf": ("#3A6B2E", True), "core": ("#3A4F3A", True),
                    "petal": ("#6F92EE", True), "petal_tip": ("#A47CE2", True)},
                "Hydrangea", OUT / "hydrangea.glb")
if TEMPLATE.exists():
    html = (TEMPLATE.read_text(encoding="utf-8").replace("__GLB_BASE64__", base64.b64encode(glb).decode())
            .replace("cam.position.set(0.5, 0.45, 0.7);", "cam.position.set(0.7, 0.6, 1.0);")
            .replace("ctl.target.set(0, 0.3, 0);", "ctl.target.set(0, 0.3, 0);")
            .replace("Spider Lily Preview", "Hydrangea Preview"))
    (OUT / "preview.html").write_text(html, encoding="utf-8")
