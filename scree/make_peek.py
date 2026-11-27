"""Build peek.html (head-tracked "window" 3D) from scree.html.  Run: python make_peek.py

The orthographic diorama camera becomes an off-axis perspective camera: the canvas is a window,
the scene sits in a box behind it, and the eye position comes from the front camera (MediaPipe
FaceLandmarker) or, without a camera, from dragging on the picture.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "scree.html").read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert a in s, "missing: " + a[:70]
    s = s.replace(a, b, 1)


rep("<title>Scree Slope</title>", "<title>Scree Peek</title>")
rep('''  <h4>画面</h4>''', '''  <h4>裸眼3D</h4>
  <div class="row"><button id="trk">📷 ヘッドトラッキング開始</button><span id="trkst" class="hint">オフ（画面をドラッグして試せます）</span></div>
  <label>画面の幅 cm <span class="row"><input type="range" id="scrw" min="4" max="60" step="0.5" value="7"><span id="scrwv">7</span></span></label>
  <label>カメラは画面の上 cm <span class="row"><input type="range" id="camoff" min="0" max="25" step="0.5" value="7"><span id="camoffv">7</span></span></label>
  <label>カメラの画角 <span class="row"><input type="range" id="hfov" min="40" max="90" step="1" value="62"><span id="hfovv">62°</span></span></label>
  <label>立体感の強さ <input type="range" id="peekk" min="0" max="2" step="0.05" value="1"></label>
  <label>箱の奥行き <input type="range" id="boxd" min="0" max="6" step="0.1" value="3.2"></label>
  <label><input type="checkbox" id="box" checked> 箱を表示</label>
  <label><input type="checkbox" id="mirror"> 左右が逆ならチェック</label>

  <h4>画面</h4>''')
# no foreground / lower-edge crop / DOF in window mode (they assume the fixed orthographic view)
rep('''<input type="checkbox" id="fg" checked> 手前のメコノプシス''', '''<input type="checkbox" id="fg"> 手前のメコノプシス''')
rep('''<input type="checkbox" id="clip" checked> 下端を切り取る''', '''<input type="checkbox" id="clip"> 下端を切り取る''')
rep('''<input type="checkbox" id="dof" checked> 被写界深度''', '''<input type="checkbox" id="dof"> 被写界深度''')
rep("uClip: { value: 1 },", "uClip: { value: 0 },")
rep("let dofOn = true;", "let dofOn = false;")
# panel hidden by default on phones so the window fills the screen
rep("  try { if (localStorage.getItem(KEY) === '1') document.body.classList.add('ui-hidden'); } catch {}",
    "  try { const v = localStorage.getItem(KEY); if (v === '1' || (v === null && matchMedia('(pointer: coarse)').matches)) document.body.classList.add('ui-hidden'); } catch {}")
# DOF depth: perspective depth buffer is not linear
rep("float viewZ(vec2 uv){ return uNear + texture2D(tDepth, uv).x * (uFar - uNear); } // ortho depth is linear",
    "uniform float uPersp;\n    float viewZ(vec2 uv){ float d = texture2D(tDepth, uv).x; return uPersp > 0.5 ? (uNear * uFar) / (uFar - d * (uFar - uNear)) : uNear + d * (uFar - uNear); }")
rep("uFocus: { value: 11.2 },", "uPersp: { value: 1 }, uFocus: { value: 11.2 },")

PEEK = r'''
/* ================= window ("parallax peek") camera =================
   The canvas is a window: a rectangle S ± R*W ± U*W in the world, facing the viewer.
   The eye E (from face tracking, in cm relative to the canvas center) looks through it with an
   off-axis frustum (Kooima's generalized perspective projection), so the scene behind the window
   shifts correctly as the head moves. */
const pcam = new THREE.PerspectiveCamera();
const P = {
  W: H,                                   // half-size of the window in world units (= the ortho frame)
  back: 1.55,                             // the window sits this far in front of the scene center
  eyeCm: new THREE.Vector3(0, 0, 40),     // eye position, cm, relative to the canvas center (x right, y up, z out)
  eyeTarget: new THREE.Vector3(0, 0, 40),
};
const coarse = matchMedia('(pointer: coarse)').matches;
if (!coarse) { document.getElementById('scrw').value = 26; document.getElementById('camoff').value = 15; P.eyeCm.z = P.eyeTarget.z = 60; }
document.getElementById('scrwv').textContent = document.getElementById('scrw').value;
document.getElementById('camoffv').textContent = document.getElementById('camoff').value;
const _R = new THREE.Vector3(), _U = new THREE.Vector3(), _N = new THREE.Vector3(), _S = new THREE.Vector3(), _E = new THREE.Vector3(), _B = new THREE.Matrix4();
function windowBasis() {
  cam.updateMatrixWorld();
  _R.setFromMatrixColumn(cam.matrixWorld, 0).normalize();
  _U.setFromMatrixColumn(cam.matrixWorld, 1).normalize();
  _N.setFromMatrixColumn(cam.matrixWorld, 2).normalize();      // toward the viewer
  _S.copy(target).addScaledVector(_N, P.back);
}
function updatePeekCam() {
  windowBasis();
  P.W = cam.top;                                                 // follows the zoom slider
  const k = 2 * P.W / +document.getElementById('scrw').value;    // world units per cm
  const s = +document.getElementById('peekk').value;
  P.eyeCm.lerp(P.eyeTarget, 0.35);
  _E.copy(_S).addScaledVector(_R, P.eyeCm.x * k * s).addScaledVector(_U, P.eyeCm.y * k * s).addScaledVector(_N, Math.max(5, P.eyeCm.z) * k);
  const n = 0.1, f = _E.distanceTo(_S) + 30;
  const va = _S.clone().addScaledVector(_R, -P.W).addScaledVector(_U, -P.W).sub(_E);
  const vb = _S.clone().addScaledVector(_R, P.W).addScaledVector(_U, -P.W).sub(_E);
  const vc = _S.clone().addScaledVector(_R, -P.W).addScaledVector(_U, P.W).sub(_E);
  const d = -va.dot(_N);
  const l = _R.dot(va) * n / d, r = _R.dot(vb) * n / d, b = _U.dot(va) * n / d, t = _U.dot(vc) * n / d;
  pcam.position.copy(_E);
  pcam.quaternion.setFromRotationMatrix(_B.makeBasis(_R, _U, _N));
  pcam.near = n; pcam.far = f;
  pcam.updateMatrixWorld(true);
  pcam.projectionMatrix.makePerspective(l, r, t, b, n, f);
  pcam.projectionMatrixInverse.copy(pcam.projectionMatrix).invert();
  post.uniforms.uNear.value = n; post.uniforms.uFar.value = f;
  // keep the focus on the main poppy from wherever the eye is
  const hero = (genLilies.centers || []).find(c => c.tier === 'L');
  if (hero) { const hv = new THREE.Vector3(hero.x, heightAt(hero.x, hero.z) + HEAD_H * hero.s, hero.z); focusTarget = hv.sub(_E).dot(_N.clone().negate()); }
  updateBox();
}

/* ---- the box behind the window: dim walls with a faint grid, so the depth reads ---- */
const gridTex = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d');
  g.fillStyle = '#1c2225'; g.fillRect(0, 0, 64, 64);
  g.fillStyle = '#2b3438'; g.fillRect(0, 0, 64, 2); g.fillRect(0, 0, 2, 64);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.magFilter = THREE.NearestFilter;
  t.colorSpace = THREE.SRGBColorSpace; return t;
})();
const boxMat = new THREE.MeshBasicMaterial({ map: gridTex, side: THREE.BackSide, fog: false });
const box = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), [boxMat, boxMat, boxMat, boxMat, boxMat, new THREE.MeshBasicMaterial({ visible: false })]);
scene.add(box);
function updateBox() {
  const D = +document.getElementById('boxd').value;
  box.visible = document.getElementById('box').checked && D > 0.05;
  if (!box.visible) return;
  // box from the window plane back by D (+ the scene depth), sized to the window
  const depth = P.back + D;
  box.position.copy(_S).addScaledVector(_N, -depth / 2);
  box.quaternion.setFromRotationMatrix(_B.makeBasis(_R, _U, _N));
  box.scale.set(2 * P.W, 2 * P.W, depth);
  for (const m of [boxMat]) { m.map.repeat.set(8, 8); }
}

/* ---- eye position: drag to simulate, or the front camera ---- */
let tracking = false, dragging = false;
renderer.domElement.addEventListener('pointerdown', e => { if (!tracking) { dragging = true; dragEye(e); } });
addEventListener('pointerup', () => { dragging = false; });
addEventListener('pointermove', e => { if (dragging && !tracking) dragEye(e); });
function dragEye(e) {
  const b = renderer.domElement.getBoundingClientRect();
  const nx = (e.clientX - b.left) / b.width * 2 - 1, ny = -((e.clientY - b.top) / b.height * 2 - 1);
  const w = +document.getElementById('scrw').value;
  P.eyeTarget.set(-nx * w * 0.9, -ny * w * 0.9, P.eyeTarget.z);   // drag right = look in from the left
}
const trkSt = document.getElementById('trkst');
document.getElementById('trk').onclick = async () => {
  if (tracking) return;
  trkSt.textContent = '顔認識を読み込み中…';
  try {
    const { FaceLandmarker, FilesetResolver } = await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs');
    const fs = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm');
    const mk = delegate => FaceLandmarker.createFromOptions(fs, {
      baseOptions: { modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task', delegate },
      runningMode: 'VIDEO', numFaces: 1 });
    let fl;
    try { fl = await mk('GPU'); } catch (e) { fl = await mk('CPU'); }   // some phones / WebViews have no GPU delegate
    trkSt.textContent = 'カメラを要求中…';
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }, audio: false });
    const video = document.createElement('video'); video.playsInline = true; video.muted = true; video.srcObject = stream;
    await video.play();
    tracking = true; trkSt.textContent = 'トラッキング中';
    let last = -1, lost = 0;
    const loop = () => {
      if (video.readyState >= 2 && video.currentTime !== last) {
        last = video.currentTime;
        const res = fl.detectForVideo(video, performance.now());
        const lm = res.faceLandmarks && res.faceLandmarks[0];
        if (lm) {
          lost = 0;
          const a = lm[468] || lm[33], b = lm[473] || lm[263];                 // iris centers (fallback: eye corners)
          const vw = video.videoWidth, vh = video.videoHeight;
          const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
          const ipd = Math.hypot((a.x - b.x) * vw, (a.y - b.y) * vh) / vw;     // eye distance as a fraction of image width
          const th = Math.tan(+document.getElementById('hfov').value * Math.PI / 360);
          const z = 6.3 / (2 * th * Math.max(ipd, 1e-3));                       // cm, from the average eye distance
          const sgn = document.getElementById('mirror').checked ? -1 : 1;
          const x = sgn * (0.5 - mx) * 2 * th * z;
          const y = (0.5 - my) * 2 * th * (vh / vw) * z + +document.getElementById('camoff').value;
          P.eyeTarget.set(x, y, z);
          trkSt.textContent = `トラッキング中 · 目 ${x.toFixed(0)}, ${y.toFixed(0)}, 距離 ${z.toFixed(0)} cm`;
        } else if (++lost > 15) { trkSt.textContent = '顔が見つかりません（インカメラに顔を映してください）'; P.eyeTarget.set(0, 0, P.eyeTarget.z); }
      }
      requestAnimationFrame(loop);
    };
    loop();
  } catch (err) {
    trkSt.textContent = '開始できません：' + (err && err.message || err) + (isSecureContext ? '' : '（カメラには https か localhost が必要です）');
  }
};
if (new URLSearchParams(location.search).has('autotrack')) setTimeout(() => document.getElementById('trk').click(), 300);
for (const id of ['scrw', 'camoff', 'hfov']) document.getElementById(id).addEventListener('input', e => {
  document.getElementById(id + 'v').textContent = e.target.value + (id === 'hfov' ? '°' : '');
});
'''
rep("/* ================= settings: copy / import / 5 save slots ================= */", PEEK + "\n/* ================= settings: copy / import / 5 save slots ================= */")
rep("  renderer.setRenderTarget(rt); renderer.render(scene, cam);", "  updatePeekCam();\n  renderer.setRenderTarget(rt); renderer.render(scene, pcam);")
rep("a.download = 'scree_meconopsis.' + ext;", "a.download = 'scree_peek.' + ext;")

(HERE / "peek.html").write_text(s, encoding="utf-8")
print("ok", len(s))
