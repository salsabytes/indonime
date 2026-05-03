@echo off
setlocal

set "URL=https://github.com/salsa-ram/indonime/releases/download/v1.0.0-mpv/mpv.7z"
set "FILE=mpv.7z"
set "DIR=mpv"

echo [Indonime] Downloading MPV...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%URL%' -OutFile '%FILE%'"

if not exist "%FILE%" (
  echo [Error] Download failed.
  pause
  exit /b
)

echo [Indonime] Extracting to ./%DIR%...
if exist "C:\Program Files\7-Zip\7z.exe" (
  "C:\Program Files\7-Zip\7z.exe" x "%FILE%" -o"%DIR%" -y >nul
) else if exist "C:\Program Files\WinRAR\WinRAR.exe" (
  "C:\Program Files\WinRAR\WinRAR.exe" x "%FILE%" "%DIR%\" >nul
) else (
  echo [Error] 7-Zip or WinRAR not found. Extract manual: %FILE%
  pause
  exit /b
)

if exist "%FILE%" del /f /q "%FILE%"
echo [Indonime] Setup complete.
timeout /t 3