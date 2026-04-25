import { useEffect, useRef, useState } from 'react';
import { useNotifications } from '@/context/NotificationsContext';

export function TopNavbar() {
  const { notifications, unreadCount, markAllRead, clear } = useNotifications();
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!open) return;
      const target = e.target as Node | null;
      if (target && wrapperRef.current && !wrapperRef.current.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  return (
    <header className="fixed top-0 right-0 w-[calc(100%-16rem)] h-16 bg-surface-container-lowest/80 backdrop-blur-xl flex items-center justify-between px-8 z-40 ml-64 shadow-[0_4px_24px_rgba(11,28,48,0.05)]">
      {/* Search Bar (on_left) */}
      <div className="flex-1 max-w-md relative">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
          search
        </span>
        <input 
          type="text" 
          placeholder="Search incidents, volunteers, tasks..."
          className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary rounded-t-lg pl-10 pr-4 py-2 text-sm text-on-surface placeholder-on-surface-variant focus:ring-0 focus:ring-opacity-0 transition-all focus-within:ring-2 focus-within:ring-primary-container focus-within:ring-opacity-20"
        />
      </div>

      {/* Trailing Actions */}
      <div className="flex items-center gap-4">
        <div className="relative" ref={wrapperRef}>
          <button
            onClick={() => {
              setOpen((v) => !v);
              if (!open) markAllRead();
            }}
            className="p-2 rounded-full text-on-surface-variant hover:text-primary hover:bg-surface-container-high transition-all duration-200 active:scale-95 relative"
            aria-label="Notifications"
          >
            <span className="material-symbols-outlined">notifications</span>
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-5 h-5 px-1 bg-error text-on-error-container rounded-full text-[11px] font-bold flex items-center justify-center">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {open && (
            <div className="absolute right-0 mt-3 w-[360px] bg-surface-container-lowest border border-outline-variant/30 rounded-xl shadow-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-outline-variant/20 flex items-center justify-between">
                <p className="font-semibold text-on-surface">Notifications</p>
                <div className="flex items-center gap-2">
                  <button onClick={clear} className="text-xs font-semibold text-on-surface-variant hover:text-primary">
                    Clear
                  </button>
                  <button onClick={() => setOpen(false)} className="text-xs font-semibold text-on-surface-variant hover:text-primary">
                    Close
                  </button>
                </div>
              </div>
              <div className="max-h-[420px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="px-4 py-10 text-sm text-on-surface-variant">No alerts yet.</div>
                ) : (
                  notifications.map((n) => (
                    <div key={n.id} className="px-4 py-3 border-b border-outline-variant/10">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-on-surface">{n.title}</p>
                          {n.detail && <p className="text-xs text-on-surface-variant mt-1 line-clamp-2">{n.detail}</p>}
                          <p className="text-[11px] text-on-surface-variant mt-2">{new Date(n.createdAt).toLocaleString()}</p>
                        </div>
                        <span
                          className={`text-[11px] font-bold uppercase px-2 py-1 rounded ${
                            n.level === 'critical'
                              ? 'bg-error-container text-on-error-container'
                              : n.level === 'warning'
                                ? 'bg-tertiary-fixed/30 text-tertiary'
                                : 'bg-primary-fixed/30 text-primary'
                          }`}
                        >
                          {n.level}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
        
        <button className="p-2 rounded-full text-on-surface-variant hover:text-primary hover:bg-surface-container-high transition-all duration-200 active:scale-95">
          <span className="material-symbols-outlined">auto_awesome</span>
        </button>
        
        <button className="flex items-center gap-2 group">
          <img 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuCwoCiEWzPiWi4fID3pSvTpzmPPexTw0Ju7VuWHxFvZ7MlH0pzf4tvJ_VamsTc0vTTCOSymXfHcO09xrYX8iLsiZHq3oLKpGGtHJT2xO4r2tMALyoZKu4aTOciodlYlPqfUCK7tk0OJ5LJOjhxBOrFe-tnrmnsVmKgzPEwKMPZkPb9qCX87GH6rFa2_iJDmgmdgMEkOOtNO3Sa1BbkspmFY1b6Q-w789ktZIG9rETpkACsWNIU7VlW3oi9JqbIZAzS5M6yM_m3mcU4y" 
            alt="User profile" 
            className="w-8 h-8 rounded-full border border-outline-variant/30 group-hover:border-primary transition-colors"
          />
        </button>
      </div>
    </header>
  );
}
