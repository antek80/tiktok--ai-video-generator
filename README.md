# 🎬 TikTok AI Video Generator & Autonomous Publisher

Zautomatyzowany generator pionowych wideo (9:16) dla TikTok / Shorts / Reels z wbudowaną ochroną przed **Shadowbanem / 200-view jail** oraz autonomicznym agentem publikującym w oparciu o Playwright Stealth.

---

## 🚀 Główne Funkcje

### 1. Ochrona przed Shadowbanem (Anti-Shadowban Engine)
- **Anti-Fingerprinting**: Czyszczenie nagłówków serwerowych FFmpeg (`-map_metadata -1`) i wstrzykiwanie metadanych mobilnych (Apple iPhone 15 Pro, iOS).
- **Film Grain**: Subtelne 2% ziarno filmowe rozbijające hashe klatek AI.
- **Audio Jakości Studio**: Dźwięk 192 kbps stereo z audio duckingiem (automatyczne wyciszanie muzyki tła pod lektora).
- **Dynamiczny Pacing**: Krótkie ujęcia (1.5–2.5 s) z płynnym ruchem kamery (Zoom In, Zoom Out, Pan Left/Right).
- **Napisy Word-by-Word (Karaoke)**: Dynamiczne napisy w stylu MrBeast / Alex Hormozi podświetlające wymawiane słowo w locie.

### 2. Autonomiczny Agent Publikujący na TikTok (Playwright Stealth)
- **Persistent Session**: Logujesz się tylko raz przez kod QR / hasło (`python cli.py login`), a ciasteczka są bezpiecznie przechowywane.
- **Auto-Upload & Tagging**: Samodzielnie wpisuje opis zoptymalizowany pod SEO, dodaje hashtagi i kadr okładki.
- **AI Content Disclosure**: Automatycznie zaznacza wymaganą przez TikTok flagę *„Treści wygenerowane przez AI”*, co zapobiega banom za nieoznaczone materiały syntetyczne.
- **Human-like Delays**: Symuluje naturalne pisanie na klawiaturze i opóźnienia człowieka.

---

## 🛠️ Instalacja

```bash
# 1. Wejdź do katalogu
cd tiktok--ai-video-generator

# 2. Aktywuj środowisko
source .venv/bin/activate

# 3. Zainstaluj zależności i przeglądarkę Playwright
pip install -r requirements.txt
playwright install chromium

# 4. Skonfiguruj .env (opcjonalnie klucz Gemini)
cp .env.example .env
```

---

## 💻 Instrukcja Użycia (CLI)

### 1. Wygenerowanie Wideo
```bash
# Wideo po polsku (domyślny głos: MarekNeural)
python cli.py generate --topic "Dlaczego oceany są niezbadane?"

# Wideo po angielsku
python cli.py generate --topic "Mysteries of the deep ocean" --lang en
```

### 2. Jednorazowe Logowanie do TikToka
```bash
python cli.py login
```
*Otworzy się okno przeglądarki. Zaloguj się telefonem (kod QR) lub hasłem. Sesja zostanie trwale zapisana.*

### 3. Sprawdzenie Statusu Logowania
```bash
python cli.py status
```

### 4. Publikacja Wygenerowanego Wideo
```bash
python cli.py upload --video output/video_xxxx.mp4 --caption "Tajemnice oceanów 🌊 Sprawdź to!" --tags "#ciekawostki #nauka #fyp"
```

### 5. Pełny Automat (Generowanie + Natychmiastowa Publikacja)
```bash
python cli.py auto --topic "Czarne dziury i zakrzywienie czasu"
```
