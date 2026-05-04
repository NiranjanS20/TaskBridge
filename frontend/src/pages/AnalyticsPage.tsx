import { useMemo } from 'react';

import { GridWrapper } from '@/components/layout/GridWrapper';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { Charts } from '@/components/analytics/Charts';
import { useAppData } from '@/providers/AppDataProvider';

export function AnalyticsPage() {
  const { analytics, status } = useAppData();

  const workload = useMemo(
    () =>
      Object.entries(analytics?.tasks_per_volunteer ?? {})
        .slice(0, 12)
        .map(([volunteerId, taskCount]) => ({ volunteer_id: volunteerId.slice(0, 8), tasks: taskCount })),
    [analytics?.tasks_per_volunteer]
  );

  if (status === 'loading') {
    return <div className="text-on-surface-variant">Loading analytics...</div>;
  }

  if (!analytics) {
    return <div className="text-on-surface-variant">No analytics data available yet.</div>;
  }

  return (
    <>
      <div className="mb-8">
        <p className="text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">Fairness & Performance</p>
        <h2 className="text-headline text-3xl font-bold tracking-tight text-on-surface">System Analytics</h2>
      </div>
      <GridWrapper>
        <CardWrapper className="col-span-12 lg:col-span-4">
          <p className="text-on-surface-variant text-sm">Total Tasks</p>
          <p className="text-3xl font-bold">{analytics.total_tasks}</p>
          <p className="text-xs text-on-surface-variant mt-2">Completed: {analytics.completed_tasks}</p>
        </CardWrapper>
        <CardWrapper className="col-span-12 lg:col-span-4">
          <p className="text-on-surface-variant text-sm">Avg Response Time</p>
          <p className="text-3xl font-bold">{analytics.avg_response_time}s</p>
          <p className="text-xs text-on-surface-variant mt-2">Queue latency: {analytics.queue_latency}s</p>
        </CardWrapper>
        <CardWrapper className="col-span-12 lg:col-span-4">
          <p className="text-on-surface-variant text-sm">Fairness (Gini)</p>
          <p className="text-3xl font-bold">{analytics.gini_coefficient}</p>
          <p className="text-xs text-on-surface-variant mt-2">
            Burnout avg: {Math.round((analytics.volunteer_health?.avg_burnout ?? 0) * 100)}%
          </p>
        </CardWrapper>
        <CardWrapper className="col-span-12 lg:col-span-4">
          <p className="text-on-surface-variant text-sm">Assignments Success Rate</p>
          <p className="text-3xl font-bold">{(analytics.assignment_success_rate * 100).toFixed(1)}%</p>
          <p className="text-xs text-on-surface-variant mt-2">In progress: {analytics.assignments_in_progress}</p>
        </CardWrapper>
        <Charts workload={workload} burnout={analytics.burnout_distribution ?? []} />
      </GridWrapper>
    </>
  );
}
