import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import settings, OUTPUT_DIR
from core.pipeline import Pipeline
from agent.session_manager import SessionManager
from agent.tiktok_uploader import TikTokUploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tiktok-generator")

app = typer.Typer(help="🎬 TikTok AI Video Generator & Autonomous Publisher with Anti-Shadowban")
console = Console()

@app.command()
def generate(
    topic: str = typer.Option(..., "--topic", "-t", help="Video topic / hook concept (e.g. 'The Dyatlov Pass Mystery')"),
    lang: str = typer.Option("en", "--lang", "-l", help="Voiceover language: 'en' (default) or 'pl'"),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Edge-TTS voice (e.g. en-US-ChristopherNeural)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="Gemini API Key (optional)")
):
    """
    Generates high-retention vertical 9:16 video with Anti-Shadowban filters, dynamic subtitles, and audio.
    """
    console.print(Panel.fit(f"[bold cyan]🎬 Generating TikTok Video for Topic:[/bold cyan] [yellow]{topic}[/yellow]"))
    
    pipeline = Pipeline(gemini_api_key=api_key or settings.gemini_api_key, voice=voice)
    result = pipeline.generate_video(topic=topic, language=lang, voice=voice)
    
    table = Table(title="✅ Video Generated Successfully!", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=18)
    table.add_column("Value")
    
    table.add_row("Video Path", str(result.video_path))
    table.add_row("Duration", f"{result.duration:.2f} s")
    table.add_row("Hook (3s)", result.script.hook)
    table.add_row("Caption", result.caption)
    table.add_row("Hashtags", " ".join(result.hashtags))
    
    console.print(table)
    console.print(f"\n[green]To publish to TikTok, run:[/green] [bold]python cli.py upload --video {result.video_path}[/bold]")

@app.command()
def login():
    """
    Opens Google Chrome to log into TikTok and save persistent session cookies.
    """
    console.print("[bold yellow]Launching official Google Chrome for login...[/bold yellow]")
    sm = SessionManager()
    asyncio.run(sm.login_interactively())

@app.command()
def status():
    """
    Checks if active TikTok session is valid and authenticated.
    """
    console.print("[bold cyan]Checking TikTok session authentication status...[/bold cyan]")
    sm = SessionManager()
    is_logged = asyncio.run(sm.is_logged_in())
    if is_logged:
        console.print("[bold green]✅ Session is active and authenticated! Ready to publish.[/bold green]")
    else:
        console.print("[bold red]❌ No active session found. Run `python cli.py login` to authenticate.[/bold red]")

@app.command("open")
def open_tiktok():
    """
    Opens Google Chrome with the exact bot session to view Creator Center.
    """
    console.print("[bold cyan]Opening TikTok Creator Center with bot session in Google Chrome...[/bold cyan]")
    subprocess.Popen([
        "open", "-na", "Google Chrome",
        "--args", f"--user-data-dir={settings.tiktok_session_dir}",
        "https://www.tiktok.com/creator-center/content"
    ])

@app.command()
def upload(
    video: Path = typer.Option(..., "--video", "-v", help="Path to .mp4 video file"),
    caption: Optional[str] = typer.Option(None, "--caption", "-c", help="Video caption"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Space-separated hashtags (e.g. '#fyp #viral')"),
    publish: bool = typer.Option(True, "--publish/--draft", help="Publish immediately or save as draft"),
    declare_ai: bool = typer.Option(False, "--declare-ai/--no-declare-ai", help="Tag with AI-generated content label")
):
    """
    Publishes a video to TikTok autonomously using stealth browser automation.
    """
    console.print(Panel.fit(f"[bold blue]🚀 Autonomous Upload to TikTok:[/bold blue] {video.name}"))
    
    hashtags_list = tags.split() if tags else ["#fyp", "#viral", "#foryou", "#facts"]
    cap = caption or f"Mind-blowing facts! Wait for the end 🔥"
    
    uploader = TikTokUploader(headless=False)
    success = asyncio.run(uploader.upload_video(
        video_path=video,
        caption=cap,
        hashtags=hashtags_list,
        publish_now=publish,
        declare_ai=declare_ai
    ))
    
    if success:
        console.print("[bold green]🎉 Video successfully uploaded and posted on TikTok![/bold green]")
    else:
        console.print("[bold red]❌ Error occurred during video upload.[/bold red]")

@app.command()
def auto(
    topic: str = typer.Option(..., "--topic", "-t", help="Video topic in English"),
    lang: str = typer.Option("en", "--lang", "-l", help="Voiceover language: 'en' or 'pl'"),
    publish: bool = typer.Option(True, "--publish/--draft", help="Publish automatically after rendering"),
    declare_ai: bool = typer.Option(False, "--declare-ai/--no-declare-ai", help="Tag with AI-generated content label")
):
    """
    Full Autonomous Flow: Generates video from scratch and posts it to TikTok immediately.
    """
    console.print(Panel.fit(f"[bold magenta]⚡ AUTO-PIPELINE: Generation + TikTok Post for:[/bold magenta] [yellow]{topic}[/yellow]"))
    
    pipeline = Pipeline()
    result = pipeline.generate_video(topic=topic, language=lang)
    console.print(f"✅ Rendered: [green]{result.video_path}[/green]")
    
    console.print("[bold cyan]Proceeding to autonomous TikTok publication...[/bold cyan]")
    uploader = TikTokUploader(headless=False)
    success = asyncio.run(uploader.upload_video(
        video_path=result.video_path,
        caption=result.caption,
        hashtags=result.hashtags,
        publish_now=publish,
        declare_ai=declare_ai
    ))
    
    if success:
        console.print("[bold green]🏆 Done! English video generated and published to TikTok![/bold green]")
    else:
        console.print("[bold red]⚠️ Video generated, but error occurred during publishing.[/bold red]")

@app.command()
def daily():
    """
    Runs the daily autonomous cycle: picks unposted English topic, generates video, and publishes to TikTok.
    """
    from daily_poster import run_daily_job
    console.print(Panel.fit("[bold green]🤖 Running Daily Autonomous Agent (English)...[/bold green]"))
    success = asyncio.run(run_daily_job())
    if success:
        console.print("[bold green]🏆 Daily English video published successfully![/bold green]")
    else:
        console.print("[bold red]❌ Error during daily publication cycle (check daily_poster.log).[/bold red]")

if __name__ == "__main__":
    app()
