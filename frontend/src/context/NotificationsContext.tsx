import { createContext, ReactNode, useContext, useMemo, useState } from 'react';

export type NotificationItem = {
  id: string;
  createdAt: string;
  title: string;
  detail?: string;
  level: 'info' | 'warning' | 'critical';
  event?: string;
};

type NotificationsContextValue = {
  notifications: NotificationItem[];
  unreadCount: number;
  push: (n: Omit<NotificationItem, 'id' | 'createdAt'> & { id?: string; createdAt?: string }) => void;
  markAllRead: () => void;
  clear: () => void;
};

const NotificationsContext = createContext<NotificationsContextValue | undefined>(undefined);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const push: NotificationsContextValue['push'] = (n) => {
    const item: NotificationItem = {
      id: n.id ?? crypto.randomUUID(),
      createdAt: n.createdAt ?? new Date().toISOString(),
      title: n.title,
      detail: n.detail,
      level: n.level,
      event: n.event,
    };
    setNotifications((prev) => [item, ...prev].slice(0, 50));
    setUnreadCount((c) => Math.min(50, c + 1));
  };

  const markAllRead = () => setUnreadCount(0);
  const clear = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  const value = useMemo<NotificationsContextValue>(
    () => ({ notifications, unreadCount, push, markAllRead, clear }),
    [notifications, unreadCount]
  );

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (!ctx) {
    throw new Error('useNotifications must be used within NotificationsProvider');
  }
  return ctx;
}

