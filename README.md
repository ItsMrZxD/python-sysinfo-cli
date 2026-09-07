# Python Sysinfo CLI

[![CI](https://github.com/ItsMrZxD/python-sysinfo-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ItsMrZxD/python-sysinfo-cli/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**A zero-dependency Python CLI that prints a clean snapshot of your system —
CPU, memory, disk, network, battery, temperature, OS, and uptime — as a
readable table or as JSON. Pure standard library, single file, cross-platform.**

`sysglance.py` is one file with no `pip install` step, so it runs anywhere
Python 3.8+ does. Drop it on a server, run it, and get the system information
you actually want at a glance. The `--json` mode makes it a convenient source
of machine-readable system info for scripts, dashboards, and monitoring
one-liners.

Works on **Linux, macOS, and Windows**, reading each platform's native
interfaces rather than shelling out to third-party tools.

## Features

- **One-screen system summary** — user, hostname, OS, architecture, Python
  version, CPU model and core count, memory, disk, uptime, IP address, network
  interfaces, battery, and CPU temperature
- **Zero dependencies** — Python standard library only, nothing to install
- **Three output modes** — coloured table, plain text for piping, and JSON
- **Cross-platform**, using native interfaces per OS (see the table below)
- **Degrades gracefully** — anything unavailable on your platform is omitted
  or reported as `null` rather than crashing
- Single file — copy `sysglance.py` anywhere and run it

## Requirements

Python 3.8 or newer. Nothing else.

CI runs the test suite on Linux, macOS, and Windows, and against Python 3.9
and 3.14.

## Installation

No install step. Clone, or just download the single file:

```bash
git clone https://github.com/ItsMrZxD/python-sysinfo-cli
cd python-sysinfo-cli
python3 sysglance.py
```

## Usage

```bash
python3 sysglance.py            # pretty, coloured table
python3 sysglance.py --no-color # plain text (good for piping to a file)
python3 sysglance.py --json     # machine-readable JSON
python3 sysglance.py --version
```

### Command-line options

| Flag | Description |
|------|-------------|
| `--json` | output as JSON instead of the table |
| `--no-color` | disable coloured output |
| `--version` | print the version and exit |
| `-h`, `--help` | show usage and exit |

## Example output

```
sysglance
---------
User      mrz@laptop
OS        Linux 6.18.5
Arch      x86_64
Python    3.11.15
CPU       Intel(R) Xeon(R) Processor @ 2.80GHz
Cores     4
Memory    5.2 GB / 15.7 GB (33%)
Disk (~)  7.0 GB / 252.0 GB (3%)
Uptime    2d 4h 31m
IP        192.168.1.42
Ifaces    lo, eth0
Battery   87% (Discharging)
CPU Temp  44.0 C
```

### JSON output

Piping to a tool? Use `--json`:

```bash
python3 sysglance.py --json | jq .cpu.model
```

The JSON object has these top-level keys:

```
user, hostname, os, arch, python, cpu, memory,
disk, uptime_seconds, network, battery, temperature_c
```

Metrics that are unavailable on the current platform are `null`, so consumers
can check for them explicitly. The full interface list lives in `network` even
when the table truncates it.

## How it works

No third-party libraries — just the standard library reading how each system
exposes its own state. Collection is separated from presentation, so the same
structured data drives both the table and the JSON output.

| Metric | Linux | macOS | Windows |
|---------------|---------------------------|------------------------|--------------------------|
| CPU model | `/proc/cpuinfo` | `sysctl` | `PROCESSOR_IDENTIFIER` |
| Memory | `/proc/meminfo` | — | `GlobalMemoryStatusEx` |
| Uptime | `/proc/uptime` | `sysctl kern.boottime` | `GetTickCount64` |
| Battery | `/sys/class/power_supply` | `pmset` | `GetSystemPowerStatus` |
| CPU temp | `/sys/class/thermal` | — | — |
| Disk / OS / IP | `shutil`, `platform`, `socket` (all platforms) |||

The Windows values come from calling the Win32 API directly through `ctypes`
rather than shelling out to `wmic` or PowerShell, which keeps it fast and
dependency-free. One subtlety worth noting: the fields in `SYSTEM_POWER_STATUS`
are declared as unsigned bytes, because a signed type would wrap the API's
`255` "no battery" sentinel to `-1` and misreport a desktop as having a
battery.

On Linux, CPU temperature is the highest reading across all
`/sys/class/thermal/thermal_zone*` entries.

## Tests

```bash
python -m unittest discover
```

CI runs the suite on `ubuntu-latest`, `windows-latest`, and `macos-latest`.

## Limitations

- **Rows are omitted when unavailable.** Battery, CPU temperature, IP, and
  network interfaces are dropped from the table entirely if the platform does
  not report them; memory shows `n/a`. In `--json` output they are `null`.
- **CPU temperature is Linux-only.** macOS and Windows both require privileged
  or vendor-specific interfaces to read it.
- **Memory is not reported on macOS** — there is no `/proc/meminfo` and no
  `ctypes` path implemented for it.
- **Colour is disabled on Windows.** Output is plain text there regardless of
  terminal capability.
- **Disk usage is for the home directory's filesystem only** (`~`), not every
  mounted volume.
- The table truncates the interface list to the first six, with a `+N more`
  marker. `--json` always carries the full list.
- This is a point-in-time snapshot, not a monitor — there is no sampling
  interval, so CPU *utilisation* is not reported, only the model and core count.

## Ideas for next

- `--watch` mode that refreshes on an interval
- per-interface IP addresses
- a `--fields` flag to pick exactly which rows to show

## License

MIT — see [LICENSE](LICENSE).
