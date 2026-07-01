@echo off
echo 서버 종료 중...
taskkill /f /im python.exe 2>nul
taskkill /f /im node.exe 2>nul
docker compose stop 2>nul
echo 완료
pause
