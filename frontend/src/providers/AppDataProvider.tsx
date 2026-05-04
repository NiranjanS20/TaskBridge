import React, { createContext, useContext, ReactNode, useEffect, useMemo, useState, useRef } from 'react';

import { AnalyticsOverview, api, AssignmentRecord, TaskRecord, UserRole, VolunteerRecord } from '@/lib/api';
import { useAuth } from '@/providers/AuthProvider';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useNotifications } from '@/context/NotificationsContext';

export interface MetricData {
  id: string;
  category: 'task' | 'volunteer' | 'alert';
  mainValue: string | number;
  primarySubValue: string | number;
  secondarySubValue: string | number;
}

export interface ActivityEvent {
  id: string;
  type: 'critical' | 'ai_allocation' | 'system' | 'standard';
  title: React.ReactNode;
  timestamp: string;
}

export interface MapMarkerData {
  id: string;
  latitude: number;
  longitude: number;
  variant: 'task' | 'volunteer';
}

export interface VASMetrics {
  efficiencyScore: number;
  timeToDeployMinutes: number;
  matchAccuracyPercentage: number;
  activeRoutesCount: number;
}

export interface UrgencyData {
  critical: number;
  urgent: number;
  standard: number;
  low: number;
}

interface AppContextType {
  metrics: MetricData[];
  events: ActivityEvent[];
  markers: MapMarkerData[];
  vasMetrics: VASMetrics | null;
  urgency: UrgencyData | null;
  analytics: AnalyticsOverview | null;
  tasks: TaskRecord[];
  volunteers: VolunteerRecord[];
  assignments: AssignmentRecord[];
  wsConnected: boolean;
  status: string;
  refresh: () => Promise<void>;
  networkError: string | null;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppDataProvider({ children }: { children: ReactNode }) {
  const { user, isAuthenticated } = useAuth();
  const { push: pushNotification } = useNotifications();
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [volunteers, setVolunteers] = useState<VolunteerRecord[]>([]);
  const [assignments, setAssignments] = useState<AssignmentRecord[]>([]);
  const [status, setStatus] = useState<string>('idle');
  const [networkError, setNetworkError] = useState<string | null>(null);
  const isRefreshingRef = useRef(false);
  const lastRefreshRef = useRef<number>(0);
  const REFRESH_COOLDOWN_MS = 5000;

  const { connected: wsConnected, events: wsEvents } = useWebSocket({
    role: (user?.role ?? 'VOLUNTEER') as UserRole,
    userId: user?.id,
  });

  const refresh = async () => {
    const now = Date.now();
    if (isRefreshingRef.current || now - lastRefreshRef.current < REFRESH_COOLDOWN_MS) {
      return;
    }

    if (!isAuthenticated) {
      setAnalytics(null);
      setTasks([]);
      setVolunteers([]);
      setAssignments([]);
      setStatus('idle');
      return;
    }

    isRefreshingRef.current = true;
    setStatus('loading');
    try {
      const isAdmin = user?.role === 'NGO_ADMIN' || user?.role === 'NGO_MANAGER';

      const [overviewRes, tasksRes, volunteersRes, assignmentsRes] = await Promise.allSettled([
        api.getAnalyticsOverview(),
        api.getTasks(),
        isAdmin ? api.getVolunteers() : Promise.resolve({ volunteers: [], total: 0, page: 1, page_size: 0 }),
        api.getAssignments(),
      ]);

      const overview = overviewRes.status === 'fulfilled' ? overviewRes.value : null;
      const taskRes = tasksRes.status === 'fulfilled' ? tasksRes.value : { tasks: [], total: 0, page: 1, page_size: 50 };
      const volunteerRes =
        volunteersRes.status === 'fulfilled'
          ? volunteersRes.value
          : { volunteers: [], total: 0, page: 1, page_size: 50 };
      const assignmentRes = assignmentsRes.status === 'fulfilled' ? assignmentsRes.value : [];

      setAnalytics(overview);
      setTasks(taskRes.tasks);
      setVolunteers(volunteerRes.volunteers);
      setAssignments(assignmentRes);
      lastRefreshRef.current = Date.now();
      setStatus('connected');
      setNetworkError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch data';
      setStatus('error');
      setNetworkError(message);
    } finally {
      isRefreshingRef.current = false;
    }
  };

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setInterval> | null = null;

    const run = async () => {
      if (!active) return;
      await refresh();
    };

    if (isAuthenticated && user?.role) {
      void run();
      timer = setInterval(() => {
        if (active) {
          void run();
        }
      }, 15000);
    }

    return () => {
      active = false;
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [isAuthenticated, user?.role]);

  useEffect(() => {
    if (!wsEvents.length) {
      return;
    }

    const IGNORE_EVENTS = ['ping', 'pong', 'health', 'heartbeat'];
    const latest = wsEvents[0];
    if (!latest) return;

    const eventName = latest.event ?? 'event';
    if (IGNORE_EVENTS.includes(eventName.toLowerCase())) return;

    const normalized = eventName.toLowerCase();
    const level =
      normalized.includes('alert') || normalized.includes('critical')
        ? ('critical' as const)
        : normalized.includes('assignment')
          ? ('warning' as const)
          : ('info' as const);

    pushNotification({
      title: eventName,
      detail: latest.payload ? JSON.stringify(latest.payload) : undefined,
      level,
      event: eventName,
    });
  }, [pushNotification, wsEvents]);

  const markers = useMemo(
    () => [
      ...tasks.map((t) => ({ id: `task-${t.id}`, latitude: t.latitude, longitude: t.longitude, variant: 'task' as const })),
      ...volunteers.map((v) => ({ id: `vol-${v.id}`, latitude: v.latitude, longitude: v.longitude, variant: 'volunteer' as const })),
    ],
    [tasks, volunteers]
  );

  const metrics: MetricData[] = useMemo(() => {
    if (!analytics) {
      return [
        { id: 'tasks', category: 'task', mainValue: 0, primarySubValue: 0, secondarySubValue: 0 },
        { id: 'volunteers', category: 'volunteer', mainValue: 0, primarySubValue: 0, secondarySubValue: 0 },
        { id: 'alerts', category: 'alert', mainValue: 0, primarySubValue: 0, secondarySubValue: 0 },
      ];
    }

    const criticalTasks = tasks.filter((task) => task.urgency >= 5).length;
    const deployedVolunteers = volunteers.filter((volunteer) => volunteer.status === 'deployed').length;
    const highBurnout = volunteers.filter((volunteer) => volunteer.burnout_score >= 0.8).length;

    return [
      {
        id: 'tasks',
        category: 'task',
        mainValue: analytics.total_tasks,
        primarySubValue: analytics.total_active_tasks,
        secondarySubValue: analytics.completed_tasks,
      },
      {
        id: 'volunteers',
        category: 'volunteer',
        mainValue: volunteers.length,
        primarySubValue: deployedVolunteers,
        secondarySubValue: analytics.volunteers_available,
      },
      {
        id: 'alerts',
        category: 'alert',
        mainValue: criticalTasks,
        primarySubValue: highBurnout,
        secondarySubValue: analytics.assignments_in_progress,
      },
    ];
  }, [analytics, tasks, volunteers]);

  const urgency = useMemo<UrgencyData | null>(() => {
    if (!tasks.length) {
      return null;
    }
    return {
      critical: tasks.filter((task) => task.urgency >= 5).length,
      urgent: tasks.filter((task) => task.urgency === 4).length,
      standard: tasks.filter((task) => task.urgency === 3).length,
      low: tasks.filter((task) => task.urgency <= 2).length,
    };
  }, [tasks]);

  const events: ActivityEvent[] = useMemo(() => {
    const baseEvents = (analytics?.recent_activity ?? []).map((item) => ({
      id: item.id,
      type: item.type === 'assignment_done' ? ('ai_allocation' as const) : ('system' as const),
      title: item.message,
      timestamp: new Date(item.created_at).toLocaleTimeString(),
    }));

    const liveEvents = wsEvents.map((event, index) => ({
      id: `ws-${index}-${event.event}`,
      type: event.event.includes('TASK') ? ('critical' as const) : ('ai_allocation' as const),
      title: `${event.event}`,
      timestamp: 'now',
    }));

    return [...liveEvents, ...baseEvents].slice(0, 20);
  }, [analytics?.recent_activity, wsEvents]);

  const vasMetrics = useMemo<VASMetrics | null>(() => {
    if (!analytics) {
      return null;
    }

    return {
      efficiencyScore: Math.round(analytics.assignment_success_rate * 100),
      timeToDeployMinutes: Math.round((analytics.queue_latency || 0) / 60),
      matchAccuracyPercentage: Number((analytics.assignment_success_rate * 100).toFixed(2)),
      activeRoutesCount: analytics.assignments_in_progress,
    };
  }, [analytics]);

  const value = {
    metrics,
    events,
    markers,
    vasMetrics,
    urgency,
    analytics,
    tasks,
    volunteers,
    assignments,
    wsConnected,
    status,
    refresh,
    networkError,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppData() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppData must be used within an AppDataProvider');
  }
  return context;
}
