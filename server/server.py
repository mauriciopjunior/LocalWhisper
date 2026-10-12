#!/usr/bin/env python3
"""Servidor local (somente stdlib) que roda transcribe.py (openai-whisper) para o painel UXP.
Uso: python3 server.py   (porta 17321, somente localhost)"""
import json, os, re, shutil, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 17321
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "transcribe.py")
EXTRA_PATH = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/opt/local/bin"]
ENV = dict(os.environ, PATH=":".join(EXTRA_PATH) + ":" + os.environ.get("PATH", ""), PYTHONUNBUFFERED="1")

FFMPEG = shutil.which("ffmpeg", path=ENV["PATH"])
PYTHON = sys.executable  # o mesmo python que está rodando o servidor (precisa ter whisper)
try:
    import whisper  # noqa: F401
    HAS_WHISPER = True
except Exception:
    HAS_WHISPER = False

jobs = {}
counter = 0
lock = threading.Lock()


def run_job(job, o):
    clips = o["clips"]
    first = os.path.abspath(clips[0]["path"])
    out_dir = os.path.dirname(first)
    out_name = os.path.splitext(os.path.basename(first))[0] + ("_legendas" if len(clips) > 1 else "")
    args = [PYTHON, "-u", SCRIPT,
            "--clips", json.dumps(clips),
            "--out-dir", out_dir, "--out-name", out_name,
            "--model", o.get("model") or "turbo",
            "--language", o.get("language") or "Portuguese",
            "--max-words", str(o.get("maxWords") or 7),
            "--break-at", str(o.get("breakAt") or 4)]
    job["status"] = "loading"
    cur, total = 0, len(clips)
    try:
        p = subprocess.Popen(args, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            chunk = p.stdout.read1(256) if hasattr(p.stdout, "read1") else p.stdout.read(256)
            if not chunk:
                break
            s = chunk.decode("utf-8", "replace")
            job["log"] = (job["log"] + s)[-4000:]
            mc = re.findall(r"@@CLIP (\d+) (\d+)", s)
            if mc:
                cur, total = int(mc[-1][0]), int(mc[-1][1])
                job["clip"], job["clips"] = cur + 1, total
            m = re.findall(r"(\d+)%\|", s)
            if m:
                job["status"] = "transcribing"
                job["progress"] = int((cur * 100 + int(m[-1])) / max(total, 1))
        code = p.wait()
    except Exception as e:
        job.update(status="error", error="python: %s" % e)
        return
    if code != 0:
        tail = " ".join([l for l in job["log"].splitlines() if l.strip()][-2:])
        job.update(status="error", error="whisper falhou (código %s): %s" % (code, tail))
        return
    srt = os.path.join(out_dir, out_name + ".srt")
    if not os.path.exists(srt):
        job.update(status="error", error="SRT não foi gerado")
        return
    job.update(srtPath=srt, progress=100, status="done")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send(204, {})

    def do_GET(self):
        global jobs
        if self.path == "/health":
            return self.send(200, {"ok": True, "ffmpeg": FFMPEG, "python": PYTHON if HAS_WHISPER else None})
        if self.path.startswith("/job/"):
            j = jobs.get(self.path[5:])
            return self.send(200, j) if j else self.send(404, {"error": "job não encontrado"})
        self.send(404, {"error": "rota inválida"})

    def do_POST(self):
        global counter
        if self.path != "/transcribe":
            return self.send(404, {"error": "rota inválida"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            o = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self.send(400, {"error": "JSON inválido"})
        if not FFMPEG:
            return self.send(500, {"error": "ffmpeg não encontrado (rode setup.sh)"})
        if not HAS_WHISPER:
            return self.send(500, {"error": "openai-whisper não instalado neste python (rode setup.sh)"})
        clips = o.get("clips")
        if not clips or not isinstance(clips, list):
            return self.send(400, {"error": "Nenhum clipe enviado"})
        for c in clips:
            if not c.get("path") or not os.path.exists(c["path"]):
                return self.send(400, {"error": "Arquivo não existe: %s" % c.get("path")})
        if o.get("model") and not re.match(r"^[\w.-]+$", o["model"]):
            return self.send(400, {"error": "Modelo inválido"})
        with lock:
            counter += 1
            jid = str(counter)
        job = {"id": jid, "status": "queued", "progress": 0, "log": ""}
        jobs[jid] = job
        threading.Thread(target=run_job, args=(job, o), daemon=True).start()
        self.send(200, {"id": jid})


if __name__ == "__main__":
    print("Whisper server em http://127.0.0.1:%d\nffmpeg: %s\npython: %s (whisper: %s)" % (PORT, FFMPEG, PYTHON, HAS_WHISPER), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
