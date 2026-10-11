#!/usr/bin/env python3
"""Observe the isolated Genshin copy; never log in or use the production prefix.

Run with sophon_server/.venv/bin/python (psutil is an existing Sophon dependency).
Runtime/prefix preparation and result boundaries are in docs/arm64-validation.md.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import psutil


def processes(runtime):
    result = []
    for proc in psutil.process_iter(["pid", "exe", "memory_info", "cmdline"]):
        info = proc.info
        if info["exe"] and info["exe"].startswith(str(runtime) + "/") and info["memory_info"]:
            result.append({"pid": proc.pid, "rss_mb": round(info["memory_info"].rss / 1048576, 1),
                           "image": (info["cmdline"] or [""])[0]})
    return result


def interrupted(signum, frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", choices=["hadron", "macneutron"])
    parser.add_argument("--seconds", type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300:
        parser.error("--seconds must be between 1 and 300")
    root = Path(__file__).resolve().parent / ".arm64-build"
    game = root / "game-cn"
    prefix = root / ("prefix-" + args.runtime)
    if args.runtime == "hadron":
        owner = root / "runtime/hadron-v0.2.0/dist"
        resources = owner
        wine = owner / "bin/wine"
    else:
        owner = root / "runtime/macneutron-v0.4.0/MacNeutron.app/Contents/Helpers/wine.app"
        resources = owner / "Contents/Resources"
        wine = owner / "Contents/MacOS/wine"
    server = resources / "bin/wineserver"
    for file in [wine, server, prefix / "system.reg", prefix / "drive_c/windows/system32/steam.exe", game / "YuanShen.exe"]:
        if not file.is_file():
            parser.error("Prepare the isolated experiment first; missing " + str(file))
    if processes(owner):
        parser.error("This experiment's Wine is already running; stop it before another probe")

    env = {"HOME": os.environ["HOME"], "USER": os.environ["USER"], "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
           "LANG": "en_US.UTF-8", "TMPDIR": "/tmp", "WINEPREFIX": str(prefix),
           "WINEDEBUG": "fixme-all,err-unwind,+timestamp,+loaddll",
           "WINEDLLOVERRIDES": "mscoree,mshtml=;lsteamclient=n", "FEX_DISKCACHE": "0",
           "HADRON_DISABLE_LSTEAMCLIENT": "1", "WINE_ENABLE_TIMEOUT_FIX": "1", "WINEESYNC": "1",
           "DXMT_CONFIG": "d3d11.preferredMaxFrameRate=30;", "DXMT_LOG_PATH": str(root / "logs"),
           "MTL_HUD_ENABLED": "0"}
    if args.runtime == "hadron":
        env["DYLD_FALLBACK_LIBRARY_PATH"] = f"{resources}/ext/lib:{resources}/mesa-zink/lib"
        # A conditional guest loop otherwise misses cooperative suspend checks.
        # Keep this bounded probe on the verified diagnostic configuration.
        env["FEX_MULTIBLOCK"] = "0"
        env["FEX_MAXINST"] = "1"
    else:
        env["WINEMSYNC"] = "1"
        env["WINEDLLOVERRIDES"] += ";dxgi,d3d10core,d3d11,d3d12=n,b;d3d9,d3d10=b"
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    stem = "genshin-" + args.runtime + "-probe"
    report = {"runtime": str(owner), "prefix": str(prefix), "seconds_limit": args.seconds, "samples": []}
    signal.signal(signal.SIGTERM, interrupted)
    start = time.monotonic()
    swap_base = psutil.swap_memory().used
    reason = "monitor error"
    code = 1
    with (logs / (stem + ".log")).open("w") as output:
        process = None
        try:
            # Same Unity preference keys as YAAGL's custom resolution flow.
            # Keep a hung fullscreen game from covering the user's desktop.
            registry = logs / "probe-windowed.reg"
            registry.write_text('Windows Registry Editor Version 5.00\n\n'
                                '[HKEY_CURRENT_USER\\Software\\miHoYo\\原神]\n'
                                '"Screenmanager Is Fullscreen mode_h3981298716"=dword:00000000\n'
                                '"Screenmanager Resolution Width_h182942802"=dword:00000500\n'
                                '"Screenmanager Resolution Height_h2627697771"=dword:000002d0\n\n'
                                '[HKEY_CURRENT_USER\\Software\\Wine\\Mac Driver]\n'
                                '"WindowsFloatWhenInactive"="none"\n'
                                '"CaptureDisplaysForFullscreen"="N"\n', encoding="utf-16")
            subprocess.run([str(wine), "reg.exe", "import", "Z:" + str(registry).replace("/", "\\")],
                           env=env, stdout=output, stderr=subprocess.STDOUT, timeout=15, check=True)
            process = subprocess.Popen(["/usr/bin/nice", "-n", "10", str(wine),
                                        r"C:\windows\system32\steam.exe", "Z:" + str(game / "YuanShen.exe").replace("/", "\\"),
                                        "-popupwindow"],
                                       cwd=game, env=env, stdout=output, stderr=subprocess.STDOUT)
            while time.monotonic() - start < args.seconds:
                entries = processes(owner)
                rss = sum(p["rss_mb"] for p in entries)
                pressure = int(subprocess.check_output(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True))
                swap = psutil.swap_memory().used
                swap_base = min(swap_base, swap)
                row = {"seconds": round(time.monotonic() - start, 1), "rss_mb": round(rss, 1),
                       "pressure": pressure, "swap_growth_mb": round((swap - swap_base) / 1048576, 1), "processes": entries}
                report["samples"].append(row)
                print(json.dumps(row), flush=True)
                if rss > 6144 or pressure >= 4 or swap - swap_base > 1073741824:
                    reason = "memory guard"
                    break
                if process.poll() is not None:
                    reason = "experiment launcher exited"
                    code = process.returncode or 1
                    break
                time.sleep(2)
            else:
                reason = "observation time limit (UI success is not asserted)"
                code = 0
        except KeyboardInterrupt:
            reason, code = "interrupted", 130
        finally:
            report["stop_reason"] = reason
            report["helper_exit_before_cleanup"] = process.poll() if process else None
            cleanup_errors = []
            # Only the server of this fixed experimental prefix is stopped.
            for action in ["-k", "-w"]:
                try:
                    subprocess.run([str(server), action], env=env, timeout=10, check=False)
                except (subprocess.TimeoutExpired, OSError) as error:
                    cleanup_errors.append(str(error))
            if process:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            # Admission requires this private runtime to be idle. A hung server
            # must not leave its experimental clients spinning after the probe.
            remaining = []
            for entry in processes(owner):
                try:
                    client = psutil.Process(entry["pid"])
                    if client.exe().startswith(str(owner) + "/"):
                        client.kill()
                        remaining.append(client)
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(remaining, timeout=5)
            report["cleanup_errors"] = cleanup_errors
            report["remaining_processes"] = processes(owner)
            if cleanup_errors or report["remaining_processes"]:
                code = 1
            report["duration_seconds"] = round(time.monotonic() - start, 1)
            (logs / (stem + "-metrics.json")).write_text(json.dumps(report, indent=2) + "\n")
    print(reason, flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
