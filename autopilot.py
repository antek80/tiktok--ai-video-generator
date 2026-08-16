#!/usr/bin/env python3
"""
Autopilot Continuous Daemon for TikTok AI Video Generator & Auto-Poster.
Runs 24/7 on any OS (macOS, Linux, Windows) and publishes scheduled videos automatically.
"""

import sys
import time
import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from daily_poster import run_daily_job, POSTED_HISTORY_FILE
import json

console = Console()

DEFAULT_SCHEDULE_HOURS = ["08:30", "10:00", "11:30", "13:00", "14:30", "16:00", "17:30", "19:00", "20:30", "22:00"]


def get_next_run_time(schedule_times: list[str]) -> tuple[datetime, str]:
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    candidates = []
    for t_str in schedule_times:
        hour, minute = map(int, t_str.split(":"))
        dt_today = datetime(now.year, now.month, now.day, hour, minute, 0)
        if dt_today > now:
            candidates.append((dt_today, t_str))
            
    if candidates:
        return min(candidates, key=lambda x: x[0])
        
    # Otherwise next run is first slot tomorrow
    tomorrow = now + timedelta(days=1)
    first_slot = min(schedule_times)
    h, m = map(int, first_slot.split(":"))
    dt_tomorrow = datetime(tomorrow.year, tomorrow.month, tomorrow.day, h, m, 0)
    return dt_tomorrow, first_slot


def print_dashboard(next_run: datetime, slot_name: str, schedule: list[str]):
    console.clear()
    
    history_count = 0
    if POSTED_HISTORY_FILE.exists():
        try:
            with open(POSTED_HISTORY_FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
                history_count = len(hist.get("posted_topics", []))
        except Exception:
            pass

    table = Table(title="🤖 TikTok AI Autopilot - Status Panel", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="yellow")
    
    table.add_row("Current Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("Total Published Videos", str(history_count))
    table.add_row("Daily Schedule Slots", f"{len(schedule)} slots ({', '.join(schedule)})")
    table.add_row("Next Scheduled Run", f"{next_run.strftime('%Y-%m-%d %H:%M:%S')} (Slot: {slot_name})")
    
    time_left = max(0, int((next_run - datetime.now()).total_seconds()))
    mins, secs = divmod(time_left, 60)
    hours, mins = divmod(mins, 60)
    table.add_row("Time Until Next Post", f"{hours:02d}h {mins:02d}m {secs:02d}s")
    
    console.print(table)
    console.print("[dim]Press Ctrl+C to stop autopilot anytime.[/dim]\n")


async def main_loop(schedule: list[str], interval_mins: int | None = None, run_immediately: bool = False):
    console.print(Panel.fit("[bold green]🚀 TikTok Autopilot Agent Activated![/bold green]\nMonitoring scheduled slots and publishing autonomously.", border_style="green"))
    
    if run_immediately:
        console.print("[bold yellow]⚡ Running immediate publication slot...[/bold yellow]")
        try:
            await run_daily_job()
        except Exception as e:
            console.print(f"[bold red]Error in immediate run:[/bold red] {e}")

    while True:
        now = datetime.now()
        if interval_mins:
            next_run = now + timedelta(minutes=interval_mins)
            slot_name = f"+{interval_mins}m"
        else:
            next_run, slot_name = get_next_run_time(schedule)
            
        while datetime.now() < next_run:
            print_dashboard(next_run, slot_name, schedule)
            await asyncio.sleep(10)
            
        console.print(f"\n[bold green]⏰ Reached publication time for slot {slot_name}! Executing pipeline...[/bold green]")
        try:
            await run_daily_job()
            console.print("[bold green]✅ Post completed successfully![/bold green]")
        except Exception as e:
            console.print(f"[bold red]❌ Error during automated publication:[/bold red] {e}")
            
        await asyncio.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok AI Video Generator Autopilot Daemon")
    parser.add_argument("--now", action="store_true", help="Run 1 publication immediately upon start")
    parser.add_argument("--interval", type=int, default=None, help="Interval in minutes between posts (overrides fixed schedule)")
    parser.add_argument("--slots", nargs="+", default=DEFAULT_SCHEDULE_HOURS, help="Specific daily post times (e.g. --slots 09:00 13:00 18:00 21:00)")
    args = parser.parse_args()

    try:
        asyncio.run(main_loop(schedule=args.slots, interval_mins=args.interval, run_immediately=args.now))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Autopilot stopped by user.[/bold yellow]")
