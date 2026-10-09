#!/usr/bin/env python3
"""HidenCloud watchdog probe (read-only).
Reads HIDEN_COOKIE env, checks login + per-service renewal state, writes public/status.json.
Never prints secrets. Exits 0 always (health is expressed in status.json, not exit code)."""
import json, os, re, sys, datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("need requests + beautifulsoup4", file=sys.stderr)
    sys.exit(2)

BASE = "https://dash.hidencloud.com"
OUT = os.environ.get("STATUS_OUT", "public/status.json")

status = {
    "checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "login_ok": False,
    "services": [],
    "healthy": False,
    "reasons": [],
}


def parse_cookie(s):
    jar = {}
    for part in (s or "").replace("\n", ";").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        jar[k.strip()] = v.strip()
    return jar


def main():
    raw = os.environ.get("HIDEN_COOKIE", "")
    # multi-account format: first entry only (watchdog watches account 1)
    first = re.split(r"[&\n]", raw)[0] if raw else ""
    jar = parse_cookie(first)
    if not jar:
        status["reasons"].append("HIDEN_COOKIE secret missing or empty")
        return write()

    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"})
    for k, v in jar.items():
        s.cookies.set(k, v, domain=".dash.hidencloud.com")
    try:
        r = s.get(BASE + "/dashboard", timeout=40, allow_redirects=True)
    except Exception as e:
        status["reasons"].append(f"dashboard unreachable: {type(e).__name__}")
        return write()
    if "/login" in r.url:
        status["reasons"].append("cookie expired (redirected to /login)")
        return write()
    soup = BeautifulSoup(r.text, "html.parser")
    title = (soup.title.string or "") if soup.title else ""
    if any(t in title.lower() for t in ("just a moment", "attention required", "security verification")):
        status["reasons"].append(f"bot challenge at login (title: {title[:60]})")
        return write()

    status["login_ok"] = True
    seen = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/service/" in href and "/manage" in href:
            sid = href.split("/service/")[1].split("/")[0]
            if sid not in seen:
                seen.append(sid)
    if not seen:
        status["reasons"].append("login ok but no services listed")
        return write()

    for sid in seen:
        info = {"id": sid, "days_left": None, "renewable": False, "flags": []}
        try:
            mr = s.get(f"{BASE}/service/{sid}/manage", timeout=40)
            page = mr.text
            m = re.search(r"showRenewAlert\((\d+),\s*(\d+),\s*(true|false)\)", page)
            if m:
                info["days_left"] = int(m.group(1))
                info["renewable"] = True
            low = page.lower()
            for kw in ("suspend", "terminat", "delet", "expir", "overdue", "unpaid"):
                if kw in low:
                    info["flags"].append(kw)
        except Exception as e:
            info["flags"].append(f"fetch-error:{type(e).__name__}")
        status["services"].append(info)
        if info["days_left"] is not None and info["days_left"] <= 1:
            status["reasons"].append(f"service {sid}: only {info['days_left']}d left")
        if any(f in ("suspend", "terminat", "delet") for f in info["flags"]):
            status["reasons"].append(f"service {sid}: danger flags {info['flags']}")

    if not status["reasons"]:
        status["healthy"] = True
    return write()


def write():
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(status, f, indent=2)
    print(json.dumps(status, indent=2))


main()
