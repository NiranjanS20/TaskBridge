import { useState, useEffect } from 'react';

type ConnectionStatus = 'connecting' | 'connected' | 'error' | 'disconnected';

export function useRealtimeData<T>(endpoint: string, initialData: T) {
  const [data, setData] = useState<T>(initialData);
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [error] = useState<Error | null>(null);

  useEffect(() => {
    // MOCK: Simulate connecting to websocket
    setStatus('connecting');
    const timer = setTimeout(() => {
      setStatus('connected');
      // Simulated payload arrival
      setData(initialData);
    }, 1000);

    // MOCK: In production, instantiate WS here and bind to onmessage
    
    return () => clearTimeout(timer);
  }, [endpoint, initialData]);

  return { data, status, error };
}
