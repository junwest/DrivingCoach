#!/bin/bash

echo "🚀 DrivingCoach - ngrok 터널 시작"
echo "=================================="
echo ""

# ngrok 설치 확인
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok가 설치되지 않았습니다!"
    echo ""
    echo "설치 방법:"
    echo "  Mac: brew install ngrok"
    echo "  또는: https://ngrok.com/download"
    exit 1
fi

# ngrok.yml 확인
if [ ! -f "ngrok.yml" ]; then
    echo "❌ ngrok.yml 파일이 없습니다!"
    echo "프로젝트 루트 디렉토리에서 실행하세요."
    exit 1
fi

# authtoken 확인
if grep -q "YOUR_NGROK_AUTH_TOKEN" ngrok.yml; then
    echo "⚠️  ngrok.yml에서 YOUR_NGROK_AUTH_TOKEN을 실제 토큰으로 교체하세요!"
    echo ""
    echo "1. https://dashboard.ngrok.com/get-started/your-authtoken 접속"
    echo "2. 토큰 복사"
    echo "3. ngrok.yml 파일에서 YOUR_NGROK_AUTH_TOKEN 부분을 토큰으로 교체"
    exit 1
fi

echo "✅ Docker 서버가 실행 중인지 확인하세요!"
echo "   docker compose ps"
echo ""

# ngrok 시작
echo "🔗 ngrok 터널 시작 중..."
ngrok start --all --config=ngrok.yml

# 종료 메시지
echo ""
echo "터널이 종료되었습니다."
