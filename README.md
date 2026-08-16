# 🎬 TikTok AI Video Generator & 24/7 Autonomous Publisher

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-Stealth-green.svg)](https://playwright.dev/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-60fps-red.svg)](https://ffmpeg.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

W pełni autonomiczny, bezobsługowy generator i publikator wiralowych wideo w formacie pionowym (9:16) dla **TikToka**, **YouTube Shorts** i **Instagram Reels**. System tworzy kompletne, 30-sekundowe historie z lektorem, dynamicznymi napisami Hormozi, 60fps gameplayem i animowanym serduszkiem CTA, a następnie sam publikuje je w TikTok Studio.

---

## 🌟 Główne Funkcje (Co potrafi system)

* **🎮 Wbudowany pakiet startowy 60FPS:** 15 gotowych, bezpłatnych teł wideo (Minecraft Parkour, Subway Surfers, GTA 5 Mega Ramps, CS:GO Surf) wgranych bezpośrednio do repozytorium (zero pobierania na start).
* **🧠 Nieskończony silnik tematów:** 50+ gotowych wiralowych historii z automatycznym fallbackiem do Gemini 2.0 Flash, który tworzy nieskończenie nowe tematy bez powtórzeń (`posted_history.json`).
* **💬 Precyzyjne napisy karaoke (Hormozi):** Dynamiczne, żółte podświetlanie aktualnie wymawianego słowa co do milisekundy (brak opóźnień audio-wideo).
* **❤️ TikTok Like Outro CTA:** 2-sekundowa animacja wektora serduszka TikToka z pulsem i napisem: *"PLEASE LIKE THE VIDEO TO SUPPORT MY WORK ❤️"*.
* **🛡️ Ochrona przed Shadowbanem (Anti-Shadowban):**
  * Wstrzykiwanie metadanych sprzętowych iPhone 15 Pro (Apple EXIF).
  * 2% ziarno filmowe rozbijające hashe klatek AI.
  * Audio Ducking 192kbps stereo (muzyka w tle automatycznie cichnie pod lektora).
* **🤖 Niezawodny Autopilot 24/7:**
  * Automatyzacja przeglądarki Playwright Stealth z zapamiętywaniem sesji.
  * Obsługa przetwarzania w chmurze TikToka (`aria-disabled="false"`), wpisywanie hashtagów i klikanie potwierdzenia.
  * 10 zaplanowanych publikacji na dobę (co ~90 minut).

---

## 📋 Wymagania wstępne (Przed instalacją)

Przed uruchomieniem upewnij się, że masz zainstalowane:
1. **Python 3.10+** – [Pobierz z python.org](https://www.python.org/downloads/) *(na Windowsie zaznacz opcję „Add Python to PATH”)*.
2. **Git** – [Pobierz z git-scm.com](https://git-scm.com/).
3. **FFmpeg** (silnik wideo):
   * **macOS:** `brew install ffmpeg`
   * **Ubuntu / Debian:** `sudo apt update && sudo apt install -y ffmpeg`
   * **Windows:** w PowerShell wpisz: `winget install Gyan.FFmpeg`
4. **Zwykłe konto TikTok** (na którym będą publikowane materiały).

---

## 🚀 Instrukcja uruchomienia krok po kroku

### KROK 1: Sklonowanie i automatyczna instalacja

Otwórz terminal (lub PowerShell na Windowsie) i wpisz:

```bash
# 1. Sklonuj repozytorium
git clone https://github.com/antek80/tiktok--ai-video-generator.git
cd tiktok--ai-video-generator

# 2. Uruchom automatyczny instalator (macOS / Linux):
./setup.sh
```

*(Jeśli jesteś na systemie Windows):*
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

---

### KROK 2: Jednorazowe logowanie do TikToka

Aby automat mógł publikować filmy na Twoim profilu, musisz połączyć konto (tylko 1 raz):

```bash
./.venv/bin/python cli.py login
```

1. Na ekranie pojawi się okno przeglądarki ze stroną logowania TikTok.
2. Zaloguj się na swoje konto (np. skanując kod QR aplikacją w telefonie lub przez login i hasło).
3. Gdy zobaczysz swój profil na TikToku, **wróć do terminala i naciśnij ENTER**.
4. Twoja sesja zostanie trwale zapisana w bezpiecznym katalogu `~/.tiktok_automation_session`.

---

### KROK 3: Uruchomienie Autopilota (Wybierz 1 z 3 sposobów)

#### Sposób A: Uniwersalny Autopilot z panelem na żywo (Zalecany – Mac / Windows / Linux)
Uruchamia interaktywny terminal z licznikiem do kolejnej publikacji i harmonogramem 10 filmów dziennie:

```bash
# Uruchomienie ciągłego autopilota:
./.venv/bin/python autopilot.py

# Opcja: opublikuj 1 film od razu na start:
./.venv/bin/python autopilot.py --now

# Opcja: publikuj regularnie co 60 minut:
./.venv/bin/python autopilot.py --interval 60
```

#### Sposób B: Cichy proces w tle dla macOS (LaunchAgent)
Działa niewidocznie w tle systemu macOS nawet po zamknięciu terminala i wyłączeniu okna:

```bash
# Instalacja i aktywacja usługi w tle:
./setup_daemon.sh

# Wyłączenie / usunięcie usługi:
launchctl unload ~/Library/LaunchAgents/com.tiktok.autoposter.plist
```

#### Sposób C: Ręczne generowanie pojedynczych filmów (CLI)
Możesz w każdej chwili wygenerować i przetestować pojedyncze wideo:

```bash
# 1. Wygeneruj film po angielsku (głos Brian):
./.venv/bin/python cli.py generate --topic "The Deep Ocean Bloop Mystery" --lang en

# 2. Wygeneruj film po polsku (głos Marek):
./.venv/bin/python cli.py generate --topic "Tajemnice Trójkąta Bermudzkiego" --lang pl

# 3. Wygeneruj i od razu opublikuj 1 film komendą all-in-one:
./.venv/bin/python cli.py auto --topic "The Philadelphia Experiment" --lang en
```

---

## ⚙️ Konfiguracja (`.env`)

W pliku `.env` możesz dostosować opcje (plik `.env` tworzy się automatycznie ze wzoru `.env.example`):

```ini
# Opcjonalny klucz Google Gemini AI (do nieskończonego wymyślania nowych tematów)
# Pobierz darmowy klucz: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=

# Domyślny głos narracji (darmowy silnik Edge-TTS)
DEFAULT_VOICE_EN=en-US-BrianNeural
DEFAULT_VOICE_PL=pl-PL-MarekNeural

# Filtry anty-shadowban
APPLY_FILM_GRAIN=true
GRAIN_INTENSITY=2
SPOOF_DEVICE_METADATA=true
SPOOFED_MAKE=Apple
SPOOFED_MODEL=iPhone 15 Pro

# Flaga oznaczania treści AI w TikTok Studio (true/false)
DECLARE_AI_CONTENT=false
```

---

## 🎬 Pobieranie dodatkowych teł wideo (Opcjonalne)

W repozytorium masz już 15 wbudowanych teł. Jeśli chcesz pobrać **ponad 50 kolejnych unikalnych klipów 1080x1920 60fps**:

```bash
./.venv/bin/python download_backgrounds.py
```
Skrypt automatycznie pobierze i potnie gameplaye z Minecrafta, GTA 5, Subway Surfers i CS:GO na 60-sekundowe kawałki.

---

## ❓ FAQ & Rozwiązywanie problemów

**1. Film ma 0 wyświetleń w pierwszych 30 minutach od publikacji – co robić?**
* **Niczego nie usuwaj ani nie ukrywaj!** Algorytm TikToka potrzebuje od 30 do 60 minut na przetworzenie wideo i kategoryzację przed wpuszczeniem go do pierwszej grupy testowej widzów (*Initial Test Batch*).

**2. Czy muszę płacić za jakiekolwiek API?**
* **Nie, 0 zł.** Głosy lektora (Edge-TTS), montaż wideo (FFmpeg), tła i tematy są w 100% darmowe. Klucz Gemini API jest również w 100% bezpłatny w AI Studio.

**3. Gdzie zapisują się gotowe filmy?**
* Wszystkie wyrenderowane pliki wideo `.mp4` trafiają do katalogu `output/`.

---

## 📄 Licencja
Projekt udostępniony na licencji [MIT](LICENSE). Możesz go dowolnie modyfikować i używać komercyjnie.
