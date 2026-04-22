"""
System Health Monitor
=====================
Tracks CPU, RAM, and Battery usage in real time.
Alerts when levels are too high.

Run with:  python monitor.py
"""

import psutil
import time
import os
import platform
from datetime import datetime

# ─── Alert Thresholds ────────────────────────────────────────────────────────
CPU_ALERT    = 80   # %
RAM_ALERT    = 80   # %
BATTERY_LOW  = 20   # %  (alert when battery is low AND not charging)

# ─── History for sparkline (last N readings) ─────────────────────────────────
HISTORY_LEN = 20
cpu_history = []
ram_history = []

# ─── ANSI colour helpers ──────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

def colour(text, r, g, b):
    return f"\033[38;2;{r};{g};{b}m{text}{RESET}"

def bg(text, r, g, b):
    return f"\033[48;2;{r};{g};{b}m{text}{RESET}"

def clear():
    os.system("cls" if platform.system() == "Windows" else "clear")

# ─── Bar renderer ─────────────────────────────────────────────────────────────
def bar(value, width=30):
    """Return a coloured progress bar string."""
    filled = int(value / 100 * width)
    empty  = width - filled

    if value >= 80:
        r, g, b = 255, 80, 80      # red
    elif value >= 60:
        r, g, b = 255, 180, 50    # amber
    else:
        r, g, b = 80, 220, 140    # green

    bar_str = colour("█" * filled, r, g, b) + DIM + "░" * empty + RESET
    return f"[{bar_str}]"

# ─── Sparkline renderer ───────────────────────────────────────────────────────
SPARK_CHARS = " ▁▂▃▄▅▆▇█"

def sparkline(history):
    if not history:
        return ""
    mx = max(history) if max(history) > 0 else 1
    chars = ""
    for v in history:
        idx = int(v / mx * (len(SPARK_CHARS) - 1))
        chars += SPARK_CHARS[idx]
    return colour(chars, 120, 180, 255)

# ─── Data collectors ──────────────────────────────────────────────────────────
def get_cpu():
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    overall  = psutil.cpu_percent(interval=0.5)
    freq     = psutil.cpu_freq()
    freq_str = f"{freq.current:.0f} MHz" if freq else "N/A"
    return overall, per_core, freq_str

def get_ram():
    mem = psutil.virtual_memory()
    used_gb  = mem.used  / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)
    return mem.percent, used_gb, total_gb

def get_battery():
    batt = psutil.sensors_battery()
    if batt is None:
        return None, None, None
    plugged = batt.power_plugged
    secs    = batt.secsleft
    if secs == psutil.POWER_TIME_UNLIMITED or secs < 0:
        time_left = "Charging" if plugged else "Calculating…"
    else:
        h, m = divmod(secs // 60, 60)
        time_left = f"{h}h {m:02d}m remaining"
    return batt.percent, plugged, time_left

def get_top_processes(n=5):
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)
    return procs[:n]

# ─── Alert system ─────────────────────────────────────────────────────────────
alerts = []

def check_alerts(cpu, ram, batt_pct, batt_plugged):
    global alerts
    alerts = []
    if cpu >= CPU_ALERT:
        alerts.append(("🔥 CPU ALERT",   f"CPU at {cpu:.1f}% — consider closing heavy apps"))
    if ram >= RAM_ALERT:
        alerts.append(("💾 RAM ALERT",   f"RAM at {ram:.1f}% — memory running low"))
    if batt_pct is not None and batt_pct <= BATTERY_LOW and not batt_plugged:
        alerts.append(("🔋 BATTERY LOW", f"Battery at {batt_pct:.0f}% — please plug in"))

# ─── Dashboard renderer ───────────────────────────────────────────────────────
TITLE = r"""
  ███████╗██╗   ██╗███████╗    ██╗  ██╗███████╗ █████╗ ██╗  ████████╗██╗  ██╗
  ██╔════╝╚██╗ ██╔╝██╔════╝    ██║  ██║██╔════╝██╔══██╗██║  ╚══██╔══╝██║  ██║
  ███████╗ ╚████╔╝ ███████╗    ███████║█████╗  ███████║██║     ██║   ███████║
  ╚════██║  ╚██╔╝  ╚════██║    ██╔══██║██╔══╝  ██╔══██║██║     ██║   ██╔══██║
  ███████║   ██║   ███████║    ██║  ██║███████╗██║  ██║███████╗██║   ██║  ██║
  ╚══════╝   ╚═╝   ╚══════╝    ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝  ╚═╝
"""

def divider(label="", width=72):
    if label:
        pad = (width - len(label) - 2) // 2
        return colour("─" * pad + f" {label} " + "─" * pad, 60, 80, 120)
    return colour("─" * width, 40, 60, 100)

def render(cpu, per_core, freq_str, ram, used_gb, total_gb,
           batt_pct, batt_plugged, batt_time, top_procs):

    clear()
    now = datetime.now().strftime("%A, %d %b %Y  %H:%M:%S")

    # Title
    print(colour(TITLE, 80, 160, 255))
    print(colour(f"  System Health Monitor  •  {now}  •  Press Ctrl+C to quit", 100, 140, 200))
    print()

    # ── CPU ──────────────────────────────────────────────────────────────────
    print(divider("CPU"))
    status = colour("⚠  HIGH", 255, 80, 80) if cpu >= CPU_ALERT else colour("✔  OK", 80, 220, 140)
    print(f"  {BOLD}Overall  {RESET}{bar(cpu)} {colour(f'{cpu:5.1f}%', 255,255,255)}  {status}  {DIM}{freq_str}{RESET}")
    print(f"  {DIM}Trend: {sparkline(cpu_history)}{RESET}")
    print()

    # Per-core bars (up to 8 cores shown)
    shown_cores = per_core[:8]
    core_strs   = [f"  Core{i} {bar(v, 12)} {colour(f'{v:4.0f}%', 180,180,220)}"
                   for i, v in enumerate(shown_cores)]
    # Print in 2 columns
    mid = (len(core_strs) + 1) // 2
    for i in range(mid):
        left  = core_strs[i]
        right = core_strs[i + mid] if (i + mid) < len(core_strs) else ""
        print(f"{left}   {right}")
    print()

    # ── RAM ──────────────────────────────────────────────────────────────────
    print(divider("MEMORY (RAM)"))
    status = colour("⚠  HIGH", 255, 80, 80) if ram >= RAM_ALERT else colour("✔  OK", 80, 220, 140)
    print(f"  {BOLD}RAM      {RESET}{bar(ram)} {colour(f'{ram:5.1f}%', 255,255,255)}  {status}")
    print(f"  {DIM}Used: {used_gb:.2f} GB / {total_gb:.2f} GB   Trend: {sparkline(ram_history)}{RESET}")
    print()

    # ── Battery ───────────────────────────────────────────────────────────────
    print(divider("BATTERY"))
    if batt_pct is None:
        print(f"  {DIM}No battery detected (desktop PC){RESET}")
    else:
        plug_icon = colour("⚡ Plugged in", 255, 220, 60) if batt_plugged else colour("🔋 On battery", 180, 180, 255)
        if batt_pct <= BATTERY_LOW and not batt_plugged:
            status = colour("⚠  LOW!", 255, 80, 80)
        elif batt_plugged:
            status = colour("✔  Charging", 80, 220, 140)
        else:
            status = colour("✔  OK", 80, 220, 140)
        print(f"  {BOLD}Battery  {RESET}{bar(batt_pct)} {colour(f'{batt_pct:5.1f}%', 255,255,255)}  {status}")
        print(f"  {DIM}{plug_icon}  {batt_time}{RESET}")
    print()

    # ── Top Processes ─────────────────────────────────────────────────────────
    print(divider("TOP PROCESSES BY CPU"))
    print(f"  {DIM}{'PID':>6}  {'NAME':<25}  {'CPU%':>6}  {'MEM%':>6}{RESET}")
    for p in top_procs:
        name = (p['name'] or 'unknown')[:24]
        cpu_col = colour(f"{p['cpu_percent']:6.1f}", 255, 140, 80) if (p['cpu_percent'] or 0) > 20 else f"{p['cpu_percent'] or 0:6.1f}"
        mem_col = f"{p['memory_percent'] or 0:6.1f}"
        print(f"  {p['pid']:>6}  {name:<25}  {cpu_col}  {mem_col}")
    print()

    # ── Alerts ────────────────────────────────────────────────────────────────
    if alerts:
        print(divider("⚠  ALERTS"))
        for title, msg in alerts:
            print(f"  {colour(BOLD + title + RESET, 255, 80, 80)}  {colour(msg, 255, 180, 180)}")
        print()
    else:
        print(divider())
        print(f"  {colour('✔  All systems normal — no alerts', 80, 220, 140)}")
        print()

    print(colour("  Refreshing every 2 seconds  •  Ctrl+C to exit", 60, 80, 120))

# ─── Main loop ────────────────────────────────────────────────────────────────
def main():
    print("Starting System Health Monitor…  (first read may take a moment)")
    # Warm up psutil's CPU counter (first call always returns 0)
    psutil.cpu_percent(interval=1, percpu=True)
    psutil.cpu_percent(interval=None)

    try:
        while True:
            cpu, per_core, freq_str    = get_cpu()
            ram, used_gb, total_gb     = get_ram()
            batt_pct, batt_plugged, batt_time = get_battery()
            top_procs                  = get_top_processes()

            # Update history
            cpu_history.append(cpu)
            ram_history.append(ram)
            if len(cpu_history) > HISTORY_LEN: cpu_history.pop(0)
            if len(ram_history) > HISTORY_LEN: ram_history.pop(0)

            check_alerts(cpu, ram, batt_pct, batt_plugged)
            render(cpu, per_core, freq_str, ram, used_gb, total_gb,
                   batt_pct, batt_plugged, batt_time, top_procs)

            time.sleep(2)

    except KeyboardInterrupt:
        clear()
        print(colour("\n  System Health Monitor stopped. Goodbye!\n", 80, 220, 140))

if __name__ == "__main__":
    main()