#!/usr/bin/env python3
"""Genera i JPEG dei post da calendar.json (1080x1350, qualità 92) e prepara i video dei reel.

  python3 instagram/render.py            # tutti i post non ancora pubblicati
  python3 instagram/render.py --id X     # un solo post
  python3 instagram/render.py --force    # rigenera anche se nulla è cambiato
Richiede: playwright (chromium) e, per i reel, ffmpeg.
"""
import argparse, hashlib, json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import templates as T  # noqa: E402

FONTS_URL = (HERE.parent / "public" / "fonts").as_uri()

CHECK_JS = """() => {
  const out = [], boxes = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const n = w.currentNode; if (!n.textContent.trim()) continue;
    const r = document.createRange(); r.selectNodeContents(n);
    const b = r.getBoundingClientRect(); if (!b.width) continue;
    boxes.push({t: n.textContent.trim().slice(0, 40), l: b.left, t_: b.top, r: b.right, b: b.bottom});
  }
  for (const x of boxes) {
    if (x.r > 1080 - 56 || x.b > 1350 - 56 || x.l < 40 || x.t_ < 40) out.push('fuori margine: ' + x.t);
  }
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], c = boxes[j];
    const ow = Math.min(a.r, c.r) - Math.max(a.l, c.l), oh = Math.min(a.b, c.b) - Math.max(a.t_, c.t_);
    if (ow > 4 && oh > 4) out.push('testi sovrapposti: «' + a.t + '» / «' + c.t + '»');
  }
  return out;
}"""

def digest(post):
    h = hashlib.sha1((HERE / "templates.py").read_bytes())
    h.update(json.dumps(post.get("slides", []), sort_keys=True).encode())
    for s in post.get("slides", []):
        if s.get("photo") and (HERE / s["photo"]).exists():
            h.update((HERE / s["photo"]).read_bytes())
    if post.get("video") and (HERE / post["video"]).exists():
        h.update(str((HERE / post["video"]).stat().st_size).encode())
    return h.hexdigest()

def prep_video(post, out_dir):
    src = HERE / post["video"]
    if not src.exists():
        raise RuntimeError(f"video mancante ({post['video']})")
    dst = out_dir / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-t", str(post.get("max_seconds", 90)),
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dst)], check=True)
    cover = out_dir / "cover.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(post.get("cover_at", 1)), "-i", str(dst),
                    "-frames:v", "1", "-q:v", "2", str(cover)], check=True)
    print(f"  video pronto: {dst.stat().st_size / 1e6:.1f} MB")

def render_post(post, page, force):
    out_dir = HERE / "media" / post["id"]
    stamp = out_dir / ".hash"
    d = digest(post)
    if not force and stamp.exists() and stamp.read_text() == d:
        print(f"= {post['id']} invariato"); return
    if post.get("video") and not (HERE / post["video"]).exists():
        raise RuntimeError(f"video mancante ({post['video']})")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in list(out_dir.glob("*.jpg")) + list(out_dir.glob("*.mp4")):
        old.unlink()
    slides = post.get("slides", [])
    for k, s in enumerate(slides):
        photo_url = None
        if s["template"] in T.NEEDS_PHOTO:
            if not s.get("photo") or not (HERE / s["photo"]).exists():
                raise RuntimeError(f"slide {k + 1}: foto mancante ({s.get('photo')})")
            photo_url = (HERE / s["photo"]).resolve().as_uri()
        html = T.page(s, k, len(slides), FONTS_URL, photo_url)
        tmp = HERE / ".build.html"; tmp.write_text(html)
        page.goto(tmp.as_uri()); page.evaluate("document.fonts.ready"); page.wait_for_timeout(150)
        problems = page.evaluate(CHECK_JS)
        if problems:
            raise RuntimeError(f"slide {k + 1}: " + "; ".join(problems))
        page.screenshot(path=str(out_dir / f"{k + 1:02d}.jpg"), type="jpeg", quality=92,
                        clip={"x": 0, "y": 0, "width": T.W, "height": T.H})
    if post.get("video"):
        prep_video(post, out_dir)
    stamp.write_text(d)
    print(f"+ {post['id']}: {len(slides)} immagini" + (" + video" if post.get("video") else ""))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id"); ap.add_argument("--force", action="store_true"); ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    cal = json.loads((HERE / "calendar.json").read_text())
    posts = [p for p in cal["posts"] if p.get("status") != "published" and (not a.id or p["id"] == a.id)]
    if not posts:
        print("niente da generare"); return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(); pg = br.new_page(viewport={"width": T.W, "height": T.H})
        skipped = []
        for p in posts:
            try:
                render_post(p, pg, a.force)
            except RuntimeError as ex:
                skipped.append(p["id"]); print(f"- {p['id']} saltato: {ex}")
        br.close()
    if skipped and a.strict:
        sys.exit(1)
    tmp = HERE / ".build.html"
    if tmp.exists(): tmp.unlink()

if __name__ == "__main__":
    main()
