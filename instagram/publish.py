#!/usr/bin/env python3
"""Pubblica su Instagram i post di calendar.json con stato «approved» e data passata.

Comandi:
  due        stampa gli id dei post da pubblicare adesso (e li scrive in $GITHUB_OUTPUT)
  lint       controlla tutti i post (regole di sicurezza e media presenti)
  publish    pubblica i post dovuti  [--id X] [--dry-run] [--now 2026-11-02T18:30]
  status     elenco dei post con stato e data
  refresh    rinnova il token Instagram (60 giorni) e, se c'è GH_PAT, aggiorna il segreto IG_TOKEN

Variabili: IG_USER_ID, IG_TOKEN  (obbligatorie per publish/refresh)
           IG_API_BASE (default https://graph.instagram.com), IG_API_VERSION (default v23.0)
           MEDIA_BASE_URL (default: raw.githubusercontent.com della repo corrente)
Solo libreria standard di Python.
"""
import argparse, hashlib, json, os, pathlib, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
CAL = HERE / "calendar.json"
TYPES = {"image", "carousel", "reel", "story"}

# Rete di sicurezza per la pubblicità sanitaria (L. 145/2018 c. 525-536: solo informazione,
# niente toni promozionali, suggestivi o comparativi). Non è una consulenza legale.
BANNED = [r"prima e dopo", r"before\s*/?\s*after", r"guarisc", r"guarigion", r"garantit", r"\bmigliore\b",
          r"\bmigliori\b", r"\bil primo\b", r"\bl'unico\b", r"100\s*%", r"\bsconto", r"\bofferta", r"\bpromo",
          r"\bgratis\b", r"\bgratuit", r"risultati assicurati", r"senza dolore"]

class ApiError(Exception):
    pass

# ---------- calendario ----------
def load():
    return json.loads(CAL.read_text())

def save(cal):
    CAL.write_text(json.dumps(cal, ensure_ascii=False, indent=2) + "\n")

def tzinfo(cal):
    return ZoneInfo(cal.get("timezone", "Europe/Rome"))

def now_local(cal, override=None):
    z = tzinfo(cal)
    o = override or os.environ.get("IG_NOW")
    if o:
        d = datetime.fromisoformat(o)
        return d if d.tzinfo else d.replace(tzinfo=z)
    return datetime.now(z)

def when(post, cal):
    d = datetime.fromisoformat(post["publish_at"])
    return d if d.tzinfo else d.replace(tzinfo=tzinfo(cal))

def is_due(post, cal, now):
    if post.get("status") != "approved":
        return False
    delta = now - when(post, cal)
    return timedelta(0) <= delta <= timedelta(hours=cal.get("max_delay_hours", 36))

def caption_text(post, cal):
    tags = post.get("hashtags", cal.get("default_hashtags", []))
    tags = " ".join(t if t.startswith("#") else "#" + t for t in tags)
    return post["caption"].strip() + (("\n\n" + tags) if tags else "")

def media_files(post):
    d = HERE / "media" / post["id"]
    imgs = sorted(d.glob("[0-9][0-9].jpg"))
    return d, imgs

# ---------- controlli ----------
def lint(post, cal, all_ids=None):
    err, warn = [], []
    pid = post.get("id", "?")
    if post.get("type") not in TYPES:
        err.append(f"tipo non valido: {post.get('type')}")
    if not post.get("caption", "").strip():
        err.append("didascalia vuota")
    full = caption_text(post, cal) if post.get("caption") else ""
    if len(full) > 2200:
        err.append(f"didascalia troppo lunga ({len(full)} > 2200)")
    n_tags = len(re.findall(r"#\w+", full))
    if n_tags > 30:
        err.append("più di 30 hashtag")
    elif n_tags > 8:
        warn.append(f"{n_tags} hashtag: meglio 3-5")
    texts = [full] + [str(v) for s in post.get("slides", []) for v in s.values() if isinstance(v, (str, list))]
    flat = " ".join(" ".join(t) if isinstance(t, list) else t for t in texts)
    for pat in BANNED:
        m = re.search(pat, flat, re.I)
        if m:
            err.append(f"espressione da evitare nella comunicazione sanitaria: «{m.group(0)}»")
    if post.get("requires_disclaimer", True) and "non sostituisce" not in full.lower():
        err.append("manca la frase «non sostituisce una visita» nella didascalia")
    for k, s in enumerate(post.get("slides", []), 1):
        if s.get("persona") == "paziente" and not s.get("consenso"):
            err.append(f"slide {k}: foto di un paziente senza consenso scritto (consenso: true)")
    if post.get("status") == "approved" and not post.get("approved_by"):
        err.append("approvato ma senza «approved_by»")
    try:
        when(post, cal)
    except Exception:
        err.append("publish_at non valido")
    t = post.get("type")
    d, imgs = media_files(post)
    if t in ("image", "story"):
        if len(imgs) != 1:
            err.append(f"servono 1 immagine in media/{pid}/ (trovate {len(imgs)}): esegui render.py")
    elif t == "carousel":
        if not 2 <= len(imgs) <= 10:
            err.append(f"il carosello vuole 2-10 immagini (trovate {len(imgs)}): esegui render.py")
        elif len(imgs) != len(post.get("slides", [])):
            err.append("immagini non allineate alle slide: esegui render.py")
    elif t == "reel":
        if not (d / "video.mp4").exists():
            err.append(f"manca media/{pid}/video.mp4: servono il video e render.py")
    if all_ids is not None and all_ids.count(pid) > 1:
        err.append("id duplicato")
    return err, warn

# ---------- API ----------
class IG:
    def __init__(self, uid, token, base=None, ver=None):
        self.uid, self.token = uid, token
        self.base = (base or os.environ.get("IG_API_BASE") or "https://graph.instagram.com").rstrip("/")
        self.ver = ver or os.environ.get("IG_API_VERSION") or "v23.0"

    def _req(self, method, path, params, retries=3):
        url = f"{self.base}/{self.ver}/{path}"
        data = None
        p = dict(params, access_token=self.token)
        if method == "GET":
            url += "?" + urllib.parse.urlencode(p)
        else:
            data = urllib.parse.urlencode(p).encode()
        last = None
        for k in range(retries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method), timeout=60) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as ex:
                body = ex.read().decode("utf-8", "replace")
                try:
                    msg = json.loads(body).get("error", {}).get("message", body)
                except Exception:
                    msg = body
                last = ApiError(f"HTTP {ex.code} su {path}: {msg}")
                if ex.code < 500 or path.endswith("media_publish"):
                    raise last
            except urllib.error.URLError as ex:
                last = ApiError(f"rete su {path}: {ex.reason}")
                if path.endswith("media_publish"):
                    raise last
            time.sleep(2 * (k + 1) if not os.environ.get("IG_FAST") else 0)
        raise last

    def post(self, path, **params):
        return self._req("POST", path, params)

    def get(self, path, **params):
        return self._req("GET", path, params)

    def wait(self, container, timeout):
        interval = float(os.environ.get("IG_POLL_INTERVAL", "10"))
        end = time.time() + timeout
        while True:
            s = self.get(container, fields="status_code,status")
            code = s.get("status_code")
            if code in ("FINISHED", "PUBLISHED"):
                return
            if code in ("ERROR", "EXPIRED"):
                raise ApiError(f"contenitore {container} in stato {code}: {s.get('status', '')}")
            if time.time() > end:
                raise ApiError(f"contenitore {container} ancora in elaborazione dopo {timeout}s")
            time.sleep(interval)

def media_base():
    b = os.environ.get("MEDIA_BASE_URL")
    if b:
        return b.rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise ApiError("manca MEDIA_BASE_URL (o GITHUB_REPOSITORY)")
    return f"https://raw.githubusercontent.com/{repo}/{os.environ.get('GITHUB_REF_NAME', 'main')}/instagram/media"

def media_url(post, name):
    f = HERE / "media" / post["id"] / name
    v = hashlib.sha1(f.read_bytes()).hexdigest()[:8]
    return f"{media_base()}/{post['id']}/{name}?v={v}"

def wait_public(url, kind):
    """Instagram scarica il file da un URL pubblico: lo verifichiamo prima di creare i contenitori."""
    wait = float(os.environ.get("IG_URL_WAIT", "300"))
    step = float(os.environ.get("IG_URL_STEP", "15"))
    end = time.time() + wait
    while True:
        try:
            req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                ct = r.headers.get("Content-Type", "")
                if r.status in (200, 206) and (ct.startswith(kind + "/") or ct == "application/octet-stream"):
                    return
                reason = f"{r.status} {ct}"
        except Exception as ex:
            reason = str(ex)
        if time.time() > end:
            raise ApiError(f"file non raggiungibile pubblicamente: {url.split('?')[0]} ({reason})")
        time.sleep(step)

def publish_post(post, cal, ig):
    t, cap = post["type"], caption_text(post, cal)
    d, imgs = media_files(post)
    alts = post.get("alt", [])
    def alt(k):
        return {"alt_text": alts[k]} if k < len(alts) and alts[k] else {}
    if t == "image":
        u = media_url(post, imgs[0].name); wait_public(u, "image")
        c = ig.post(f"{ig.uid}/media", image_url=u, caption=cap, **alt(0))["id"]; ig.wait(c, 180)
    elif t == "story":
        u = media_url(post, imgs[0].name); wait_public(u, "image")
        c = ig.post(f"{ig.uid}/media", image_url=u, media_type="STORIES")["id"]; ig.wait(c, 180)
    elif t == "carousel":
        kids = []
        for k, f in enumerate(imgs):
            u = media_url(post, f.name); wait_public(u, "image")
            kids.append(ig.post(f"{ig.uid}/media", image_url=u, is_carousel_item="true", **alt(k))["id"])
        for k in kids:
            ig.wait(k, 180)
        c = ig.post(f"{ig.uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]; ig.wait(c, 180)
    else:
        u = media_url(post, "video.mp4"); wait_public(u, "video")
        extra = {}
        if (d / "cover.jpg").exists():
            cu = media_url(post, "cover.jpg"); wait_public(cu, "image"); extra["cover_url"] = cu
        c = ig.post(f"{ig.uid}/media", media_type="REELS", video_url=u, caption=cap, share_to_feed="true", **extra)["id"]
        ig.wait(c, 900)
    mid = ig.post(f"{ig.uid}/media_publish", creation_id=c)["id"]
    link = ""
    try:
        link = ig.get(mid, fields="permalink").get("permalink", "")
    except ApiError:
        pass
    return mid, link

# ---------- comandi ----------
def cmd_due(a):
    cal = load(); n = now_local(cal, a.now)
    ids = [p["id"] for p in cal["posts"] if is_due(p, cal, n)]
    for p in cal["posts"]:
        if p.get("status") == "approved" and (n - when(p, cal)) > timedelta(hours=cal.get("max_delay_hours", 36)):
            print(f"::warning::{p['id']} è approvato ma la data è passata da troppo: non verrà pubblicato")
    print("da pubblicare:", ", ".join(ids) or "-")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"ids={','.join(ids)}\n")

def cmd_lint(a):
    cal = load(); ids = [p.get("id") for p in cal["posts"]]; bad = 0
    for p in cal["posts"]:
        if p.get("status") == "published":
            continue
        e, w = lint(p, cal, ids)
        mark = "OK " if not e else "!! "
        print(f"{mark}{p['id']} [{p.get('status')}]")
        for x in e: print("     errore:", x)
        for x in w: print("     avviso:", x)
        if e and p.get("status") == "approved":
            bad += 1
    sys.exit(1 if bad else 0)

def cmd_status(a):
    cal = load()
    for p in sorted(cal["posts"], key=lambda p: p["publish_at"]):
        print(f"{p['publish_at'][:16]}  {p['status']:<10} {p['type']:<8} {p['id']}  {p.get('permalink', '')}")

def cmd_publish(a):
    cal = load(); n = now_local(cal, a.now); ids = [p["id"] for p in cal["posts"]]
    todo = [p for p in cal["posts"] if (p["id"] == a.id if a.id else is_due(p, cal, n))]
    if a.id and todo and todo[0].get("status") not in ("approved",) and not a.dry_run:
        sys.exit(f"{a.id} non è approvato (stato: {todo[0].get('status')})")
    if not todo:
        print("niente da pubblicare"); return
    uid, tok = os.environ.get("IG_USER_ID"), os.environ.get("IG_TOKEN")
    if not a.dry_run and not (uid and tok):
        sys.exit("mancano IG_USER_ID e IG_TOKEN")
    ig = IG(uid, tok); failed = 0
    for p in todo[:3]:
        e, w = lint(p, cal, ids)
        if e:
            print(f"✗ {p['id']}: " + "; ".join(e)); p["last_error"] = "; ".join(e); failed += 1; continue
        if a.dry_run:
            print(f"(prova) {p['id']}: {p['type']}, {len(media_files(p)[1])} immagini\n---\n{caption_text(p, cal)}\n---"); continue
        try:
            mid, link = publish_post(p, cal, ig)
            p.update(status="published", published_at=now_local(cal).isoformat(timespec="seconds"),
                     ig_media_id=mid, permalink=link); p.pop("last_error", None)
            print(f"✓ {p['id']} pubblicato {link}")
        except ApiError as ex:
            p["attempts"] = p.get("attempts", 0) + 1; p["last_error"] = str(ex)
            if p["attempts"] >= 4:
                p["status"] = "failed"
            print(f"✗ {p['id']}: {ex}"); failed += 1
        save(cal)
    if not a.dry_run:
        save(cal)
    sys.exit(1 if failed else 0)

def cmd_refresh(a):
    tok = os.environ.get("IG_TOKEN")
    if not tok:
        sys.exit("manca IG_TOKEN")
    base = (os.environ.get("IG_API_BASE") or "https://graph.instagram.com").rstrip("/")
    url = f"{base}/refresh_access_token?" + urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": tok})
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as ex:
        sys.exit(f"rinnovo non riuscito: HTTP {ex.code} {ex.read().decode('utf-8', 'replace')[:300]}")
    days = int(res.get("expires_in", 0)) // 86400
    print(f"token rinnovato: scade tra {days} giorni")
    new = res.get("access_token")
    if new and new != tok:
        pat, repo = os.environ.get("GH_PAT"), os.environ.get("GITHUB_REPOSITORY")
        if pat and repo:
            subprocess.run(["gh", "secret", "set", "IG_TOKEN", "--repo", repo, "--body", new],
                           env=dict(os.environ, GH_TOKEN=pat), check=True)
            print("segreto IG_TOKEN aggiornato")
        else:
            print("::error::il token è cambiato ma manca GH_PAT per aggiornare il segreto: rigeneralo a mano")
            sys.exit(1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["due", "lint", "publish", "status", "refresh"])
    ap.add_argument("--id"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--now")
    a = ap.parse_args()
    {"due": cmd_due, "lint": cmd_lint, "publish": cmd_publish, "status": cmd_status, "refresh": cmd_refresh}[a.cmd](a)

if __name__ == "__main__":
    main()
