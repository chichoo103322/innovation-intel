# ============================================================
# 创新常州·对标快讯 — 定时任务安装脚本 (Windows Task Scheduler)
# 用法: 右键 → 使用 PowerShell 运行，或
#       powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
# 参数: -Action Install (默认) / Uninstall / Status
# ============================================================
param(
    [ValidateSet("Install", "Uninstall", "Status")]
    [string]$Action = "Install"
)

$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $Python) { Write-Host "[错误] 未找到 Python，请先安装 Python 3"; exit 1 }

$TaskNameDaily = "创新常州对标快讯-日报"
$TaskNameWeekly = "创新常州对标快讯-周报"
$TaskNameMonthly = "创新常州对标快讯-月报"
$LogFile = "$ProjectDir\cache\scheduler.log"

Write-Host "=== 创新情报定时任务设置 (Windows) ==="
Write-Host "项目目录: $ProjectDir"
Write-Host "Python:     $Python"
Write-Host ""

function Install-Tasks {
    # 先移除旧任务
    Uninstall-Tasks -Silent

    # 日报：每天早上 8:30
    $dailyAction = New-ScheduledTaskAction -Execute $Python `
        -Argument "run_daily.py" `
        -WorkingDirectory $ProjectDir
    $dailyTrigger = New-ScheduledTaskTrigger -Daily -At 08:30
    $dailySettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $TaskNameDaily -Action $dailyAction -Trigger $dailyTrigger -Settings $dailySettings -Description "创新常州对标快讯日报生成" | Out-Null
    Write-Host "  日报: 每天 8:30"

    # 周报：每周五 17:00
    $weeklyAction = New-ScheduledTaskAction -Execute $Python `
        -Argument "run_weekly.py" `
        -WorkingDirectory $ProjectDir
    $weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 17:00
    $weeklySettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $TaskNameWeekly -Action $weeklyAction -Trigger $weeklyTrigger -Settings $weeklySettings -Description "创新常州对标快讯周报生成" | Out-Null
    Write-Host "  周报: 周五 17:00"

    # 月报：每月最后一天 17:00（用脚本内部判断）
    $monthlyAction = New-ScheduledTaskAction -Execute $Python `
        -Argument "run_monthly.py" `
        -WorkingDirectory $ProjectDir
    $monthlyTrigger = New-ScheduledTaskTrigger -Daily -At 17:00
    $monthlySettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $TaskNameMonthly -Action $monthlyAction -Trigger $monthlyTrigger -Settings $monthlySettings -Description "创新常州对标快讯月报生成" | Out-Null
    Write-Host "  月报: 每天 17:00（自动判断是否月末）"

    Write-Host ""
    Write-Host "[完成] 定时任务已安装。可在'任务计划程序'中查看。"
    Write-Host "日志文件: $LogFile"
}

function Uninstall-Tasks {
    param([switch]$Silent)
    $tasks = @($TaskNameDaily, $TaskNameWeekly, $TaskNameMonthly)
    foreach ($t in $tasks) {
        try {
            Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction Stop
            if (-not $Silent) { Write-Host "[已移除] $t" }
        } catch {
            if (-not $Silent) { Write-Host "[跳过] $t 不存在" }
        }
    }
}

function Show-Status {
    $tasks = @($TaskNameDaily, $TaskNameWeekly, $TaskNameMonthly)
    foreach ($t in $tasks) {
        $info = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
        if ($info) {
            Write-Host "  [已安装] $t — 状态: $($info.State)"
        } else {
            Write-Host "  [未安装] $t"
        }
    }
}

switch ($Action) {
    "Install"   { Install-Tasks }
    "Uninstall" { Uninstall-Tasks }
    "Status"    { Show-Status }
}
