"""Procedural blue poppy (美丽绿绒蒿, Meconopsis speciosa) -> meconopsis.glb (+ preview.html).

numpy only. Run:  python make_meconopsis.py [out_dir] [seed]
Close to the reference photos, kept under 3k tris. One stout upright stem carrying a dense spike of
~16 sky-blue saucer flowers facing outward and slightly nodding (the lowest few on long arching
stalks, smaller toward the top). Each flower has 6 broad rounded crinkled petals, a dark purple
filament fringe, a yellow anther ring and a dark ovary. A bristly tip with small buds; a rosette of
deeply cut, narrow-lobed grey-green leaves. Y-up, meters, origin at the base, flat shaded.
Named materials:
  stem, leaf, petal_base, petal, petal_edge (blue, deep -> pale), filament (dark purple fringe),
  anther (yellow ring), ovary, bud
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


M = Mesh(["stem", "leaf", "petal_base", "petal", "petal_edge", "filament", "anther", "ovary", "bud"])


def bezier(p0, p1, p2, n):
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in np.linspace(0, 1, n)]


# ---------------- organs ----------------
def petal(c, face, d, L, W, cup):
    """broad rounded papery petal on a grid: deep cup, edges curling up, ruffled/crinkled"""
    s = np.cross(face, d)
    ts = [0.05, 0.5, 0.9]
    hws = [0.25, 1.0, 0.7]
    K = 2                                                   # samples on each side of the midline
    ph = rng.uniform(0, 6, 3)

    def P(t, y):
        z = cup * t * t + 0.22 * (y ** 2) * t                # bowl + edge curl
        z += t ** 2 * (0.045 * math.sin(6 * y + ph[0]) + 0.03 * math.sin(13 * y + ph[2]))   # ruffled rim
        z += 0.02 * math.sin(10 * t + 4 * y + ph[1]) * t     # papery crinkle
        return c + d * L * t + s * W * L * y * float(np.interp(t, ts, hws)) + face * L * z

    rows = [[P(t, k / K) for k in range(-K, K + 1)] for t in ts]
    for i in range(len(ts) - 1):
        mat = "petal_base" if i == 0 else "petal"
        A, B = rows[i], rows[i + 1]
        for k in range(2 * K):
            M.quad(mat, A[k], A[k + 1], B[k + 1], B[k])
    tip = P(1.02, 0.0)                                      # rounded tip
    last = rows[-1]
    for k in range(2 * K):
        M.tri("petal_edge", last[k], last[k + 1], tip)


def flower(c, face, L, spin, npet=4):
    """nodding cup of 4 broad overlapping papery petals around a brush of indigo stamens with yellow anthers"""
    u, w = frame(face)
    for k in range(npet):
        a = spin + k * 2 * math.pi / npet + rng.uniform(-0.12, 0.12)
        d = norm(math.cos(a) * u + math.sin(a) * w + face * 0.3)
        petal(c + face * 0.0008 * k, face, d, L * rng.uniform(0.92, 1.08), 0.82, 0.62)
    base = c + face * L * 0.04
    # dense indigo mass of filaments at the base
    M.lathe("filament", base, face, [(0, L * 0.2), (L * 0.18, L * 0.24), (L * 0.36, 0)],
            sides=5, spin=spin)
    # a brush of stamens fanning out: thin indigo filaments, yellow anthers at the tips
    for k in range(8):
        a = rng.uniform(0, 2 * math.pi)
        dd = math.cos(a) * u + math.sin(a) * w
        dn = -math.sin(a) * u + math.cos(a) * w
        fd = norm(face + dd * rng.uniform(0.3, 1.0))
        ln = L * rng.uniform(0.38, 0.58)
        p0 = base + dd * L * rng.uniform(0.02, 0.1)
        p1 = p0 + fd * ln
        hw = L * 0.026
        M.tri("filament", p0 + dn * hw * 1.5, p0 - dn * hw * 1.5, p1)
        r = L * rng.uniform(0.09, 0.12)
        M.quad("anther", p1 - dn * r, p1 - dd * r, p1 + dn * r, p1 + dd * r * 1.2)   # flat diamond facing out of the flower
    # green pistil peeking out of the middle


def bud(c, axis, size):
    M.lathe("bud", c, axis, [(0, 0), (size * 0.25, size * 0.36), (size * 0.65, size * 0.38),
                             (size * 1.15, 0)], sides=4, spin=rng.uniform(0, 6))


def leaf(base, out, L, rise, droop, nlobe=7, width=1.0):
    """deeply pinnatisect leaf: thin midrib with pairs of narrow linear lobes angled forward"""
    side = norm(np.cross(UP, out))
    n = nlobe + 2
    pts = [base + out * L * t + UP * (L * rise * math.sin(math.pi * t * 0.7) - droop * L * t * t)
           for t in np.linspace(0, 1, n)]
    M.tube("leaf", pts, list(np.linspace(0.0025, 0.0008, n)), sides=3)
    for i in range(1, n - 1):
        a = pts[i]; fwd = norm(pts[i + 1] - pts[i - 1])
        f = math.sin(math.pi * (i / (n - 1)) * 0.9 + 0.25)          # lobes longest in the middle
        ll = L * 0.15 * f * width
        hw = 0.0065
        for sg in (-1, 1):
            dirl = norm(side * sg + fwd * 0.7 + UP * 0.15)
            q0, q1 = a + fwd * hw, a - fwd * hw
            mid = a + dirl * ll * 0.55
            m0, m1 = mid + fwd * hw * 1.0, mid - fwd * hw * 1.0
            M.quad("leaf", q1, q0, m0, m1)
            M.tri("leaf", m1, m0, a + dirl * ll)
    M.tri("leaf", pts[-2] + side * 0.003, pts[-2] - side * 0.003, pts[-1] + (pts[-1] - pts[-2]) * 0.8)


# ---------------- assemble ----------------
H = 0.62
stem = bezier(np.array([0.0, 0.0, 0.0]), np.array([0.008, H * 0.5, 0.0]), np.array([-0.01, H, 0.006]), 10)
M.tube("stem", stem, list(np.linspace(0.0095, 0.004, len(stem))), sides=5)
P = np.array(stem)
seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
cum = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()


def at(s):
    i = max(min(np.searchsorted(cum, s) - 1, len(P) - 2), 0)
    f = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    return P[i] + (P[i + 1] - P[i]) * f, norm(P[i + 1] - P[i])


N = 16
for i in range(N):
    u = i / (N - 1)                                  # 0 lowest (oldest) .. 1 highest
    base, tan = at(0.24 + 0.64 * u ** 0.9)
    a1, a2 = frame(tan)
    ang = i * GOLDEN
    out = norm(math.cos(ang) * a1 + math.sin(ang) * a2)
    L = 0.040 * (1.1 - 0.35 * u) * rng.uniform(0.94, 1.06)
    if i < 3:   # the lowest few on long stalks that arch out and up
        Lp = rng.uniform(0.07, 0.11)
        p1 = base + out * Lp * 0.3 + tan * Lp * 0.75
        p2 = base + out * Lp * 0.75 + tan * Lp * 0.95
        M.tube("stem", [base, p1, p2], [0.0028, 0.0025, 0.0022], sides=4)
    else:       # short pedicels: the flowers crowd around the stem as a dense spike
        Lp = 0.012 + 0.012 * (1 - u)
        p2 = base + out * Lp + tan * Lp * 0.3
        M.tube("stem", [base, p2], [0.0025, 0.002], sides=4)
    face = norm(out * 0.9 - tan * (0.45 - 0.25 * u) + rng.normal(0, 0.08, 3))
    flower(p2 + face * 0.002, face, L, rng.uniform(0, 6))

# small buds near the tip
for s_at, ang, sz in ((0.9, 0.5, 0.022), (0.93, 2.7, 0.018), (0.96, 4.6, 0.015), (0.99, 1.3, 0.012)):
    b0, t0 = at(s_at)
    a1, a2 = frame(t0)
    out = norm(math.cos(ang) * a1 + math.sin(ang) * a2)
    b1 = b0 + out * 0.008 + t0 * 0.008
    M.tube("stem", [b0, b1], [0.002, 0.0018], sides=3)
    bud(b1, norm(out * 0.5 + t0 * 0.6), sz)
# bristles / narrow bracts along the top
for k in range(8):
    b0, t0 = at(0.86 + 0.14 * k / 9)
    a1, a2 = frame(t0)
    ang = k * 2.4
    out = norm(math.cos(ang) * a1 + math.sin(ang) * a2)
    M.tri("bud", b0 + t0 * 0.002, b0 - t0 * 0.002, b0 + out * 0.012 + t0 * 0.012)

# basal rosette + a few leaves on the lower stem
for k in range(6):
    yaw = k * 2 * math.pi / 6 + rng.uniform(-0.25, 0.25)
    leaf(np.array([0.0, 0.008, 0.0]), np.array([math.cos(yaw), 0.0, math.sin(yaw)]),
         rng.uniform(0.15, 0.21), rng.uniform(0.7, 1.1), 0.45, nlobe=7)
for s_at, yaw, L in ((0.10, 1.0, 0.11), (0.17, 3.6, 0.09), (0.22, 5.4, 0.07)):
    b, _ = at(s_at)
    leaf(b, np.array([math.cos(yaw), 0.0, math.sin(yaw)]), L, 0.7, 0.5, nlobe=5, width=0.8)


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
    gltf = {"asset": {"version": "2.0", "generator": "make_meconopsis.py"},
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
glb = write_glb(M, {"stem": ("#5F7F3E", True), "leaf": ("#6E8C55", True),
                    "petal_base": ("#4A80DE", True), "petal": ("#6A9FEC", True), "petal_edge": ("#88B5F1", True),
                    "filament": ("#34338A", True), "anther": ("#D9AE2C", True), "ovary": ("#6E8A4A", True),
                    "bud": ("#56663A", True)},
                "Meconopsis", OUT / "meconopsis.glb")
if TEMPLATE.exists():
    html = (TEMPLATE.read_text(encoding="utf-8").replace("__GLB_BASE64__", base64.b64encode(glb).decode())
            .replace("cam.position.set(0.5, 0.45, 0.7);", "cam.position.set(0.6, 0.5, 0.95);")
            .replace("ctl.target.set(0, 0.3, 0);", "ctl.target.set(0, 0.34, 0);")
            .replace("Spider Lily Preview", "Meconopsis Preview"))
    (OUT / "preview.html").write_text(html, encoding="utf-8")
