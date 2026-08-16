# 🎬 TikTok AI Video Generator & 24/7 Autonomous Publisher

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-Stealth-green.svg)](https://playwright.dev/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-60fps-red.svg)](https://ffmpeg.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fully autonomous, production-ready AI video generation and scheduled publishing engine designed for **TikTok**, **YouTube Shorts**, and **Instagram Reels**. Built from scratch to produce high-retention vertical videos (9:16) with zero human intervention.

---

## 🌟 Key Features

* **🎮 Pre-bundled 60FPS Gameplay Starter Pack**: 15 curated, copyright-free high-definition background clips (Minecraft Parkour, Subway Surfers, GTA 5 Mega Ramps, CS:GO Surf) included directly in the repo.
* **🧠 Infinite Topic Engine**: 50+ pre-curated viral mystery/fact topics with automatic Gemini 2.0 Flash generation fallback that never repeats a topic (`posted_history.json`).
* **💬 Sample-Accurate Hormozi Subtitles**: Dynamic word-by-word yellow highlighted subtitles with zero cumulative timing drift.
* **❤️ TikTok Double-Tap Like Outro**: 2.0s animated `#FE2C55` vector heart with pulse ripple and high-converting CTA: *"PLEASE LIKE THE VIDEO TO SUPPORT MY WORK ❤️"*.
* **🛡️ Anti-Shadowban Engine**:
  * iPhone 15 Pro Apple device metadata spoofing.
  * 2% film grain filter to break AI hash fingerprinting.
  * Studio-grade 192kbps stereo audio ducking (BGM drops automatically during speech).
* **🤖 Autonomous Scheduled Auto-Poster**:
  * Playwright Stealth browser automation with persistent session storage (`~/.tiktok_automation_session`).
  * Handles TikTok Studio chunk uploads, transcode waiting (`aria-disabled="false"`), caption entry, and modal confirmations.
  * 10 daily publication slots out of the box (every ~90 minutes).

---

## 🚀 Quick Start (3 Steps)

### Step 1: Clone & Run Setup
```bash
git clone https://github.com/antek80/tiktok--ai-video-generator.git
cd tiktok--ai-video-generator

# Run automated 1-click installer (creates venv, installs dependencies & browser)
./setup.sh
```

*(Optional)* If you want Gemini AI to generate custom topics dynamically, add your free key to `.env`:
```bash
cp .env.example .env
# Edit .env -> GEMINI_API_KEY=your_key_here
```

---

### Step 2: One-Time TikTok Login
```bash
./.venv/bin/python cli.py login
```
* A browser window will open.
* Log in to your TikTok account (via QR code or login/password).
* Press **Enter** in the terminal once logged in. Your session cookies will be safely stored locally in `~/.tiktok_automation_session`.

---

### Step 3: Start 24/7 Autopilot
Choose how you want to run the automated publisher:

#### Option A: Cross-Platform Autopilot (Mac, Linux, Windows)
```bash
# Starts live terminal dashboard with automatic countdown and 10 daily scheduled slots
./.venv/bin/python autopilot.py

# Or post immediately once right now:
./.venv/bin/python autopilot.py --now

# Or post every 60 minutes:
./.venv/bin/python autopilot.py --interval 60
```

#### Option B: Native macOS Background Service (`launchd`)
```bash
# Installs and enables background daemon that runs even after closing the terminal
./setup_daemon.sh
```

---

## 🛠️ CLI Command Reference

You can also generate and test videos manually using `cli.py`:

### 1. Generate a Single Video
```bash
# English video with Brian neural voice
./.venv/bin/python cli.py generate --topic "The Mysterious Bloop Sound" --lang en

# Polish video with Marek neural voice
./.venv/bin/python cli.py generate --topic "Tajemnice Rowu Mariańskiego" --lang pl
```

### 2. Upload an Existing Video File
```bash
./.venv/bin/python cli.py upload \
  --video output/video_xxxx.mp4 \
  --caption "The terrifying sound recorded in the deep ocean #mystery #facts #fyp"
```

### 3. All-In-One Single Command (Generate + Upload)
```bash
./.venv/bin/python cli.py auto --topic "The Philadelphia Experiment" --lang en
```

### 4. Download 50+ Additional Gameplay Backgrounds
```bash
# Automatically downloads & slices 100+ fresh 1080x1920 60fps vertical gameplay clips
./.venv/bin/python download_backgrounds.py
```

---

## 📁 Project Architecture

```
tiktok--ai-video-generator/
├── agent/                      # Playwright stealth browser & TikTok Studio uploader
│   ├── browser.py              # Stealth browser session manager
│   ├── session_manager.py      # Cookie & authentication storage
│   └── tiktok_uploader.py      # Multi-step upload, transcoding & publish handler
├── assets/                     # Starter packs, fonts, SFX, and backgrounds
│   ├── backgrounds/            # 60fps vertical gameplay clips (Minecraft, GTA, Subway Surfers)
│   ├── fonts/                  # Impact.ttf & fonts for Hormozi subtitles
│   └── music/                  # Cinematic background ambient music
├── config/                     # Settings & environment variables
│   └── settings.py
├── core/                       # Video generation engine
│   ├── asset_manager.py        # Outro heart animation & entity card generator
│   ├── audio_engine.py         # Edge-TTS voiceover & audio ducking
│   ├── script_generator.py     # Gemini AI & factual story scripts
│   ├── subtitle_engine.py      # Sample-accurate dynamic Hormozi subtitles
│   └── video_engine.py         # Quad-layer FFmpeg composition engine
├── autopilot.py                # 24/7 cross-platform autopilot daemon
├── daily_poster.py             # Single scheduled slot runner with history tracker
├── download_backgrounds.py     # YouTube vertical gameplay downloader/slicer
├── setup.sh                    # 1-click automated environment installer
├── setup_daemon.sh             # Native macOS launchd daemon installer
└── requirements.txt            # Python dependencies
```

---

## ⚙️ Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for dynamic story generation | *Optional* |
| `DEFAULT_VOICE_EN` | Default English narrator voice | `en-US-BrianNeural` |
| `DEFAULT_VOICE_PL` | Default Polish narrator voice | `pl-PL-MarekNeural` |
| `APPLY_FILM_GRAIN` | Adds subtle film grain to bypass frame hash duplication | `true` |
| `SPOOF_DEVICE_METADATA` | Injects Apple iPhone 15 Pro EXIF metadata | `true` |
| `DECLARE_AI_CONTENT` | Discloses AI-generated content toggle in TikTok Studio | `false` |

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
