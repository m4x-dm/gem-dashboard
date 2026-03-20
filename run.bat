@echo off
title GEM Dashboard
echo.
echo  ========================================
echo    GEM ETF Dashboard - uruchamianie...
echo  ========================================
echo.
cd /d "%~dp0"
C:\Python314\python.exe -c "import subprocess,re; o=subprocess.run(['netstat','-ano'],capture_output=True,text=True).stdout; pids={m.group(1) for m in re.finditer(r':8501\s+\S+\s+LISTENING\s+(\d+)',o)}; [subprocess.run(['taskkill','/F','/PID',p],capture_output=True) for p in pids]; print(f'  Zamknieto {len(pids)} instancji' if pids else '  Port 8501 wolny')"
echo  Startuje na http://localhost:8501
echo.
C:\Python314\python.exe -m streamlit run app.py --server.port 8501
pause
