import { useMemo } from 'react';

import { GridWrapper } from '@/components/layout/GridWrapper';
import { MetricsRow } from '@/components/modules/MetricsRow';
import { MapModule } from '@/components/modules/MapModule';
import { ActivityFeed } from '@/components/modules/ActivityFeedModule';
import { VASPanel } from '@/components/modules/VASPanel';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { MapView } from '@/components/map/MapView';
import { useAppData } from '@/providers/AppDataProvider';

export function DashboardPage() {
  const {
    events,
    vasMetrics,
    status,
    analytics,
    wsConnected,
    tasks,
    volunteers,
    assignments,
  } = useAppData();

  const heatPoints = useMemo(
    () =>
      (analytics?.burnout_distribution ?? []).map((item, index) => ({
        latitude: (volunteers[index]?.latitude ?? 0),
        longitude: (volunteers[index]?.longitude ?? 0),
        risk_score: item.burnout_score,
      })),
    [analytics?.burnout_distribution, volunteers]
  );

  const lines = useMemo(() => {
    const taskMap = new Map(tasks.map((task) => [task.id, task]));
    const volunteerMap = new Map(volunteers.map((volunteer) => [volunteer.id, volunteer]));

    return assignments
      .map((assignment) => {
        const task = taskMap.get(assignment.task_id);
        const volunteer = volunteerMap.get(assignment.volunteer_id);
        if (!task || !volunteer) {
          return null;
        }

        return {
          task_id: assignment.task_id,
          volunteer_id: assignment.volunteer_id,
          from: [volunteer.latitude, volunteer.longitude] as [number, number],
          to: [task.latitude, task.longitude] as [number, number],
        };
      })
      .filter((line): line is NonNullable<typeof line> => line !== null);
  }, [assignments, tasks, volunteers]);

  const noData = status !== 'loading' && tasks.length === 0 && volunteers.length === 0;

  return (
    <>
      <div className="mb-8 flex justify-between items-end">
        <div>
          <p className="text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">Live Overview</p>
          <h2 className="text-headline text-3xl font-bold tracking-tight text-on-surface">TASKBRIDGE Operations</h2>
        </div>
        <div className="flex items-center gap-2 text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant">
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-tertiary-container animate-pulse' : 'bg-outline-variant'}`} />
          API {status} / WS {wsConnected ? 'connected' : 'offline'}
        </div>
      </div>

      <div className="mb-6">
        <MetricsRow />
      </div>

      {noData ? (
        <CardWrapper className="col-span-12">
          <h3 className="text-xl font-bold text-on-surface mb-2">No operational data yet</h3>
          <p className="text-on-surface-variant text-sm">
            Create your first task and onboard volunteers to activate real-time allocation, explainability, and analytics.
          </p>
        </CardWrapper>
      ) : (
        <GridWrapper>
          <MapModule>
            <MapView tasks={tasks} volunteers={volunteers} heat={heatPoints} lines={lines} />
          </MapModule>

          <ActivityFeed.Root>
            {events.length === 0 && <p className="text-sm text-on-surface-variant">No activity yet.</p>}
            {events.map((event) => {
              let icon = 'info';
              let iconColorClass = 'text-primary';
              let iconBgClass = 'bg-primary-container';

              if (event.type === 'critical') {
                icon = 'warning';
                iconColorClass = 'text-error';
                iconBgClass = 'bg-error-container';
              } else if (event.type === 'ai_allocation') {
                icon = 'smart_toy';
                iconColorClass = 'text-tertiary';
                iconBgClass = 'bg-tertiary-fixed-dim/30';
              }

              return (
                <ActivityFeed.Item
                  key={event.id}
                  icon={icon}
                  iconColorClass={iconColorClass}
                  iconBgClass={iconBgClass}
                  title={event.title}
                  timestamp={event.timestamp}
                />
              );
            })}
          </ActivityFeed.Root>

          {vasMetrics && (
            <VASPanel.Root>
              <VASPanel.Header
                title="AI Volunteer Allocation"
                subtitle="VAS performance metrics"
                efficiencyScore={vasMetrics.efficiencyScore}
              />
              <VASPanel.MetricsGrid>
                <VASPanel.Metric label="Time to Deploy" value={vasMetrics.timeToDeployMinutes} unit="m" valueColorClass="text-primary" />
                <VASPanel.Metric label="Match Accuracy" value={vasMetrics.matchAccuracyPercentage} unit="%" />
                <VASPanel.Metric label="Active Routes" value={vasMetrics.activeRoutesCount} />
              </VASPanel.MetricsGrid>
            </VASPanel.Root>
          )}

          <CardWrapper className="col-span-12 lg:col-span-4">
            <h3 className="font-semibold text-on-surface mb-3">Insights</h3>
            <p className="text-sm text-on-surface-variant">Total tasks: {analytics?.total_tasks ?? 0}</p>
            <p className="text-sm text-on-surface-variant">Completed tasks: {analytics?.completed_tasks ?? 0}</p>
            <p className="text-sm text-on-surface-variant">Assignments in progress: {analytics?.assignments_in_progress ?? 0}</p>
            <p className="text-sm text-on-surface-variant">Fairness (Gini): {analytics?.gini_coefficient ?? 0}</p>
            <p className="text-sm text-on-surface-variant">Avg response time: {analytics?.avg_response_time ?? 0}s</p>
          </CardWrapper>
        </GridWrapper>
      )}
    </>
  );
}
