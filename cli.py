import asyncio
import logging
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
    topic: str = typer.Option(..., "--topic", "-t", help="Temat lub idea wideo (np. 'Fakty o czarnych dziurach')"),
    lang: str = typer.Option("pl", "--lang", "-l", help="Język lektora: 'pl' lub 'en'"),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Nazwa głosu Edge-TTS (np. pl-PL-MarekNeural)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="Klucz Gemini API (opcjonalny)")
):
    """
    Generuje pionowe wideo (9:16) z filtrami Anti-Shadowban, dynamicznymi napisami i montażem.
    """
    console.print(Panel.fit(f"[bold cyan]🎬 Generowanie wideo TikTok dla tematu:[/bold cyan] [yellow]{topic}[/yellow]"))
    
    pipeline = Pipeline(gemini_api_key=api_key or settings.gemini_api_key, voice=voice)
    result = pipeline.generate_video(topic=topic, language=lang, voice=voice)
    
    table = Table(title="✅ Wygenerowano pomyślnie!", show_header=True, header_style="bold magenta")
    table.add_column("Parametr", style="dim", width=18)
    table.add_column("Wartość")
    
    table.add_row("Plik wideo", str(result.video_path))
    table.add_row("Czas trwania", f"{result.duration:.2f} s")
    table.add_row("Hook (3 sekundy)", result.script.hook)
    table.add_row("Opis (Caption)", result.caption)
    table.add_row("Hashtagi", " ".join(result.hashtags))
    
    console.print(table)
    console.print(f"\n[green]Aby opublikować na TikToku, uruchom:[/green] [bold]python cli.py upload --video {result.video_path}[/bold]")

@app.command()
def login():
    """
    Otwiera okno przeglądarki, aby zalogować się na konto TikTok i zapisać trwałą sesję.
    """
    console.print("[bold yellow]Uruchamianie przeglądarki w trybie logowania...[/bold yellow]")
    sm = SessionManager()
    asyncio.run(sm.login_interactively())

@app.command()
def status():
    """
    Sprawdza, czy sesja TikTok jest aktywna i zalogowana.
    """
    console.print("[bold cyan]Sprawdzanie stanu sesji TikTok...[/bold cyan]")
    sm = SessionManager()
    is_logged = asyncio.run(sm.is_logged_in())
    if is_logged:
        console.print("[bold green]✅ Sesja jest aktywna i zalogowana! Agent może publikować.[/bold green]")
    else:
        console.print("[bold red]❌ Brak aktywnej sesji. Uruchom `python cli.py login`, aby się zalogować.[/bold red]")

@app.command()
def upload(
    video: Path = typer.Option(..., "--video", "-v", help="Ścieżka do pliku .mp4"),
    caption: Optional[str] = typer.Option(None, "--caption", "-c", help="Opis wideo"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Hashtagi oddzielone spacją (np. '#fyp #viral')"),
    publish: bool = typer.Option(True, "--publish/--draft", help="Opublikuj natychmiast lub zapisz wersję roboczą"),
    declare_ai: bool = typer.Option(False, "--declare-ai/--no-declare-ai", help="Oznacz film oficjalną etykietą AI na TikToku")
):
    """
    Autonomicznie publikuje wideo na TikToku za pomocą Playwright Stealth.
    """
    console.print(Panel.fit(f"[bold blue]🚀 Autonomiczny upload wideo na TikTok:[/bold blue] {video.name}"))
    
    hashtags_list = tags.split() if tags else ["#fyp", "#viral", "#dlaciebie"]
    cap = caption or f"Niesamowite wideo! Sprawdź do końca 🔥"
    
    uploader = TikTokUploader(headless=False)
    success = asyncio.run(uploader.upload_video(
        video_path=video,
        caption=cap,
        hashtags=hashtags_list,
        publish_now=publish,
        declare_ai=declare_ai
    ))
    
    if success:
        console.print("[bold green]🎉 Wideo zostało pomyślnie przesłane na TikTok![/bold green]")
    else:
        console.print("[bold red]❌ Wystąpił błąd podczas przesyłania wideo.[/bold red]")

@app.command()
def auto(
    topic: str = typer.Option(..., "--topic", "-t", help="Temat wideo"),
    lang: str = typer.Option("pl", "--lang", "-l", help="Język lektora"),
    publish: bool = typer.Option(True, "--publish/--draft", help="Automatycznie opublikuj po wyrenderowaniu"),
    declare_ai: bool = typer.Option(False, "--declare-ai/--no-declare-ai", help="Oznacz film oficjalną etykietą AI na TikToku")
):
    """
    Pełny automat: Generuje wideo od zera i natychmiast publikuje je na TikToku.
    """
    console.print(Panel.fit(f"[bold magenta]⚡ AUTO-PIPELINE: Generowanie + Publikacja dla:[/bold magenta] [yellow]{topic}[/yellow]"))
    
    # 1. Generowanie
    pipeline = Pipeline()
    result = pipeline.generate_video(topic=topic, language=lang)
    console.print(f"✅ Wyrenderowano: [green]{result.video_path}[/green]")
    
    # 2. Publikacja
    console.print("[bold cyan]Przechodzę do automatycznej publikacji...[/bold cyan]")
    uploader = TikTokUploader(headless=False)
    success = asyncio.run(uploader.upload_video(
        video_path=result.video_path,
        caption=result.caption,
        hashtags=result.hashtags,
        publish_now=publish,
        declare_ai=declare_ai
    ))
    
    if success:
        console.print("[bold green]🏆 Gotowe! Wideo wygenerowane i opublikowane na TikToku bez ryzyka shadowbanu.[/bold green]")
    else:
        console.print("[bold red]⚠️ Wygenerowano wideo, ale wystąpił problem z publikacją na TikToku.[/bold red]")

if __name__ == "__main__":
    app()
