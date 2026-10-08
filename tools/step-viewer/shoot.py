"""tools/step-viewer/shoot.py -- 3-D stills of a tube STEP in headless Chromium (three.js, tools/step-viewer/scene.js).
Setup once:  cd tools/step-viewer && npm install            (three 0.160.0 into node_modules, not committed)
Model:       python3 sim/step_to_glb.py docs/geometry/tube/tube-r150-n8-wound-g0p5-6br.step
Stills:      python3 -m http.server 8765 --bind 127.0.0.1 &      (from the repo root)
             python3 tools/step-viewer/shoot.py 8765 docs/geometry/tube/tube-r150-n8-wound-g0p5-6br [view ...]
Views: cutaway half reluctance plan exploded whole; each is written to <prefix>-3d-<view>.png.
The interactive page (viewer.html) is the same scene with orbit controls; it loads ./model.json, the GLB base64-wrapped
(sim/step_to_glb.py --json), for hosts that do not serve .glb.
"""
import os
import sys

from playwright.sync_api import sync_playwright

port, prefix = sys.argv[1], sys.argv[2]
names = sys.argv[3:] or ["cutaway", "half", "reluctance", "plan", "exploded"]
model = "/" + os.path.relpath(prefix + ".glb", os.getcwd())
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"),
                          args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    logs = []
    for n in names:
        pg = b.new_page(viewport={"width": 1400, "height": 1200}, device_scale_factor=1.5)
        pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        pg.goto(f"http://127.0.0.1:{port}/tools/step-viewer/render.html?model={model}")
        pg.wait_for_function("window.ready === true", timeout=180000)
        w, h = pg.evaluate(f"viewSize('{n}')")
        pg.set_viewport_size({"width": w, "height": h})
        pg.evaluate(f"renderView('{n}')")
        out = f"{prefix}-3d-{n}.png"
        pg.screenshot(path=out)
        print("wrote", out, flush=True)
        pg.close()
    b.close()
    for line in logs:
        print(line)
