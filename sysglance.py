#!/usr/bin/env python3
"""sysglance - a tiny, zero-dependency snapshot of your system.

Prints CPU, memory, disk, network, battery, temperature, OS, and uptime
using only the Python standard library. Works on Linux, macOS, and Windows,
with graceful fallbacks when a particular metric isn't available.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import sys
import time

__version__ = "0.2.0"

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def supports_color() -> bool:
    """True if stdout is an interactive terminal that likely supports ANSI."""
    return sys.stdout.isatty() and os.name != "nt"


def paint(text: str, color: str, enable: bool) -> str:
    return f"{color}{text}{RESET}" if enable else text


def human_bytes(n: float) -> str:
    """Format a byte count as a short human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024.0:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} EB"


def fmt_uptime(secs: float | None) -> str:
    if secs is None:
        return "n/a"
    secs = int(secs)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Metric collection (each function degrades gracefully to None)
# --------------------------------------------------------------------------- #
def cpu_model() -> str:
    """Best-effort CPU model name across platforms."""
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    system = platform.system()
    if system == "Darwin":
        try:
            import subprocess

            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            )
            return out.strip()
        except Exception:
            pass
    elif system == "Windows":
        ident = os.environ.get("PROCESSOR_IDENTIFIER")
        if ident:
            return ident
    return platform.processor() or "Unknown CPU"


def mem_info() -> tuple[int | None, int | None]:
    """Return (total_bytes, available_bytes), or (None, None) if unknown."""
    try:
        fields = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                key, _, val = line.partition(":")
                fields[key.strip()] = val.strip()
        total = int(fields["MemTotal"].split()[0]) * 1024
        avail = int(fields.get("MemAvailable", fields["MemFree"]).split()[0]) * 1024
        return total, avail
    except (OSError, KeyError, ValueError, IndexError):
        pass

    if platform.system() == "Windows":
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys), int(status.ullAvailPhys)
        except Exception:
            pass
    return None, None


def uptime_seconds() -> float | None:
    """Seconds since boot, or None if it can't be determined."""
    try:
        with open("/proc/uptime") as fh:
            return float(fh.read().split()[0])
    except (OSError, ValueError, IndexError):
        pass

    system = platform.system()
    if system == "Darwin":
        try:
            import subprocess

            out = subprocess.check_output(["sysctl", "-n", "kern.boottime"], text=True)
            boot = int(out.split("sec =")[1].split(",")[0])
            return max(0.0, time.time() - boot)
        except Exception:
            pass
    elif system == "Windows":
        try:
            import ctypes

            return ctypes.windll.kernel32.GetTickCount64() / 1000.0
        except Exception:
            pass
    return None


def network_info() -> dict:
    """Primary outbound IP and the list of interface names, where available."""
    info: dict = {"primary_ip": None, "interfaces": []}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0.2)
        # No packets are sent for a UDP "connect"; it just selects the route
        # the kernel would use, which reveals the primary local address.
        sock.connect(("8.8.8.8", 80))
        info["primary_ip"] = sock.getsockname()[0]
    except OSError:
        pass
    finally:
        sock.close()

    try:
        info["interfaces"] = [name for _, name in socket.if_nameindex()]
    except (OSError, AttributeError):
        pass
    return info


def battery_info() -> dict | None:
    """Battery percentage and status, or None if there's no battery."""
    base = "/sys/class/power_supply"
    try:
        for entry in sorted(os.listdir(base)):
            if entry.startswith("BAT"):
                with open(os.path.join(base, entry, "capacity")) as fh:
                    percent = int(fh.read().strip())
                status = "Unknown"
                try:
                    with open(os.path.join(base, entry, "status")) as fh:
                        status = fh.read().strip()
                except OSError:
                    pass
                return {"percent": percent, "status": status}
    except OSError:
        pass

    system = platform.system()
    if system == "Windows":
        try:
            import ctypes

            class SystemPowerStatus(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]

            status = SystemPowerStatus()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                percent = status.BatteryLifePercent
                if percent == 255:  # unknown / no battery
                    return None
                charging = status.ACLineStatus == 1
                return {"percent": int(percent), "status": "Charging" if charging else "Discharging"}
        except Exception:
            pass
    elif system == "Darwin":
        try:
            import re
            import subprocess

            out = subprocess.check_output(["pmset", "-g", "batt"], text=True)
            match = re.search(r"(\d+)%", out)
            if match:
                charging = "discharging" not in out.lower() and "charging" in out.lower()
                return {"percent": int(match.group(1)), "status": "Charging" if charging else "Discharging"}
        except Exception:
            pass
    return None


def cpu_temp() -> float | None:
    """Highest CPU/thermal-zone temperature in Celsius (Linux), else None."""
    base = "/sys/class/thermal"
    try:
        temps = []
        for entry in os.listdir(base):
            if entry.startswith("thermal_zone"):
                try:
                    with open(os.path.join(base, entry, "temp")) as fh:
                        temps.append(int(fh.read().strip()) / 1000.0)
                except (OSError, ValueError):
                    pass
        if temps:
            return round(max(temps), 1)
    except OSError:
        pass
    return None


def collect() -> dict:
    """Gather all system information into a structured, JSON-ready dict."""
    total, avail = mem_info()
    disk = shutil.disk_usage(os.path.expanduser("~"))
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    return {
        "user": user,
        "hostname": socket.gethostname(),
        "os": {"system": platform.system(), "release": platform.release()},
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu": {"model": cpu_model(), "cores": os.cpu_count()},
        "memory": (
            {"total": total, "used": total - avail, "available": avail}
            if total and avail is not None
            else None
        ),
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "uptime_seconds": uptime_seconds(),
        "network": network_info(),
        "battery": battery_info(),
        "temperature_c": cpu_temp(),
    }


# --------------------------------------------------------------------------- #
# Presentation
# --------------------------------------------------------------------------- #
def human_rows(data: dict) -> list[tuple[str, str]]:
    """Turn the structured data into ordered (label, value) display rows."""
    rows = [
        ("User", f"{data['user']}@{data['hostname']}"),
        ("OS", f"{data['os']['system']} {data['os']['release']}".strip()),
        ("Arch", data["arch"]),
        ("Python", data["python"]),
        ("CPU", data["cpu"]["model"]),
        ("Cores", str(data["cpu"]["cores"] or "?")),
    ]

    mem = data["memory"]
    if mem:
        pct = mem["used"] / mem["total"] * 100
        rows.append(("Memory", f"{human_bytes(mem['used'])} / {human_bytes(mem['total'])} ({pct:.0f}%)"))
    else:
        rows.append(("Memory", "n/a"))

    disk = data["disk"]
    dpct = disk["used"] / disk["total"] * 100
    rows.append(("Disk (~)", f"{human_bytes(disk['used'])} / {human_bytes(disk['total'])} ({dpct:.0f}%)"))
    rows.append(("Uptime", fmt_uptime(data["uptime_seconds"])))

    net = data["network"]
    if net.get("primary_ip"):
        rows.append(("IP", net["primary_ip"]))
    if net.get("interfaces"):
        rows.append(("Ifaces", ", ".join(net["interfaces"])))

    bat = data["battery"]
    if bat:
        rows.append(("Battery", f"{bat['percent']}% ({bat['status']})"))

    temp = data["temperature_c"]
    if temp is not None:
        rows.append(("CPU Temp", f"{temp:.1f} C"))

    return rows


def render(rows: list[tuple[str, str]], color: bool) -> None:
    title = "sysglance"
    rule = "-" * len(title)
    if color:
        print(f"{BOLD}{CYAN}{title}{RESET}")
        print(f"{DIM}{rule}{RESET}")
    else:
        print(title)
        print(rule)
    width = max(len(key) for key, _ in rows)
    for key, value in rows:
        print(f"{paint(f'{key:<{width}}', GREEN, color)}  {value}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A tiny snapshot of your system.")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    parser.add_argument("--no-color", action="store_true", help="disable colored output")
    parser.add_argument("--version", action="version", version=f"sysglance {__version__}")
    args = parser.parse_args(argv)

    data = collect()
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        render(human_rows(data), supports_color() and not args.no_color)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
