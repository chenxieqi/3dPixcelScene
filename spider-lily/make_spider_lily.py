"""Procedural low-poly red spider lily (Lycoris radiata) -> GLB.

No dependencies besides numpy. Run:  python make_spider_lily.py
Outputs spider_lily.glb (Y-up, meters, origin at stem base) and preview.html.
Flat-shaded (per-face normals), flat-color materials -> pixelates cleanly.
"""
import base64, json, math, struct
from pathlib import Path
import numpy as np

rng = np.random.default_rng(7)
UP = np.array([0.0, 1.0, 0.0])
OUT = Path(__file__).resolve().parent


def norm(v):
    return v / np.linalg.norm(v)


def rot(v, axis, ang):
    """Rodrigues rotation of v around unit axis."""
    axis = norm(axis)
    return (v * math.cos(ang) + np.cross(axis, v) * math.sin(ang)
            + axis * np.dot(axis, v) * (1 - math.cos(ang)))


def perp_basis(a):
    helper = UP if abs(np.dot(a, UP)) < 0.9 else np.array([1.0, 0, 0])
    u = norm(np.cross(a, helper))
    v = np.cross(a, u)
    return u, v


# ---------- geometry buckets: material -> list of triangles ----------
tris = {k: [] for k in ("stem", "pedicel", "petal", "filament", "anther")}


def quad(bucket, a, b, c, d):
    tris[bucket] += [(a, b, c), (a, c, d)]


def tube(bucket, pts, radii, sides):
    """Low-poly tube along polyline pts, closed at tip."""
    rings = []
    prev_u = None
    for i, p in enumerate(pts):
        t = norm(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        if prev_u is None:
            u, _ = perp_basis(t)
        else:  # parallel-transport-ish: keep previous u, re-orthogonalize
            u = norm(prev_u - t * np.dot(prev_u, t))
        prev_u = u
        v = np.cross(t, u)
        ring = [p + radii[i] * (math.cos(2 * math.pi * s / sides) * u
                                + math.sin(2 * math.pi * s / sides) * v)
                for s in range(sides)]
        rings.append(ring)
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for s in range(sides):
            n = (s + 1) % sides
            quad(bucket, r0[s], r0[n], r1[n], r1[s])
    tip = pts[-1] + norm(pts[-1] - pts[-2]) * radii[-1]
    for s in range(sides):
        tris[bucket].append((rings[-1][s], rings[-1][(s + 1) % sides], tip))


def bezier(p0, p1, p2, n):
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
            for t in np.linspace(0, 1, n)]


def octa(bucket, c, r, axis):
    u, v = perp_basis(axis)
    a = norm(axis)
    top, bot = c + a * r * 1.4, c - a * r * 1.4
    ring = [c + r * (math.cos(k * math.pi / 2) * u + math.sin(k * math.pi / 2) * v)
            for k in range(4)]
    for k in range(4):
        n = (k + 1) % 4
        tris[bucket].append((ring[k], ring[n], top))
        tris[bucket].append((ring[n], ring[k], bot))


# ---------- stem ----------
STEM_H = 0.42
stem_pts = [np.array([0.004 * math.sin(t * 2.2), STEM_H * t, 0.003 * t * t])
            for t in np.linspace(0, 1, 5)]
tube("stem", stem_pts, [0.0085, 0.008, 0.0075, 0.007, 0.0065], 6)
top = stem_pts[-1]

# ---------- flowers (umbel) ----------
N_FLOWERS = 5
for i in range(N_FLOWERS):
    psi = 2 * math.pi * i / N_FLOWERS + rng.uniform(-0.25, 0.25)
    horiz = np.array([math.cos(psi), 0.0, math.sin(psi)])

    # pedicel: short, pale, angled up/out
    ped_dir = norm(horiz * math.sin(math.radians(45)) + UP * math.cos(math.radians(45)))
    ped_len = 0.042 + rng.uniform(-0.004, 0.006)
    C = top + ped_dir * ped_len
    tube("pedicel", bezier(top, top + UP * ped_len * 0.5, C, 3), [0.0035, 0.003, 0.0028], 5)

    # flower axis: faces outward and a bit up
    elev = math.radians(rng.uniform(5, 25))
    a = norm(horiz * math.cos(elev) + UP * math.sin(elev))
    u, v = perp_basis(a)
    octa("pedicel", C, 0.004, a)  # ovary / receptacle

    # 6 recurved, wavy tepals
    for k in range(6):
        beta = 2 * math.pi * k / 6 + rng.uniform(-0.15, 0.15)
        radial = math.cos(beta) * u + math.sin(beta) * v
        side = np.cross(a, radial)  # width direction (azimuthal)
        L = 0.065 * rng.uniform(0.9, 1.1)
        SEG = 5
        phi0, phi1 = math.radians(35), math.radians(rng.uniform(190, 220))
        p = C + a * 0.002
        cl, tans = [p.copy()], []
        for s in range(SEG):
            t = (s + 0.5) / SEG
            phi = phi0 + (phi1 - phi0) * t ** 1.3
            d = a * math.cos(phi) + radial * math.sin(phi)
            tans.append(d)
            p = p + d * (L / SEG)
            cl.append(p.copy())
        tans = [tans[0]] + tans
        rows = []
        for s, (c, tg) in enumerate(zip(cl, tans)):
            t = s / SEG
            w = 0.0075 * math.sin(math.pi * (0.12 + 0.82 * t)) + 0.0006
            wave = math.radians(28) * math.sin(2 * math.pi * t * 1.3 + k)
            wd = rot(side, tg, wave)
            nrm = norm(np.cross(tg, wd))
            rows.append((c - wd * w, c + nrm * w * 0.35, c + wd * w))  # V crease
        for s in range(SEG):
            l0, m0, r0 = rows[s]
            l1, m1, r1 = rows[s + 1]
            quad("petal", l0, m0, m1, l1)
            quad("petal", m0, r0, r1, m1)

    # 6 stamens + 1 pistil: long whiskers arching outward and up
    for k in range(7):
        beta = 2 * math.pi * k / 6 + rng.uniform(-0.3, 0.3)
        radial = math.cos(beta) * u + math.sin(beta) * v
        s = rng.uniform(0.85, 1.1) * (1.15 if k == 6 else 1.0)
        if k == 6:
            radial = radial * 0.3
        p0 = C + a * 0.004
        p1 = C + (a * 0.055 + radial * 0.02) * s
        p2 = C + (a * 0.085 + radial * 0.055 + UP * 0.018) * s
        pts = bezier(p0, p1, p2, 5)
        tube("filament", pts, [0.002, 0.0019, 0.0017, 0.0015, 0.0013], 3)
        if k < 6:
            octa("anther", pts[-1], 0.0022, pts[-1] - pts[-2])


# ---------- GLB writer ----------
def srgb2lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


MATS = {  # name: (hex sRGB, doubleSided)
    "stem": ("#6E8B2F", False),
    "pedicel": ("#C9D29A", False),
    "petal": ("#D8283A", True),
    "filament": ("#E2463F", False),
    "anther": ("#6A3B1F", False),
}

bin_data = bytearray()
buffer_views, accessors, primitives, materials = [], [], [], []
total_tris = 0
for mi, (name, (hexc, ds)) in enumerate(MATS.items()):
    materials.append({"name": name, "doubleSided": ds,
                      "pbrMetallicRoughness": {"baseColorFactor": srgb2lin(hexc),
                                               "metallicFactor": 0.0, "roughnessFactor": 0.85}})
    T = np.array(tris[name], dtype=np.float32)  # (n,3,3)
    total_tris += len(T)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    pos = T.reshape(-1, 3)
    nor = np.repeat(n, 3, axis=0).astype(np.float32)
    attrs = {}
    for key, arr in (("POSITION", pos), ("NORMAL", nor)):
        raw = arr.astype(np.float32).tobytes()
        buffer_views.append({"buffer": 0, "byteOffset": len(bin_data), "byteLength": len(raw),
                             "target": 34962})
        bin_data += raw
        acc = {"bufferView": len(buffer_views) - 1, "componentType": 5126,
               "count": len(arr), "type": "VEC3"}
        if key == "POSITION":
            acc["min"] = arr.min(axis=0).tolist()
            acc["max"] = arr.max(axis=0).tolist()
        accessors.append(acc)
        attrs[key] = len(accessors) - 1
    primitives.append({"attributes": attrs, "material": mi, "mode": 4})

gltf = {
    "asset": {"version": "2.0", "generator": "make_spider_lily.py"},
    "scene": 0, "scenes": [{"nodes": [0]}],
    "nodes": [{"name": "SpiderLily", "mesh": 0}],
    "meshes": [{"name": "SpiderLily", "primitives": primitives}],
    "materials": materials, "accessors": accessors, "bufferViews": buffer_views,
    "buffers": [{"byteLength": len(bin_data)}],
}
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * ((4 - len(js) % 4) % 4)
bin_data += b"\0" * ((4 - len(bin_data) % 4) % 4)
glb = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_data))
       + struct.pack("<II", len(js), 0x4E4F534A) + js
       + struct.pack("<II", len(bin_data), 0x004E4942) + bytes(bin_data))
(OUT / "spider_lily.glb").write_bytes(glb)

tpl = (OUT / "preview_template.html").read_text(encoding="utf-8")
(OUT / "preview.html").write_text(tpl.replace("__GLB_BASE64__", base64.b64encode(glb).decode()),
                                  encoding="utf-8")
print(f"triangles: {total_tris}  bytes: {len(glb)}")
for k, v in tris.items():
    print(f"  {k}: {len(v)}")
