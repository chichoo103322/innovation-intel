#!/bin/bash
# ============================================================
# 创新常州·对标快讯 — 定时任务安装脚本 (Mac/Linux)
# 日报: launchd 每30分钟触发（自带去重，醒了就补跑）
# 周报/月报: cron 定点触发
# 用法: bash setup_scheduler.sh [--uninstall|--status]
# ============================================================
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(which python3 2>/dev/null || which python 2>/dev/null)"
CRON_MARKER="# innovation-intel"
PLIST_NAME="com.innovation.daily.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=== 创新情报定时任务设置 ==="
echo "项目目录: $PROJECT_DIR"
echo "Python:    $PYTHON"
echo ""

install_all() {
    # ---- 日报：launchd 每30分钟触发 ----
    echo "[日报] 安装 launchd 定时任务..."
    cat > "$PLIST_PATH" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.innovation.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$PROJECT_DIR/run_daily.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/cache/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/cache/launchd.log</string>
</dict>
</plist>
PLISTEOF

    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
    echo "  日报: 每30分钟自动检测（已生成则跳过，工作日生成）"

    # ---- 周报：cron 周五 17:00 ----
    echo "[周报] 安装 cron 定时任务..."
    { crontab -l 2>/dev/null || true; } | grep -v "$CRON_MARKER-weekly" > /tmp/cron_tmp || true
    echo "0 17 * * 5 cd $PROJECT_DIR && $PYTHON run_weekly.py >> $PROJECT_DIR/cache/cron.log 2>&1 $CRON_MARKER-weekly" >> /tmp/cron_tmp
    crontab /tmp/cron_tmp
    echo "  周报: 周五 17:00"

    # ---- 月报：cron 月末 17:00 ----
    echo "[月报] 安装 cron 定时任务..."
    { crontab -l 2>/dev/null || true; } | grep -v "$CRON_MARKER-monthly" > /tmp/cron_tmp || true
    echo "0 17 28-31 * * [ \$(date -d tomorrow +\%d) -eq 1 ] && cd $PROJECT_DIR && $PYTHON run_monthly.py >> $PROJECT_DIR/cache/cron.log 2>&1 $CRON_MARKER-monthly" >> /tmp/cron_tmp
    crontab /tmp/cron_tmp
    echo "  月报: 每月最后一天 17:00"

    echo ""
    echo "[完成] 定时任务已安装。"
    echo "  日志: $PROJECT_DIR/cache/launchd.log"
    echo ""
    echo "  注意：电脑睡眠期间不会执行，唤醒后 launchd 会在30分钟内自动补跑。"
}

uninstall_all() {
    echo "[移除] 正在卸载定时任务..."
    launchctl unload "$PLIST_PATH" 2>/dev/null && rm -f "$PLIST_PATH" && echo "  已移除 launchd 日报" || echo "  (launchd 日报未安装)"
    { crontab -l 2>/dev/null | grep -v "$CRON_MARKER" > /tmp/cron_tmp && crontab /tmp/cron_tmp && echo "  已移除 cron 周报/月报"; } || echo "  (cron 未安装)"
    echo "[完成]"
}

show_status() {
    echo "--- launchd 日报 ---"
    if launchctl list | grep -q "com.innovation.daily"; then
        echo "  [已安装] com.innovation.daily (每30分钟)"
    else
        echo "  [未安装]"
    fi
    echo "--- cron 周报/月报 ---"
    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        crontab -l 2>/dev/null | grep "$CRON_MARKER"
    else
        echo "  [未安装]"
    fi
}

case "${1:-}" in
    --uninstall) uninstall_all ;;
    --status)    show_status ;;
    *)           install_all ;;
esac
