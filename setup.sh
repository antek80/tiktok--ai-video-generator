#!/usr/bin/env bash
# ==============================================================================
# TikTok AI Video Generator & Auto-Poster - Automated Setup Script
# ==============================================================================

set -e

echo ""
echo "=========================================================="
echo " 🚀 TikTok AI Video Generator & Auto-Poster - Setup"
echo "=========================================================="
echo ""

# 1. Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+ and re-run this script."
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Detected Python $PY_VER"

# 2. Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Please install FFmpeg:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu/Debian: sudo apt-get install -y ffmpeg"
    echo "   Windows: winget install Gyan.FFmpeg"
else
    echo "✅ FFmpeg is installed."
fi

# 3. Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment (.venv) already exists."
fi

# 4. Activate venv
source .venv/bin/activate

# 5. Install dependencies
echo "📥 Installing Python dependencies from requirements.txt..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# 6. Install Playwright browser
echo "🌐 Installing Playwright Chromium browser..."
playwright install chromium

# 7. Setup .env
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env from .env.example..."
    cp .env.example .env
    echo "💡 You can optionally edit .env to add your GEMINI_API_KEY (free at aistudio.google.com)."
else
    echo "✅ .env file already exists."
fi

echo ""
echo "=========================================================="
echo " 🎉 Installation Complete!"
echo "=========================================================="
echo ""
echo "Next Steps:"
echo " 1. Log in to your TikTok account (one-time setup):"
echo "    ./.venv/bin/python cli.py login"
echo ""
echo " 2. Generate and test a single video:"
echo "    ./.venv/bin/python cli.py generate --topic \"The Bermuda Triangle Mystery\" --upload"
echo ""
echo " 3. Start 24/7 Autopilot mode:"
echo "    ./.venv/bin/python autopilot.py"
echo "    or install macOS daemon: ./setup_daemon.sh"
echo ""
