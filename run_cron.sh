#!/bin/bash
# TikTok Autonomous Daily Poster Runner for macOS Launchd
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd /Users/antoniborawski/repos/tiktok--ai-video-generator

# Execute daily poster with project's Python virtualenv
/Users/antoniborawski/repos/tiktok--ai-video-generator/.venv/bin/python /Users/antoniborawski/repos/tiktok--ai-video-generator/daily_poster.py >> /Users/antoniborawski/repos/tiktok--ai-video-generator/daily_poster_cron.log 2>&1
