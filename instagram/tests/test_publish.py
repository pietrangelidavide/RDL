"""Prove del flusso di pubblicazione contro un finto server Graph API (nessuna chiamata reale a Meta).
Esecuzione: python3 -m unittest discover -s instagram/tests -v"""
import warnings; warnings.simplefilter("ignore", ResourceWarning)
import copy, http.server, json, os, pathlib, shutil, subprocess, sys, tempfile, threading, unittest, urllib.parse
from datetime import datetime

SRC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))
import publish as P  # noqa: E402

TOKEN = "TESTTOKEN"

class Mock(http.server.BaseHTTPRequestHandler):
    state = {}
    def log_message(self, *a): pass
    def _json(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query); S = self.state
        if u.path.startswith("/media/"):
            f = S["media"] / u.path[len("/media/"):]
            if not f.exists(): return self._json(404, {})
            data = f.read_bytes(); ct = "video/mp4" if f.suffix == ".mp4" else "image/jpeg"
            self.send_response(206); self.send_header("Content-Type", ct); self.send_header("Content-Length", "1"); self.end_headers(); self.wfile.write(data[:1]); return
        if q.get("access_token", [""])[0] != TOKEN:
            return self._json(400, {"error": {"message": "Invalid OAuth access token."}})
        cid = u.path.rsplit("/", 1)[-1]
        if q.get("fields", [""])[0].startswith("status_code"):
            S["polls"][cid] = S["polls"].get(cid, 0) + 1
            if cid in S["error_ids"]: return self._json(200, {"status_code": "ERROR", "status": "Media upload has failed"})
            need = S["slow"].get(cid, 0)
            return self._json(200, {"status_code": "FINISHED" if S["polls"][cid] > need else "IN_PROGRESS"})
        if q.get("fields", [""])[0] == "permalink":
            return self._json(200, {"permalink": f"https://www.instagram.com/p/{cid}/"})
        self._json(404, {})
    def do_POST(self):
        S = self.state; n = int(self.headers.get("Content-Length", 0))
        f = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode()).items()}
        if f.get("access_token") != TOKEN:
            return self._json(400, {"error": {"message": "Invalid OAuth access token."}})
        if self.path.endswith("/media_publish"):
            if f["creation_id"] in S["published"]: return self._json(400, {"error": {"message": "già pubblicato"}})
            S["published"].append(f["creation_id"]); S["calls"].append(("publish", f)); return self._json(200, {"id": "m" + str(len(S["published"]))})
        if self.path.endswith("/media"):
            cid = "c" + str(len(S["calls"]) + 1); S["calls"].append(("create", f, cid)); S["containers"][cid] = f
            if f.get("media_type") == "REELS": S["slow"][cid] = 2
            if f.get("media_type") == "CAROUSEL":
                assert all(k in S["containers"] for k in f["children"].split(",")), "figli inesistenti"
            if S.get("fail_create_error"): S["error_ids"].add(cid)
            return self._json(200, {"id": cid})
        self._json(404, {})

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(SRC / "media", self.tmp / "media")
        self.cal = json.loads((SRC / "calendar.json").read_text())
        P.HERE, P.CAL = self.tmp, self.tmp / "calendar.json"
        Mock.state = {"media": self.tmp / "media", "calls": [], "containers": {}, "published": [], "polls": {}, "slow": {}, "error_ids": set()}
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Mock)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{self.srv.server_port}"
        os.environ.update(IG_API_BASE=base, MEDIA_BASE_URL=base + "/media", IG_USER_ID="123", IG_TOKEN=TOKEN,
                          IG_FAST="1", IG_POLL_INTERVAL="0.01", IG_URL_STEP="0.01", IG_URL_WAIT="0.3")
        self.S = Mock.state
    def tearDown(self):
        self.srv.shutdown(); shutil.rmtree(self.tmp)
    def approve(self, pid, at="2026-11-04T18:30"):
        for p in self.cal["posts"]:
            if p["id"] == pid: p.update(status="approved", approved_by="Riccardo Di Lazzaro", publish_at=at)
        P.CAL.write_text(json.dumps(self.cal))
    def run_pub(self, now, **kw):
        a = type("A", (), {**dict(id=None, dry_run=False, now=now), **kw})
        try: P.cmd_publish(a)
        except SystemExit as e: return e.code
        return 0
    def post(self, pid):
        return next(p for p in json.loads(P.CAL.read_text())["posts"] if p["id"] == pid)

class Due(Base):
    def test_solo_approvati_e_in_orario(self):
        pid = "2026-11-04-mal-di-schiena"; self.approve(pid)
        cal = json.loads(P.CAL.read_text()); p = self.post(pid)
        ok = lambda s: P.is_due(p, cal, P.now_local(cal, s))
        self.assertFalse(ok("2026-11-04T18:29")); self.assertTrue(ok("2026-11-04T18:30")); self.assertTrue(ok("2026-11-05T20:00"))
        self.assertFalse(ok("2026-11-06T07:00"))  # oltre 36 ore: non si pubblica un contenuto «vecchio»
        p["status"] = "draft"; self.assertFalse(ok("2026-11-04T19:00"))

class Lint(Base):
    def test_bozze_pulite(self):
        ids = [p["id"] for p in self.cal["posts"]]
        for p in self.cal["posts"]:
            if p["type"] == "reel": continue
            e, _ = P.lint(p, self.cal, ids); self.assertEqual(e, [], p["id"])
    def test_regole_di_sicurezza(self):
        p = copy.deepcopy(next(x for x in self.cal["posts"] if x["id"] == "2026-11-04-mal-di-schiena"))
        p["caption"] = "Guarigione garantita con lo sconto di novembre"
        e, _ = P.lint(p, self.cal); t = " ".join(e)
        self.assertIn("garantit", t.lower()); self.assertIn("sconto", t.lower()); self.assertIn("non sostituisce", t)
        p["status"] = "approved"; e, _ = P.lint(p, self.cal); self.assertTrue(any("approved_by" in x for x in e))
        p = copy.deepcopy(self.cal["posts"][0]); p["slides"][0]["persona"] = "paziente"
        e, _ = P.lint(p, self.cal); self.assertTrue(any("consenso" in x for x in e))
    def test_reel_senza_video(self):
        p = next(x for x in self.cal["posts"] if x["type"] == "reel"); e, _ = P.lint(p, self.cal)
        self.assertTrue(any("video.mp4" in x for x in e))

class Flusso(Base):
    def test_immagine_singola(self):
        pid = "2026-11-02-presentazione"; self.approve(pid, "2026-11-02T18:30")
        self.assertEqual(self.run_pub("2026-11-02T18:31"), 0)
        p = self.post(pid); self.assertEqual(p["status"], "published"); self.assertTrue(p["permalink"].startswith("https://www.instagram.com/p/"))
        c = [x for x in self.S["calls"] if x[0] == "create"]; self.assertEqual(len(c), 1)
        f = c[0][1]; self.assertIn("image_url", f); self.assertIn("#fisioterapia", f["caption"]); self.assertIn("Riccardo", f["alt_text"])
        self.assertEqual(len(self.S["published"]), 1)
    def test_carosello_ordine_e_figli(self):
        pid = "2026-11-04-mal-di-schiena"; self.approve(pid)
        self.assertEqual(self.run_pub("2026-11-04T19:00"), 0)
        c = [x for x in self.S["calls"] if x[0] == "create"]; kids = [x for x in c if x[1].get("is_carousel_item")]
        self.assertEqual(len(kids), 6); parent = c[-1][1]
        self.assertEqual(parent["media_type"], "CAROUSEL"); self.assertEqual(parent["children"].split(","), [k[2] for k in kids])
        self.assertEqual([k[1]["image_url"].split("?")[0].rsplit("/", 1)[-1] for k in kids], [f"0{i}.jpg" for i in range(1, 7)])
    def test_reel_con_attesa_elaborazione(self):
        pid = "2026-11-11-gatto-cammello"; (self.tmp / "media" / pid).mkdir()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:d=1", "-pix_fmt", "yuv420p", str(self.tmp / "media" / pid / "video.mp4")], check=True)
        self.approve(pid, "2026-11-11T18:30"); self.assertEqual(self.run_pub("2026-11-11T18:31"), 0)
        f = [x for x in self.S["calls"] if x[0] == "create"][0][1]
        self.assertEqual(f["media_type"], "REELS"); self.assertIn("video_url", f); self.assertGreaterEqual(max(self.S["polls"].values()), 3)
    def test_nessun_doppione(self):
        pid = "2026-11-06-percorsi-su-misura"; self.approve(pid, "2026-11-06T18:30")
        self.run_pub("2026-11-06T18:31"); n = len(self.S["calls"])
        self.run_pub("2026-11-06T19:01"); self.assertEqual(len(self.S["calls"]), n)
    def test_errore_non_segna_pubblicato(self):
        pid = "2026-11-06-percorsi-su-misura"; self.approve(pid, "2026-11-06T18:30"); self.S["fail_create_error"] = True
        for k in range(4): self.assertEqual(self.run_pub(f"2026-11-06T1{9 + 0}:0{k}"), 1)
        p = self.post(pid); self.assertEqual(p["attempts"], 4); self.assertEqual(p["status"], "failed"); self.assertEqual(self.S["published"], [])
    def test_token_sbagliato(self):
        pid = "2026-11-06-percorsi-su-misura"; self.approve(pid, "2026-11-06T18:30"); os.environ["IG_TOKEN"] = "SBAGLIATO"
        self.assertEqual(self.run_pub("2026-11-06T18:31"), 1); self.assertEqual(self.post(pid)["status"], "approved")
        self.assertIn("Invalid OAuth", self.post(pid)["last_error"]); os.environ["IG_TOKEN"] = TOKEN
    def test_prova_a_secco(self):
        pid = "2026-11-06-percorsi-su-misura"; self.approve(pid, "2026-11-06T18:30")
        self.assertEqual(self.run_pub("2026-11-06T18:31", dry_run=True), 0); self.assertEqual(self.S["calls"], [])

if __name__ == "__main__":
    unittest.main()
