# sysglance

[![CI](https://github.com/ItsMrZxD/sysglance/actions/workflows/ci.yml/badge.svg)](https://github.com/ItsMrZxD/sysglance/actions/workflows/ci.yml)

A tiny, zero-dependency CLI that prints a clean snapshot of your system — CPU,
memory, disk, network, battery, temperature, OS, and uptime. Pure Python
standard library, so it runs anywhere Python 3.8+ does, with no `pip install`
required.

## Usage

```bash
python3 sysglance.py            # pretty, colored table
python3 sysglance.py --no-color # plain text (good for piping to a file)
python3 sysglance.py --json     # machine-readable JSON
python3 sysglance.py --version
```

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

Piping to a tool? Use `--json`:

```bash
python3 sysglance.py --json | jq .cpu.model
```

## How it works

No third-party libraries — just the standard library reading how the system
exposes its own state. Collection is separated from presentation, so the same
structured data drives both the table and the JSON output.

| Metric        | Linux                     | macOS                  | Windows                  |
|---------------|---------------------------|------------------------|--------------------------|
| CPU model     | `/proc/cpuinfo`           | `sysctl`               | `PROCESSOR_IDENTIFIER`   |
| Memory        | `/proc/meminfo`           | —                      | `GlobalMemoryStatusEx`   |
| Uptime        | `/proc/uptime`            | `sysctl kern.boottime` | `GetTickCount64`         |
| Battery       | `/sys/class/power_supply` | `pmset`                | `GetSystemPowerStatus`   |
| CPU temp      | `/sys/class/thermal`      | —                      | —                        |
| Disk / OS / IP| `shutil`, `platform`, `socket` (all platforms)              |||

Any metric that isn't available on your platform degrades gracefully: it shows
`n/a` in the table (or `null` in JSON) instead of crashing.

> Tested on Linux. The macOS and Windows code paths use documented system APIs
> and fall back safely, but haven't been run on those platforms yet — bug
> reports welcome.

## Tests

```bash
python -m unittest discover
```

## Ideas for next

- `--watch` mode that refreshes on an interval
- per-interface IP addresses
- a `--fields` flag to pick exactly which rows to show

## License

MIT — see [LICENSE](LICENSE).
