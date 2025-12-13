#!/bin/bash

# DrivingCoach - 전체 프로젝트 실행 스크립트 (Mac/Linux)
# 이 파일을 실행하면 백엔드와 AI 서버가 자동으로 시작됩니다.

echo "======================================"
echo "🚗 DrivingCoach 프로젝트 시작"
echo "======================================"

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되어 있지 않습니다."
    echo "   https://www.docker.com/products/docker-desktop 에서 설치해주세요."
    exit 1
fi

# Docker Compose 확인
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되어 있지 않습니다."
    echo "   Docker Desktop을 설치하면 자동으로 포함됩니다."
    exit 1
fi

# Docker 실행 확인
if ! docker info &> /dev/null; then
    echo "❌ Docker가 실행되고 있지 않습니다."
    echo "   Docker Desktop을 실행해주세요."
    exit 1
fi

echo ""
echo "✅ Docker 확인 완료"
echo ""
echo "🔨 서버 빌드 및 실행 중..."
echo "   (처음 실행 시 5-10분 소요될 수 있습니다)"
echo ""

# Docker Compose로 실행
docker-compose up --build -d

# 실행 결과 확인
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "✅ 서버 시작 완료!"
    echo "======================================"
    echo ""
    echo "📍 백엔드 서버: http://localhost:8080"
    echo "   Swagger UI: http://localhost:8080/swagger-ui/index.html"
    echo ""
    echo "📍 AI 서버: http://localhost:5000"
    echo "   API 문서: http://localhost:5000/docs"
    echo ""
    echo "======================================"
    echo "📱 모바일 앱 설정:"
    echo "   1. front/config.js 파일 열기"
    echo "   2. API_HOST를 본인 컴퓨터 IP로 변경"
    echo "   3. 앱 실행: cd front && npm start"
    echo "======================================"
    echo ""
    echo "⏹️  서버 중지: docker-compose down"
    echo "📊 로그 확인: docker-compose logs -f"
    echo ""
else
    echo ""
    echo "❌ 서버 시작 실패"
    echo "   로그 확인: docker-compose logs"
    exit 1
fi
