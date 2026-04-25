import { useEffect, useMemo, useRef, useState } from 'react';

import { UserRole, websocketUrl } from '@/lib/api';

type EventPayload = { event: string; payload?: Record<string, unknown> };

interface Options {
  role: UserRole;
  userId?: string;
}

export function useWebSocket({ role, userId }: Options) {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<EventPayload[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const debounceRef = useRef<number | null>(null);
  const bufferRef = useRef<EventPayload[]>([]);

  const wsUrl = useMemo(() => {
    if (!userId) {
      return null;
    }
    return websocketUrl(role, userId);
  }, [role, userId]);

  useEffect(() => {
    if (!wsUrl) {
      setConnected(false);
      setEvents([]);
      return;
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as EventPayload;
        bufferRef.current.push(parsed);
        if (debounceRef.current !== null) {
          window.clearTimeout(debounceRef.current);
        }
        debounceRef.current = window.setTimeout(() => {
          setEvents((prev) => [...bufferRef.current, ...prev].slice(0, 50));
          bufferRef.current = [];
        }, 150);
      } catch {
        // ignore malformed events
      }
    };

    return () => {
      ws.close();
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [wsUrl]);

  return { connected, events };
}
