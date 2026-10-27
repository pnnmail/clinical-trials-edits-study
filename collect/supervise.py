"""Watchdog for the version download: starts collect/versions.py and restarts it if the process crashed
or no new files appeared in raw/ for 10 minutes. Exits when "done" appears in the collector's log."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "versions.log"
STALL_SEC = 600


def newest_mtime():
    m = 0.0
    for d in (ROOT / "raw").glob("NCT*"):
        m = max(m, d.stat().st_mtime)
    return m


def done():
    if not LOG.exists():
        return False
    lines = LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    return bool(lines) and "done" in lines[-1]


def kill_browsers():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'chrome-headless-shell*' } | "
                    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                   capture_output=True)


def main():
    with open(ROOT / "logs" / "supervise.log", "a", encoding="utf-8") as out:
        while not done():
            p = subprocess.Popen([sys.executable, "collect/versions.py"], cwd=ROOT,
                                 stdout=subprocess.DEVNULL, stderr=open(ROOT / "logs" / "versions.err", "a"))
            out.write(f"{time.ctime()} start pid {p.pid}\n"); out.flush()
            last_change = time.time()
            seen = newest_mtime()
            while p.poll() is None:
                time.sleep(60)
                m = newest_mtime()
                if m > seen:
                    seen, last_change = m, time.time()
                elif time.time() - last_change > STALL_SEC:
                    out.write(f"{time.ctime()} no new files for {STALL_SEC} s — restarting\n"); out.flush()
                    p.kill()
                    break
            kill_browsers()
            if done():
                break
            time.sleep(30)
        out.write(f"{time.ctime()} download finished\n")


if __name__ == "__main__":
    main()
