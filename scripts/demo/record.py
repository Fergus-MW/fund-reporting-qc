"""Record docs/media/demo.mp4 and demo.gif: one project graph forming, then a close zoom.

Needs `make up` with a seeded workspace (seed.py), the forming page served by
`cd frontend && npx vite --config ../scripts/demo/forming/vite.config.mjs`,
Python Playwright with Chromium, and ffmpeg.

    python scripts/demo/record.py "$(node scripts/demo/session.mjs you@example.com)" PROJECT_ID
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND, FORMING = "http://localhost:18081", "http://localhost:18090"
MEDIA = Path(__file__).resolve().parents[2] / "docs" / "media"
SIZE = {"width": 1280, "height": 800}


def graph(cookie, project_id):
    request = urllib.request.Request(f"{FRONTEND}/api/graph/views/{project_id}", headers={"Cookie": f"connection={cookie}"})
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main(cookie, project_id):
    data = graph(cookie, project_id)
    with tempfile.TemporaryDirectory() as videos, sync_playwright() as playwright:
        # SwiftShader gives headless Chromium WebGL for Sigma.
        browser = playwright.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        context = browser.new_context(viewport=SIZE, record_video_dir=videos, record_video_size=SIZE)
        page = context.new_page()
        opened = time.monotonic()
        page.goto(FORMING)
        page.wait_for_function("typeof window.play === 'function'")
        page.wait_for_timeout(300)
        start = time.monotonic() - opened
        print(page.evaluate("data => window.play(data)", data))
        page.wait_for_timeout(200)
        context.close()
        browser.close()
        webm = next(Path(videos).glob("*.webm"))
        mp4, gif = MEDIA / "demo.mp4", MEDIA / "demo.gif"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", webm, "-c:v", "libx264",
                        "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", mp4], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf",
                        "fps=8,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=48:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle",
                        gif], check=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
