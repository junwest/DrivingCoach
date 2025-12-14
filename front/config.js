/**
 * DrivingCoach API Configuration
 * 
 * 이 파일에서 API 주소를 한 곳에서 관리합니다.
 * IP 주소만 변경하면 모든 API 호출에 적용됩니다.
 */

// ========================================
// 여기만 수정하세요! ✏️
// ========================================

// 환경 변수 우선 (Vercel 배포용)
const ENV_BACKEND = typeof process !== 'undefined' && process.env?.REACT_APP_BACKEND_URL;
const ENV_AI_SERVER = typeof process !== 'undefined' && process.env?.REACT_APP_AI_SERVER_URL;

// ⚠️ Vercel 배포용: ngrok URL 직접 입력 (노트북 실행 중일 때만 작동)
const API_HOST = 'https://df68d74f529e.ngrok-free.app';

// 로컬 개발 시 localhost로 변경하려면 위 줄을 주석처리하고 아래를 활성화:
// const API_HOST = 'localhost';

// 같은 Wi-Fi 네트워크 (실제 기기 테스트용)
// 본인 컴퓨터의 IP 주소로 변경하세요
// const API_HOST = '192.168.0.100';  // 👈 여기를 본인 IP로 변경!


// ========================================
// 아래는 수정하지 마세요
// ========================================

// 포트 설정
const BACKEND_PORT = 8080;
const AI_SERVER_PORT = 5001;  // Docker에서 실제 사용하는 포트

// ngrok URL 체크 (https:// 또는 http://로 시작하면 ngrok)
const isNgrok = API_HOST.startsWith('http://') || API_HOST.startsWith('https://');

// 전체 URL 구성 (환경 변수 우선)
export const API_CONFIG = {
    // 백엔드 API
    BACKEND_URL: ENV_BACKEND || (isNgrok
        ? `${API_HOST}/api`  // ngrok은 이미 프로토콜 포함
        : `http://${API_HOST}:${BACKEND_PORT}/api`),

    // AI 서버 API
    AI_SERVER_URL: ENV_AI_SERVER || (isNgrok
        ? API_HOST  // ngrok은 이미 프로토콜 포함
        : `http://${API_HOST}:${AI_SERVER_PORT}`),

    // WebSocket (실시간 통신)
    WEBSOCKET_URL: ENV_BACKEND
        ? ENV_BACKEND.replace('http', 'ws').replace('/api', '/ws')
        : (isNgrok
            ? `${API_HOST.replace('https', 'wss').replace('http', 'ws')}/ws`
            : `ws://${API_HOST}:${BACKEND_PORT}/ws`)
};

// 디버그: 현재 설정 출력
console.log('📡 API Configuration:');
console.log('  Backend:', API_CONFIG.BACKEND_URL);
console.log('  AI Server:', API_CONFIG.AI_SERVER_URL);
console.log('  WebSocket:', API_CONFIG.WEBSOCKET_URL);

export default API_CONFIG;
