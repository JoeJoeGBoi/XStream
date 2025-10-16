@echo off
REM Installs a Windows Nginx build that includes the RTMP module and configures
REM it with a basic streaming setup.

setlocal enableextensions enabledelayedexpansion

REM Require administrative privileges (needed for writing to Program Files and firewall rules).
>nul 2>&1 net session
if not %errorlevel%==0 (
    echo This script must be run from an elevated command prompt ("Run as administrator").
    exit /b 1
)

REM Allow custom install directory as first argument, default to C:\nginx-rtmp.
if "%~1"=="" (
    set "INSTALL_ROOT=C:\nginx-rtmp"
) else (
    set "INSTALL_ROOT=%~1"
)

REM You can change this to a different release if needed.
set "DOWNLOAD_URL=https://github.com/illuspas/nginx-rtmp-win32/releases/download/v1.2.1/nginx-1.25.2.0-Gryphon.zip"
set "ZIP_NAME=nginx-rtmp.zip"
set "TEMP_DIR=%TEMP%\nginx_rtmp_install"

if exist "%TEMP_DIR%" rd /s /q "%TEMP_DIR%"
md "%TEMP_DIR%" || (
    echo Failed to create temporary working directory.
    exit /b 1
)

set "ZIP_PATH=%TEMP_DIR%\%ZIP_NAME%"

echo Downloading Nginx RTMP package...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%ZIP_PATH%'" || (
    echo Failed to download RTMP-enabled Nginx build.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)

echo Extracting archive...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%TEMP_DIR%' -Force" || (
    echo Failed to extract archive.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)

set "EXTRACTED_DIR="
for /d %%I in ("%TEMP_DIR%\nginx-*") do (
    set "EXTRACTED_DIR=%%I"
)

if not defined EXTRACTED_DIR (
    echo Could not find extracted nginx folder in %TEMP_DIR%.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)

echo Preparing installation directory at %INSTALL_ROOT% ...
if not exist "%INSTALL_ROOT%" (
    md "%INSTALL_ROOT%" || (
        echo Failed to create installation directory.
        rd /s /q "%TEMP_DIR%"
        exit /b 1
    )
)

REM Copy files into installation directory.
robocopy "%EXTRACTED_DIR%" "%INSTALL_ROOT%" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul
if not %errorlevel% LSS 8 (
    echo File copy failed.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)

REM Deploy RTMP-focused nginx.conf.
set "NGINX_CONF=%INSTALL_ROOT%\conf\nginx.conf"
>"%NGINX_CONF%" echo worker_processes  auto^;
>>"%NGINX_CONF%" echo events ^{
>>"%NGINX_CONF%" echo ^    worker_connections  1024^;
>>"%NGINX_CONF%" echo ^}
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo rtmp ^{
>>"%NGINX_CONF%" echo ^    server ^{
>>"%NGINX_CONF%" echo ^        listen 1935^;
>>"%NGINX_CONF%" echo ^        chunk_size 4096^;
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo ^        application live ^{
>>"%NGINX_CONF%" echo ^            live on^;
>>"%NGINX_CONF%" echo ^            record off^;
>>"%NGINX_CONF%" echo ^        ^}
>>"%NGINX_CONF%" echo ^    ^}
>>"%NGINX_CONF%" echo ^}
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo http ^{
>>"%NGINX_CONF%" echo ^    include       mime.types^;
>>"%NGINX_CONF%" echo ^    default_type  application/octet-stream^;
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo ^    sendfile        on^;
>>"%NGINX_CONF%" echo ^    keepalive_timeout  65^;
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo ^    server ^{
>>"%NGINX_CONF%" echo ^        listen       8080^;
>>"%NGINX_CONF%" echo ^        server_name  localhost^;
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo ^        location / ^{
>>"%NGINX_CONF%" echo ^            root   html^;
>>"%NGINX_CONF%" echo ^            index  index.html index.htm^;
>>"%NGINX_CONF%" echo ^        ^}
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo ^        location /stat ^{
>>"%NGINX_CONF%" echo ^            rtmp_stat all^;
>>"%NGINX_CONF%" echo ^            rtmp_stat_stylesheet stat.xsl^;
>>"%NGINX_CONF%" echo ^        ^}
>>"%NGINX_CONF%" echo.
>>"%NGINX_CONF%" echo ^        location /stat.xsl ^{
>>"%NGINX_CONF%" echo ^            root html^;
>>"%NGINX_CONF%" echo ^        ^}
>>"%NGINX_CONF%" echo ^    ^}
>>"%NGINX_CONF%" echo ^}

if not %errorlevel%==0 (
    echo Failed to write nginx configuration.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)

REM Allow RTMP (1935) and HTTP (8080) through Windows firewall.
echo Configuring Windows Firewall rules...
netsh advfirewall firewall add rule name="Nginx RTMP (TCP 1935)" dir=in action=allow protocol=TCP localport=1935 >nul
netsh advfirewall firewall add rule name="Nginx RTMP Status (TCP 8080)" dir=in action=allow protocol=TCP localport=8080 >nul

REM Create helper scripts to start/stop nginx easily.
set "START_SCRIPT=%INSTALL_ROOT%\start_nginx.bat"
set "STOP_SCRIPT=%INSTALL_ROOT%\stop_nginx.bat"
>"%START_SCRIPT%" echo @echo off
>>"%START_SCRIPT%" echo cd /d "%INSTALL_ROOT%"
>>"%START_SCRIPT%" echo start "Nginx RTMP" nginx.exe
>"%STOP_SCRIPT%" echo @echo off
>>"%STOP_SCRIPT%" echo cd /d "%INSTALL_ROOT%"
>>"%STOP_SCRIPT%" echo nginx.exe -s stop

echo.
echo Installation complete!
echo ----------------------------------------
echo Nginx RTMP has been installed to: %INSTALL_ROOT%
echo Use start_nginx.bat to launch the server and stop_nginx.bat to stop it.
echo RTMP endpoint: rtmp://^<your-ip^>/live
echo HTTP status page: http://localhost:8080/stat

echo Cleaning up temporary files...
rd /s /q "%TEMP_DIR%"

echo Done.
exit /b 0
