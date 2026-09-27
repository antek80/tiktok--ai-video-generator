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
echo " ⚙️ Configuring TikTok Auto-Poster Daemon (slots from .env)"
echo "=========================================================="

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS operating system."
    
    # Create LaunchAgents directory if not exists
    mkdir -p "$HOME/Library/LaunchAgents"

    # Unload existing if loaded
    launchctl unload "$PLIST_PATH" 2>/dev/null || true

    # Generate intervals dynamically based on .env
    INTERVALS_XML=$($PYTHON_EXEC -c "
from config.settings import settings
slots = settings.get_schedule_slots()
xml = ''
for s in slots:
    h, m = map(int, s.split(':'))
    xml += f'        <dict><key>Hour</key><integer>{h}</integer><key>Minute</key><integer>{m}</integer></dict>\n'
print(xml.rstrip())
")

    cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tiktok.autoposter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT_RUNNER</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
$INTERVALS_XML
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
    echo "📅 Scheduled daily publication slots:"
    $PYTHON_EXEC -c "from config.settings import settings; print('\\n'.join('   ' + s for s in settings.get_schedule_slots()))"
    echo "💡 To unload/stop the background daemon: launchctl unload $PLIST_PATH"

else
    echo "Detected Linux or non-macOS system."
    echo "Add this line to your crontab (crontab -e):"
    echo "30 8,10,11,13,14,16,17,19,20,22 * * * cd $PROJECT_DIR && $PYTHON_EXEC $PROJECT_DIR/daily_poster.py >> $PROJECT_DIR/cron.log 2>&1"
    echo "Or simply run: python autopilot.py"
fi
