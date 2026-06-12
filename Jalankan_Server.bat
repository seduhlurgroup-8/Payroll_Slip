@echo off
title Server Payroll Merempah
echo ===================================================
echo   MEMULAI LOCAL SERVER PAYROLL - PT. SIG (MEREMPAH)
echo ===================================================
echo.
echo Server akan dijalankan di http://localhost:8000
echo Membuka browser default otomatis...
echo.

:: Pindah ke folder tempat file .bat ini berada
cd /d "%~dp0"

:: Jalankan browser secara otomatis membuka alamat server
start "" "http://localhost:8000"

:: Eksekusi Python server
python pythonscript/payroll_server.py

pause
