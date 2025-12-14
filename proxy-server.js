const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({});

const server = http.createServer((req, res) => {
    // CORS 헤더 추가
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', '*');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // /api 또는 /ws로 시작하면 백엔드로
    if (req.url.startsWith('/api') || req.url.startsWith('/ws')) {
        console.log(`[백엔드] ${req.method} ${req.url}`);
        proxy.web(req, res, { target: 'http://localhost:8080' });
    }
    // 나머지는 프론트엔드로
    else {
        console.log(`[프론트] ${req.method} ${req.url}`);
        proxy.web(req, res, { target: 'http://localhost:8081' });
    }
});

// WebSocket 처리
server.on('upgrade', (req, socket, head) => {
    console.log(`[WebSocket] ${req.url}`);
    proxy.ws(req, socket, head, { target: 'ws://localhost:8080' });
});

proxy.on('error', (err, req, res) => {
    console.error('프록시 에러:', err.message);
    if (res.writeHead) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('프록시 에러');
    }
});

const PORT = 9000;
server.listen(PORT, () => {
    console.log(`
🚀 통합 프록시 서버 시작!
  
  포트: ${PORT}
  프론트엔드: localhost:8081 -> /${''
  백엔드 API: localhost: 8080 -> /api/ *
    WebSocket: localhost: 8080 -> /ws/ *
  
✅ 이제 ngrok으로 포트 9000을 노출하세요:
        ngrok http 9000
        `);
});
