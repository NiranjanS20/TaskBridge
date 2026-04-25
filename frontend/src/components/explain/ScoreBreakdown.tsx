import { CardWrapper } from '@/components/ui/CardWrapper';

interface Props {
  factors: {
    skill_match: number;
    proximity: number;
    reliability: number;
    availability: number;
    burnout_adjustment: number;
    volunteer_fit: number;
    final_vas_score: number;
  } | null;
}

const LABELS: Array<{ key: keyof NonNullable<Props['factors']>; label: string }> = [
  { key: 'skill_match', label: 'Skill Match' },
  { key: 'proximity', label: 'Proximity' },
  { key: 'reliability', label: 'Reliability' },
  { key: 'availability', label: 'Availability' },
  { key: 'burnout_adjustment', label: 'Burnout Adjustment' },
  { key: 'volunteer_fit', label: 'Volunteer Fit' },
  { key: 'final_vas_score', label: 'Final VAS' },
];

export function ScoreBreakdown({ factors }: Props) {
  if (!factors) {
    return <CardWrapper className="col-span-12">No scoring factors available.</CardWrapper>;
  }

  return (
    <CardWrapper className="col-span-12 lg:col-span-6 space-y-3">
      <h3 className="text-lg font-semibold text-on-surface">Factor Breakdown</h3>
      {LABELS.map(({ key, label }) => {
        const value = Math.max(0, Math.min(1, Number(factors[key] ?? 0)));
        return (
          <div key={key} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-on-surface-variant">{label}</span>
              <span className="font-semibold text-on-surface">{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-surface-container-high rounded">
              <div className="h-2 bg-primary rounded" style={{ width: `${value * 100}%` }} />
            </div>
          </div>
        );
      })}
    </CardWrapper>
  );
}
