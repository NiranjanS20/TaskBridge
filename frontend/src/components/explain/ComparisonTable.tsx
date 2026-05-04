import { CardWrapper } from '@/components/ui/CardWrapper';

interface Alternative {
  volunteer_id: string;
  volunteer_name: string;
  vas_score: number;
  rejection_reason: string;
}

interface Props {
  reason: string;
  confidence: number;
  alternatives: Alternative[];
}

export function ComparisonTable({ reason, confidence, alternatives }: Props) {
  const confidenceLabel =
    confidence >= 0.75 ? 'High' : confidence >= 0.4 ? 'Medium' : 'Low';

  return (
    <CardWrapper className="col-span-12 lg:col-span-6 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-on-surface">Selection Comparison</h3>
        <span className="text-xs px-2 py-1 rounded bg-primary-container text-primary font-bold uppercase">
          Confidence {confidenceLabel}
        </span>
      </div>
      <p className="text-sm text-on-surface-variant">{reason}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-on-surface-variant border-b border-surface-container-high">
              <th className="py-2">Volunteer</th>
              <th className="py-2">VAS</th>
              <th className="py-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {alternatives.map((alternative) => (
              <tr key={`${alternative.volunteer_id}-${alternative.vas_score}`} className="border-b border-surface-container-high/40">
                <td className="py-2 text-on-surface">{alternative.volunteer_name}</td>
                <td className="py-2">{alternative.vas_score.toFixed(4)}</td>
                <td className="py-2 text-on-surface-variant">{alternative.rejection_reason}</td>
              </tr>
            ))}
            {alternatives.length === 0 && (
              <tr>
                <td className="py-3 text-on-surface-variant" colSpan={3}>
                  No alternatives recorded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </CardWrapper>
  );
}
