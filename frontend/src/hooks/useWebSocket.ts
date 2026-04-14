import { useEffect, useRef, useState } from "react";

interface PipelineEvent {
  step: string;
  agent: string | null;
  progress: number;
  status: string;
}

export function useWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<PipelineEvent[]>([]);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);
      } catch {
        // ignore non-JSON messages
      }
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { connected, events };
}
