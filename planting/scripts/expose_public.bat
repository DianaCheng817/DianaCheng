@echo off
chcp 65001 >nul
REM ============================================================
REM 一键启动公网 MVP（Windows 批处理）
REM 作用：启动本机 FastAPI 服务 + Cloudflare 临时隧道，输出可外部访问的 https 网址
REM 前置：1) 本机已安装依赖（pip install -r requirements.txt）
REM       2) 已下载 cloudflared.exe 到 scripts/cloudflared.exe（约 53MB）
REM          下载地址 https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
REM 用法：双击本文件，或在命令行执行 scripts\expose_public.bat
REM 说明：隧道地址每次启动都会变化；窗口保持打开即公网可访问，关闭窗口则失效。
REM ============================================================

setlocal
cd /d "%~dp0.."

REM 步骤 1：后台启动 FastAPI 服务（端口 8000）
echo [1/2] 启动本地服务 http://127.0.0.1:8000 ...
start "planting-api" /min cmd /c "python run.py --port 8000"

REM 等待服务就绪
timeout /t 4 /nobreak >nul

REM 步骤 2：启动 Cloudflare 隧道并打印网址
echo [2/2] 建立 Cloudflare 公网隧道（首次约需 5-10 秒）...
echo.
echo ===================================================================
echo  请在下方日志中查找形如 https://xxxx.trycloudflare.com 的公网网址
echo  该网址即为老师可访问的 MVP 地址；保持本窗口开启即持续可用。
echo ===================================================================
echo.

if exist "scripts\cloudflared.exe" (
    scripts\cloudflared.exe tunnel --url http://127.0.0.1:8000 --no-autoupdate --protocol http2
) else (
    echo [错误] 未找到 scripts\cloudflared.exe，请先按前置说明下载。
    pause
)

endlocal
