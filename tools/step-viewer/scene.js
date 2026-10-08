// Shared three.js scene for the DCCREG tube model (model.glb from sim/step_to_glb.py): lights, materials with darkened
// back faces (cut interiors read as section), polygon offsets for the parts that touch, clipping, an exploded utron and
// camera views with labelled anchors. Used by the headless stills and by the interactive viewer.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

// model.glb directly, or model.json (the same GLB base64-wrapped, for hosts that serve JSON but not .glb)
async function loadGLTF(url) {
  const loader = new GLTFLoader();
  if (!url.endsWith(".json")) return loader.loadAsync(url);
  const j = await (await fetch(url)).json();
  const bin = Uint8Array.from(atob(j.glb), (c) => c.charCodeAt(0));
  return loader.parseAsync(bin.buffer, "");
}

// parts that share a surface with a neighbour are pushed back in depth so the neighbour wins (no z-fighting)
const OFFSET = [[/^shaft_/, 4], [/_bearing_/, 3], [/^rotor_sleeve/, 2], [/stator_cage/, 2],
                [/(bridge_ring|_strip|_spacer|_cheek|_wedge|carrier_disc|ring_flange)/, 1]];

export async function buildScene(renderer, url) {
  renderer.localClippingEnabled = true;
  const scene = new THREE.Scene();
  const gltf = await loadGLTF(url);
  const root = gltf.scene;
  scene.add(root);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;     // metals need something to reflect
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8b9099, 0.45));
  const key = new THREE.DirectionalLight(0xffffff, 1.5); key.position.set(1.2, -1.6, 2.2); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.35); fill.position.set(-1.5, -0.6, 0.4); scene.add(fill);
  const planes = { x: new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0), y: new THREE.Plane(new THREE.Vector3(0, 1, 0), 0) };
  const parts = [];
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!o.isMesh) return;
    const info = (o.userData && o.userData.part) ? o.userData : (o.parent && o.parent.userData) || {};
    const name = info.part || o.name;
    const m = o.material.clone();
    m.side = THREE.DoubleSide;
    const off = (OFFSET.find(([re]) => re.test(name)) || [null, 0])[1];
    m.polygonOffset = off > 0; m.polygonOffsetFactor = off; m.polygonOffsetUnits = 4 * off;
    m.onBeforeCompile = (sh) => {
      sh.fragmentShader = sh.fragmentShader.replace("#include <dithering_fragment>",
        "#include <dithering_fragment>\n  if (!gl_FrontFacing) gl_FragColor.rgb *= 0.55;");
    };
    o.material = m;
    parts.push({ mesh: o, part: name, body: info.body || "", group: info.group || "", material: info.material || "",
                 label: info.label || name, home: o.position.clone(), homeQ: o.quaternion.clone(),
                 role: classify(name, info.body || "") });
  });
  const box = new THREE.Box3().setFromObject(root);
  return { scene, root, parts, planes, box };
}

// which body a part turns with: the rotor, the counter-rotor (the stator body, geared 1 : -1) or the frame
export function classify(name, body) {
  if (/_(bearing|spider)_end$/.test(name)) return "frame";
  if (body === "bearing") return "bearing";
  return body === "stator" ? "counter" : "rotor";
}

// turn the rotor by +a and the counter-rotor by -a (radians) about the shaft, on top of the explode offsets
const ZAX = new THREE.Vector3(0, 0, 1);
export function spin(S, a) {
  for (const p of S.parts) {
    const s = p.role === "rotor" ? 1 : p.role === "counter" ? -1 : 0;
    const base = p.mesh.userData.explodedPos || p.home;
    p.mesh.position.copy(base).applyAxisAngle(ZAX, s * a);
    p.mesh.quaternion.setFromAxisAngle(ZAX, s * a).multiply(p.homeQ);
  }
  S.root.updateMatrixWorld(true);
}

export function bboxOf(S, re) {
  const b = new THREE.Box3();
  for (const p of S.parts) if (re.test(p.part)) b.expandByObject(p.mesh);
  return b;
}

// cut: "none" | "quarter" (x > 0 and y < 0 removed) | "half" (y < 0 removed)
export function setCut(S, cut) {
  for (const p of S.parts) {
    const m = p.mesh.material;
    m.clippingPlanes = cut === "quarter" ? [S.planes.x, S.planes.y] : cut === "half" ? [S.planes.y] : [];
    m.clipIntersection = cut === "quarter";
    m.needsUpdate = true;
  }
}

// exploded utron A1 (at 0 deg its local u, v, w are the world x, y, z), offsets in mm
// along the assembly directions: the half-cores, strip and spacer slide tangentially (v = y) through the coil's
// window, the cheeks come off the stack ends, the slot cover and the bridge lift radially
const EXPLODE = { A_U1_core_pos: [0, 62, 0], A_U1_core_neg: [0, -62, 0], A_U1_strip: [0, -128, 0], A_U1_spacer: [0, 112, 0],
                  A_U1_wedge: [24, 0, 0], A_bridge_1: [62, 0, 0],
                  A_U1_cheek_pos_hi: [0, 62, 34], A_U1_cheek_pos_lo: [0, 62, -34],
                  A_U1_cheek_neg_hi: [0, -62, 34], A_U1_cheek_neg_lo: [0, -62, -34] };

export function setExplode(S, on) {
  for (const p of S.parts) {
    const d = on && EXPLODE[p.part];
    p.mesh.position.copy(p.home);
    p.mesh.quaternion.copy(p.homeQ);
    if (d) p.mesh.position.add(new THREE.Vector3(d[0], d[1], d[2]));   // node space is mm (root scaled to m)
    p.mesh.userData.explodedPos = d ? p.mesh.position.clone() : null;
  }
  S.root.updateMatrixWorld(true);
}

export function aim(camera, target, dir, dist, up) {
  const d = new THREE.Vector3(...dir).normalize();
  camera.position.copy(target.clone().add(d.multiplyScalar(dist)));
  camera.up.set(...(up || [0, 0, 1]));
  camera.lookAt(target);
  camera.updateProjectionMatrix();
}

const SECTIONS = [[/^A_U\d_core/, "reluctance A: 3 utrons (rotor), 6 bridges (counter-rotor)"], [/^A_Ca_/, "Ca fixed plates"],
                  [/^A_C1_/, "C1 varicap: 8 stator + 8 rotor vanes"], [/^hub_bicone/, "hub: bicone + AH (placeholder)"],
                  [/^B_C2_/, "C2 varicap"], [/^B_Cb_/, "Cb fixed plates"],
                  [/^B_U\d_core/, "reluctance B: bridges offset 30°"]];

// the views (world units: metres, z up). labels: [anchor (world), text, dx px, dy px]
export function views(S) {
  const c = S.box.getCenter(new THREE.Vector3());
  const zA = bboxOf(S, /^A_U\d_core/);
  const zc = zA.getCenter(new THREE.Vector3());
  const R = S.box.max.x;
  const sec = (x) => SECTIONS.map(([re, t]) => {
    const b = bboxOf(S, re);
    return [new THREE.Vector3(x, 0, 0.5 * (b.min.z + b.max.z)), t, 70, 0];
  });
  const ctr = (re) => bboxOf(S, re).getCenter(new THREE.Vector3());
  return {
    cutaway: { title: "Quarter cutaway at rotor angle 0 (rotor + counter-rotor geared 1 : −1; frame: the end bearings)",
               cut: "quarter", explode: false, show: () => true, size: [1400, 1500],
               target: c.clone().setZ(c.z - 0.01), dir: [1.0, -1.25, 0.5], dist: 2.45, labels: [] },
    half: { title: "Half section (the near half removed): the machine from the front", cut: "half", explode: false,
            show: () => true, size: [1500, 1500], target: c.clone().setX(c.x + 0.09), dir: [0.18, -1.0, 0.22], dist: 2.3,
            labels: sec(R * 0.98) },
    reluctance: { title: "Reluctance section A, quarter cut: 3 wound utrons on the rotor, 6 passive bridges in the G10 ring",
                  cut: "quarter", explode: false, size: [1500, 1150], zTop: zA.max.z + 0.033,
                  show: (p) => new THREE.Box3().setFromObject(p.mesh).min.z < zA.max.z + 0.04,
                  target: zc.clone().setZ(zc.z - 0.012), dir: [1.0, -1.0, 0.8], dist: 1.0,
                  labels: [[new THREE.Vector3(0.112, 0, zc.z + 0.03), "utron A1, cut through its centre: coil, neck strip, air break", 80, -210],
                           [new THREE.Vector3(0.1375, 0, zc.z - 0.02), "bridge A1, aligned (gap 0.5 mm)", 140, -20],
                           [ctr(/^A_U3_core_pos$/), "utron A3: half-cores, cheeks with studs, coil", -90, -230],
                           [new THREE.Vector3(0.155 * Math.cos(1.95), 0.155 * Math.sin(1.95), zA.max.z + 0.03), "bridge ring, G10 (counter-rotor)", -150, -40],
                           [new THREE.Vector3(0.03, 0.0, zA.max.z + 0.016), "carrier disc, G10, on the rotor sleeve", 200, -150],
                           [new THREE.Vector3(0.0, 0.0, 0.004), "end bearing (frame)", -200, 60]] },
    plan: { title: "Plan view of reluctance A, cut at mid-stack: utrons A1 to A3 aligned under bridges (B is unaligned)",
            cut: "none", explode: false, size: [1300, 1300], zTop: zc.z, show: (p) => p.group === "rel-A" || p.group === "rotor",
            target: new THREE.Vector3(0, 0, zc.z), dir: [0.0001, -0.0001, 1], dist: 0.82, up: [0, 1, 0], labels: [] },
    whole: { title: "The whole machine", cut: "none", explode: false, show: () => true, size: [1400, 1500],
             target: c.clone(), dir: [1.0, -1.25, 0.5], dist: 2.45, labels: [] },
    exploded: { title: "Utron A1 exploded along its assembly directions, with bridge A1", cut: "none", explode: true,
                size: [1600, 1150], show: (p) => p.part.startsWith("A_U1_") || p.part === "A_bridge_1",
                target: new THREE.Vector3(0.112, 0, zc.z), dir: [1.0, -0.62, 0.75], dist: 0.82,
                labels: [["A_U1_core_pos", "half-core (+v), M235-35A, tip face on the gap arc", 40, -150],
                         ["A_U1_core_neg", "half-core (−v)", -60, -150],
                         ["A_U1_strip", "neck: 80 % NiFe strip, 3.0 × 100 mm (30 × 0.1)", -40, 110],
                         ["A_U1_spacer", "air-break spacer, G10, 12 mm", 40, 110],
                         ["A_U1_wedge", "slot cover, G10 (bonded)", 60, -110],
                         ["A_bridge_1", "bridge, SiFe (counter-rotor)", 90, 70],
                         ["A_U1_cheek_pos_hi", "cheeks, G10, studded to the half-cores", 50, -60],
                         ["A_U1_winding", "yoke coil: 200 turns of Ø1.55 mm on a G10 former", -150, 330]] },
  };
}

export function applyView(S, camera, v, renderer) {
  setExplode(S, v.explode);
  for (const p of S.parts) p.mesh.visible = v.show(p);
  setCut(S, v.cut);
  if (renderer) renderer.clippingPlanes = v.zTop ? [new THREE.Plane(new THREE.Vector3(0, 0, -1), v.zTop)] : [];
  aim(camera, v.target, v.dir, v.dist, v.up);
}

// screen-space labels: each [anchor, text, dx, dy]; anchor a world point or a part name (its exploded centre)
export function labelPositions(S, camera, v, W, H) {
  return (v.labels || []).map(([a, text, dx, dy]) => {
    const p = typeof a === "string" ? bboxOf(S, new RegExp("^" + a + "$")).getCenter(new THREE.Vector3()) : a.clone();
    p.project(camera);
    return { x: (p.x + 1) / 2 * W, y: (1 - p.y) / 2 * H, dx, dy, text };
  });
}
