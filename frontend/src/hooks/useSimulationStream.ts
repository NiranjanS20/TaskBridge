import { useEffect, useState } from 'react';
import { simulationStreamUrl } from '@/lib/api';

export interface SimulationStreamEvent {
  simulation_id: string;
  status: string;
  tasks_generated?: number;
  assignments_done?: number;
  queue_depth?: number;
  avg_latency?: number;
  error?: string;
}

export function useSimulationStream(simulationId: string | null) {
  const [event, setEvent] = useState<SimulationStreamEvent | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!simulationId) {
      setConnected(false);
      setEvent(null);
      return;
    }

    const source = new EventSource(simulationStreamUrl(simulationId));
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as SimulationStreamEvent;
        setEvent(parsed);
      } catch {
        // ignore malformed payloads
      }
    };
    return () => {
      source.close();
      setConnected(false);
    };
  }, [simulationId]);

  return { event, connected };
}
