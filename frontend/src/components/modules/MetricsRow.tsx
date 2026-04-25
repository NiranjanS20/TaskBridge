import { MetricCard } from './MetricCard';
import { useAppData } from '@/providers/AppDataProvider';

export function MetricsRow() {
  const { metrics } = useAppData();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      {metrics.map((m) => {
        const isTask = m.category === 'task';
        const isVolunteer = m.category === 'volunteer';
        const isError = m.category === 'alert';

        const icon = isTask ? 'task' : isVolunteer ? 'group' : 'warning';
        const color = isTask ? 'text-primary' : isVolunteer ? 'text-secondary' : '';
        const title = isTask ? 'Total Tasks' : isVolunteer ? 'Total Volunteers' : 'Active Alerts';
        const pLabel = isTask ? 'Active' : isVolunteer ? 'Deployed' : 'Critical';
        const sLabel = isTask ? 'Pending' : isVolunteer ? 'Standby' : 'Warnings';

        return (
          <MetricCard 
            key={m.id}
            title={title}
            icon={icon}
            iconColorClass={color}
            mainValue={m.mainValue}
            primarySubValue={m.primarySubValue}
            primarySubLabel={pLabel}
            primarySubColorClass={color}
            secondarySubValue={m.secondarySubValue}
            secondarySubLabel={sLabel}
            variant={isError ? 'error' : 'default'}
          />
        );
      })}
    </div>
  );
}
