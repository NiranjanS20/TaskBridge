import { useMemo, useState } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/providers/AuthProvider';

type ChatMessage = { id: string; role: 'user' | 'assistant'; content: string };

export function ChatWidget() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 'init', role: 'assistant', content: 'Ask me about tasks, predictions, explainability, or analytics.' },
  ]);

  const role = useMemo(() => user?.role ?? 'volunteer', [user?.role]);

  const send = async () => {
    if (!query.trim()) return;
    const text = query.trim();
    setQuery('');
    setMessages((prev) => [{ id: crypto.randomUUID(), role: 'user', content: text }, ...prev]);
    setLoading(true);
    try {
      const data = await api.chat(text);
      setMessages((prev) => [
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.answer ?? 'No response.',
        },
        ...prev,
      ]);
    } catch {
      setMessages((prev) => [
        { id: crypto.randomUUID(), role: 'assistant', content: 'Chat service is unavailable right now.' },
        ...prev,
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-[70]">
      {open && (
        <div className="w-[360px] max-h-[540px] bg-surface-container-low rounded-xl shadow-xl border border-surface-container-high mb-3 flex flex-col">
          <div className="px-4 py-3 border-b border-surface-container-high flex justify-between items-center">
            <div className="font-semibold text-on-surface">TaskBridge Assistant ({role})</div>
            <button onClick={() => setOpen(false)} className="text-on-surface-variant text-sm">Close</button>
          </div>
          <div className="p-3 space-y-2 overflow-y-auto flex-1">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`text-sm rounded-lg px-3 py-2 ${
                  m.role === 'assistant' ? 'bg-surface-container-high text-on-surface' : 'bg-primary text-on-primary'
                }`}
              >
                {m.content}
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-surface-container-high flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void send()}
              className="flex-1 rounded-lg bg-surface-container-high px-3 py-2 text-sm"
              placeholder="Ask AI..."
            />
            <button
              onClick={() => void send()}
              disabled={loading}
              className="px-3 py-2 rounded bg-primary text-on-primary text-sm"
            >
              {loading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      )}
      <button
        onClick={() => setOpen((v) => !v)}
        className="h-12 w-12 rounded-full bg-primary text-on-primary shadow-lg flex items-center justify-center"
      >
        AI
      </button>
    </div>
  );
}
