import { useEffect, useRef, useCallback } from "react";
import { usePipelineStore } from "../stores/pipelineStore";

interface PipelineEvent {
  type: string;
  data: {
    chapter?: number;
    step?: string;
    agent?: string;
    status?: string;
    progress?: number;
    score?: number;
    error?: string;
  };
}

export function useWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectRef = useRef<() => void>(() => {});
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ action: "subscribe" }));
      };

      ws.onclose = () => {
        if (!shouldReconnectRef.current) {
          return;
        }
        reconnectTimerRef.current = setTimeout(() => connectRef.current(), 3000);
      };

      ws.onmessage = (event) => {
        try {
          const msg: PipelineEvent = JSON.parse(event.data);
          const store = usePipelineStore.getState();

          if (msg.type === "event") {
            const data = msg.data;
            // Update pipeline store based on event
            if (data.status === "running") {
              store.fetchStatus();
            } else if (data.step === "complete") {
              // Chapter completed, refresh
              store.fetchStatus();
            }
          } else if (msg.type === "subscription_confirmed") {
            // Connection established
          } else if (msg.type === "pong") {
            // Heartbeat response
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        // Will be handled by onclose
      };
    } catch {
      if (!shouldReconnectRef.current) {
        return;
      }
      // Connection failed, retry
      reconnectTimerRef.current = setTimeout(() => connectRef.current(), 3000);
    }
  }, [url]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "unsubscribe" }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { connect, disconnect };
}
