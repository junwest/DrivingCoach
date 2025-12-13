// context/WebSocketContext.tsx
import React, { createContext, useContext, useRef, useCallback } from "react";

type WSApi = {
  connect: (url: string) => Promise<void>;
  close: () => void;
  sendJson: (obj: any) => void;
  sendBinary: (buf: ArrayBuffer) => void;
  ref: React.MutableRefObject<WebSocket | null>;
  onceOpen: () => Promise<void>;
};

const WebSocketContext = createContext<WSApi | null>(null);

export const WebSocketProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const wsRef = useRef<WebSocket | null>(null);

  const onceOpen = useCallback(() => {
    return new Promise<void>((resolve, reject) => {
      const ws = wsRef.current;
      if (!ws) return reject(new Error("WS not created"));
      if (ws.readyState === WebSocket.OPEN) return resolve();
      const onOpen = () => { cleanup(); resolve(); };
      const onClose = () => { cleanup(); reject(new Error("WS closed before open")); };
      const cleanup = () => {
        ws.removeEventListener("open", onOpen);
        ws.removeEventListener("close", onClose);
      };
      ws.addEventListener("open", onOpen);
      ws.addEventListener("close", onClose);
    });
  }, []);

  const connect = useCallback(async (url: string) => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) return;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => console.log("[WS] open");
    ws.onmessage = (e) => {
      try { console.log("[WS] msg:", typeof e.data === "string" ? JSON.parse(e.data) : e.data); }
      catch { console.log("[WS] msg(raw):", e.data); }
    };
    ws.onerror = (e: any) => console.warn("[WS] error", e?.message ?? e);
  ws.onclose = (ev: any) => console.log("[WS] close", ev?.code, ev?.reason);
}, []);

  const close = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const sendJson = useCallback((obj: any) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }, []);

  const sendBinary = useCallback((buf: ArrayBuffer) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(buf);
  }, []);

  return (
    <WebSocketContext.Provider value={{ connect, close, sendJson, sendBinary, ref: wsRef, onceOpen }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("WebSocketProvider로 감싸주세요");
  return ctx;
};
