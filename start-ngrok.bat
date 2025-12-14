@echo off
chcp 65001 >nul
echo 🚀 DrivingCoach - ngrok 터널 시작
echo ==================================
echo.

REM ngrok 설치 확인
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ ngrok가 설치되지 않았습니다!
    echo.
    echo 설치 방법:
    echo   https://ngrok.com/download
    echo   다운로드 후 PATH에 추가하거나 이 폴더에 넣으세요.
    pause
    exit /b 1
)

REM ngrok.yml 확인
if not exist "ngrok.yml" (
    echo ❌ ngrok.yml 파일이 없습니다!
    echo 프로젝트 루트 디렉토리에서 실행하세요.
    pause
    exit /b 1
)

REM authtoken 확인
findstr "YOUR_NGROK_AUTH_TOKEN" ngrok.yml >nul
if %ERRORLEVEL% EQU 0 (
    echo ⚠️  ngrok.yml에서 YOUR_NGROK_AUTH_TOKEN을 실제 토큰으로 교체하세요!
    echo.
    echo 1. https://dashboard.ngrok.com/get-started/your-authtoken 접속
    echo 2. 토큰 복사
    echo 3. ngrok.yml 파일에서 YOUR_NGROK_AUTH_TOKEN 부분을 토큰으로 교체
    pause
    exit /b 1
)

echo ✅ Docker 서버가 실행 중인지 확인하세요!
echo    docker compose ps
echo.

REM ngrok 시작
echo 🔗 ngrok 터널 시작 중...
ngrok start --all --config=ngrok.yml

echo.
echo 터널이 종료되었습니다.
pause
