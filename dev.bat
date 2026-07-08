@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===== 함께사는양평 로컬 개발 서버 =====
echo.

echo [1/3] PostgreSQL 확인 중...
docker ps --filter name=yp_postgres --format "{{.Status}}" | findstr "Up" >nul
if %errorlevel% neq 0 (
    echo PostgreSQL 시작 중...
    docker compose up -d
    timeout /t 3 >nul
)
echo PostgreSQL: OK

echo [2/3] Flask + React 시작...
echo.
echo 브라우저에서 http://localhost:5000 으로 접속하세요
echo 로그인: admin@unocum.kr / pw1234
echo.
echo 종료하려면 Ctrl+C 두 번 누르세요
echo.

:: 1. Flask 서버 실행
start "Flask" cmd /c "cd /d "%~dp0" && venv\Scripts\python run.py"

:: 2. AI 검증 워커 실행 (5초 간격 폴링)
start "AIWorker" cmd /c "cd /d "%~dp0" && venv\Scripts\python services/ai_moderation_worker.py"

:: 3. Vite 프런트엔드 실행
start "React" cmd /c "cd /d "%~dp0frontend" && npx vite --host"

echo [3/3] 브라우저 자동 연결 중...
timeout /t 2 >nul
:: 3. 기본 웹 브라우저로 개발 사이트 바로 열기
start http://localhost:5000

exit
