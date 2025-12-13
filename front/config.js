/**
 * DrivingCoach API Configuration
 * 
 * 이 파일에서 API 주소를 한 곳에서 관리합니다.
 * IP 주소만 변경하면 모든 API 호출에 적용됩니다.
 */

// ========================================
// 여기만 수정하세요! ✏️
// ========================================

// 로컬 개발 (같은 컴퓨터)
// const API_HOST = 'localhost';

// 같은 Wi-Fi 네트워크 (실제 기기 테스트)
// 본인 컴퓨터의 IP 주소로 변경하세요
const API_HOST = '192.168.0.100';  // 👈 여기를 본인 IP로 변경!

// ngrok 사용 시 (외부 접근)
// const API_HOST = 'https://abc123.ngrok.io'  // ngrok URL로 변경

// ========================================
// 아래는 수정하지 마세요
// ========================================

// 포트 설정
const BACKEND_PORT = 8080;
const AI_SERVER_PORT = 5000;

// 프로토콜 자동 설정
const isNgrok = API_HOST.includes('ngrok.io');
const protocol = isNgrok ? '' : 'http://';

// 전체 URL 구성
export const API_CONFIG = {
    // 백엔드 API
    BACKEND_URL: isNgrok
        ? `${API_HOST}/api`
        : `${protocol}${API_HOST}:${BACKEND_PORT}/api`,

    // AI 서버 API
    AI_SERVER_URL: isNgrok
        ? API_HOST  // ngrok은 한 URL에 모두 포함
        : `${protocol}${API_HOST}:${AI_SERVER_PORT}`,

    // WebSocket (실시간 통신)
    WEBSOCKET_URL: isNgrok
        ? API_HOST.replace('https', 'wss')
        : `ws://${API_HOST}:${BACKEND_PORT}/ws`
};

// 디버그: 현재 설정 출력
console.log('📡 API Configuration:');
console.log('  Backend:', API_CONFIG.BACKEND_URL);
console.log('  AI Server:', API_CONFIG.AI_SERVER_URL);
console.log('  WebSocket:', API_CONFIG.WEBSOCKET_URL);

export default API_CONFIG;
