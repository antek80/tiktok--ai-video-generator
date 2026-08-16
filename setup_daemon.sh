#!/usr/bin/env bash
# ==============================================================================
# TikTok AI Video Generator - Background Daemon Setup Script
# Configures native macOS launchd background service
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python"
PLIST_PATH="$HOME/Library/LaunchAgents/com.tiktok.autoposter.plist"
SCRIPT_RUNNER="$PROJECT_DIR/run_cron.sh"

echo "=========================================================="
echo " ⚙️ Configuring TikTok 10x Daily Auto-Poster Daemon"
echo "=========================================================="

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS operating system."
    
    # Create LaunchAgents directory if not exists
    mkdir -p "$HOME/Library/LaunchAgents"

    # Unload existing if loaded
    launchctl unload "$PLIST_PATH" 2>/dev/null || true

    cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tiktok.autoposter</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_RUNNER</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>11</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>13</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>17</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>22</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/launchd_stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
</dict>
</plist>
EOF

    # Make run_cron.sh executable
    chmod +x "$SCRIPT_RUNNER"

    # Load launchd job
    launchctl load "$PLIST_PATH"

    echo "✅ Successfully installed and loaded LaunchAgent: $PLIST_PATH"
    echo "📅 Scheduled 10 daily publication slots: 08:30, 10:00, 11:30, 13:00, 14:30, 16:00, 17:30, 19:00, 20:30, 22:00"
    echo "💡 To unload/stop the background daemon: launchctl unload $PLIST_PATH"

else
    echo "Detected Linux or non-macOS system."
    echo "Add this line to your crontab (crontab -e):"
    echo "30 8,10,11,13,14,16,17,19,20,22 * * * cd $PROJECT_DIR && $PYTHON_EXEC $PROJECT_DIR/daily_poster.py >> $PROJECT_DIR/cron.log 2>&1"
    echo "Or simply run: python autopilot.py"
fi
