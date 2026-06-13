#!/usr/bin/env python3
"""
TimeMachine — DeepSeek implementation harness.

Fans out one DeepSeek agent per module (in parallel threads), each implementing a single file
against the locked contract in SPEC.md. This is the "speedrun" build step: every JS/CSS module is
written concurrently, then validated by a separate Claude validation swarm.

Setup:
  1. Put your key in a gitignored .env at the repo root (copy .env.example), or set the env var:
         DEEPSEEK_API_KEY=sk-...
     Optional: DEEPSEEK_MODEL (default "deepseek-chat"), DEEPSEEK_BASE_URL (default
     "https://api.deepseek.com").
  2. Test the key:        python tools/deepseek_agent.py --ping
  3. Build everything:    python tools/deepseek_agent.py --tasks tools/tasks.deepseek.json
     Build a subset:      python tools/deepseek_agent.py --tasks tools/tasks.deepseek.json --only util,map
     Dry run (no write):  add --dry

No third-party dependencies (urllib only).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO / "SPEC.md"

SYSTEM_BASE = (
    "You are a senior front-end engineer implementing the TimeMachine wildlife tracker. "
    "You write production-quality, dependency-free code that runs by double-clicking index.html "
    "(file://). You follow the contract in the SPEC EXACTLY: never invent globals, rename DOM ids, "
    "change the data shape, or add a build step / ES modules / fetch / frameworks. Match the dark "
    "theme and the exact method signatures. Output ONLY the complete contents of the requested "
    "file — no prose, no explanation, and no Markdown code fences.\n\n"
    "===== SPEC.md (the contract) =====\n{spec}\n===== end SPEC ====="
)


def load_env() -> None:
    """Merge a repo-root .env into os.environ without overwriting real env vars."""
    env = REPO / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v:                       # .env is authoritative (overrides a stale shell var)
            os.environ[k] = v


def cfg() -> dict:
    load_env()
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        sys.exit("DEEPSEEK_API_KEY is not set. Add it to .env (see .env.example) or export it.")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    return {
        "key": key,
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip(),
        "url": base + "/chat/completions",
        "temperature": float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.15")),
    }


def call(c: dict, system: str, user: str, max_tokens: int = 8192, retries: int = 2) -> str:
    body = json.dumps({
        "model": c["model"],
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": c["temperature"],
        "max_tokens": max_tokens,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(c["url"], data=body, method="POST", headers={
        "Authorization": f"Bearer {c['key']}",
        "Content-Type": "application/json",
    })
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last = f"HTTP {e.code}: {detail}"
            if e.code in (429, 500, 502, 503, 529) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            break
        except Exception as e:  # noqa: BLE001
            last = repr(e)
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            break
    raise RuntimeError(last or "unknown error")


def extract_code(text: str) -> str:
    """Strip Markdown fences if the model wrapped the file in them."""
    blocks = re.findall(r"```[a-zA-Z0-9]*\n(.*?)```", text, re.S)
    if blocks:
        return max(blocks, key=len).strip() + "\n"
    return text.strip() + "\n"


def run_task(c: dict, spec: str, task: dict, dry: bool) -> dict:
    path = task["path"]
    user = (f"{task['brief']}\n\nWrite the COMPLETE final contents of `{path}`. "
            f"Output ONLY the file contents (no fences, no commentary).")
    t0 = time.time()
    try:
        code = extract_code(call(c, SYSTEM_BASE.format(spec=spec), user))
        if not dry:
            out = REPO / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(code, encoding="utf-8")
        return {"id": task["id"], "path": path, "ok": True,
                "bytes": len(code.encode("utf-8")), "secs": round(time.time() - t0, 1)}
    except Exception as e:  # noqa: BLE001
        return {"id": task["id"], "path": path, "ok": False,
                "error": str(e)[:300], "secs": round(time.time() - t0, 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", help="path to tasks JSON (list of {id,path,brief})")
    ap.add_argument("--only", help="comma-separated task ids to run")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry", action="store_true", help="generate but do not write files")
    ap.add_argument("--ping", action="store_true", help="test the key/model with one tiny call")
    args = ap.parse_args()
    c = cfg()

    if args.ping:
        try:
            out = call(c, "You are a health check.", "Reply with exactly: PONG", max_tokens=16)
            print(f"OK — model={c['model']} replied: {out.strip()!r}")
        except Exception as e:  # noqa: BLE001
            sys.exit(f"PING FAILED — model={c['model']}: {e}")
        return

    if not args.tasks:
        sys.exit("Provide --tasks <file> (or --ping).")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    if args.only:
        want = {x.strip() for x in args.only.split(",")}
        tasks = [t for t in tasks if t["id"] in want]
    if not tasks:
        sys.exit("No matching tasks.")

    print(f"DeepSeek build · model={c['model']} · {len(tasks)} module(s) · {args.workers} parallel"
          + (" · DRY RUN" if args.dry else ""))
    results = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_task, c, spec, t, args.dry): t for t in tasks}
        for f in cf.as_completed(futs):
            r = f.result()
            results.append(r)
            mark = "OK " if r["ok"] else "ERR"
            extra = f"{r['bytes']:>6}B" if r["ok"] else r.get("error", "")
            print(f"  [{mark}] {r['id']:<9} {r['path']:<22} {r['secs']:>5}s  {extra}")

    ok = sum(1 for r in results if r["ok"])
    print(f"\n{ok}/{len(results)} modules generated."
          + ("" if ok == len(results) else "  Re-run failures with --only <ids>."))
    if ok != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
