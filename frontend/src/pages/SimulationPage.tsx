import { useState } from 'react';

import { api, AssignmentRecord } from '@/lib/api';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { GridWrapper } from '@/components/layout/GridWrapper';

export function SimulationPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    assignments_created: number;
    assignments_reassigned: number;
    tasks_unmatched: number;
    cycle_duration_ms: number;
    details: AssignmentRecord[];
  } | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runAllocationCycle();
      setResult(res);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">Simulation</p>
          <h2 className="text-headline text-3xl font-bold tracking-tight text-on-surface">Allocation Cycle Runner</h2>
        </div>
        <button
          onClick={() => void run()}
          disabled={loading}
          className="bg-primary hover:bg-primary-container text-on-primary px-4 py-2 rounded-lg font-bold text-sm disabled:opacity-50"
        >
          {loading ? 'Running...' : 'Run Allocation'}
        </button>
      </div>

      {error && (
        <div className="mb-6 bg-error-container text-on-error-container px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {!result && !loading && !error && (
        <CardWrapper className="col-span-12">
          <h3 className="text-xl font-bold text-on-surface mb-2">No run yet</h3>
          <p className="text-sm text-on-surface-variant">
            Start a new allocation cycle to generate assignments from current pending tasks and available volunteers.
          </p>
        </CardWrapper>
      )}

      {result && (
        <GridWrapper>
          <CardWrapper className="col-span-12 lg:col-span-3">
            <p className="text-on-surface-variant text-sm">Assignments Created</p>
            <p className="text-3xl font-bold text-on-surface">{result.assignments_created}</p>
          </CardWrapper>
          <CardWrapper className="col-span-12 lg:col-span-3">
            <p className="text-on-surface-variant text-sm">Unmatched Tasks</p>
            <p className="text-3xl font-bold text-on-surface">{result.tasks_unmatched}</p>
          </CardWrapper>
          <CardWrapper className="col-span-12 lg:col-span-3">
            <p className="text-on-surface-variant text-sm">Reassigned</p>
            <p className="text-3xl font-bold text-on-surface">{result.assignments_reassigned}</p>
          </CardWrapper>
          <CardWrapper className="col-span-12 lg:col-span-3">
            <p className="text-on-surface-variant text-sm">Cycle Duration</p>
            <p className="text-3xl font-bold text-on-surface">{Math.round(result.cycle_duration_ms)}ms</p>
          </CardWrapper>

          <CardWrapper className="col-span-12">
            <h3 className="font-semibold text-on-surface mb-3">Assignments</h3>
            {result.details.length === 0 ? (
              <p className="text-sm text-on-surface-variant">No assignments were generated in this run.</p>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {result.details.map((a) => (
                  <div key={a.id} className="rounded-lg border border-outline-variant/30 bg-surface px-4 py-3">
                    <p className="text-sm font-semibold text-on-surface">Task: {a.task_id}</p>
                    <p className="text-xs text-on-surface-variant mt-1">Volunteer: {a.volunteer_id}</p>
                    <div className="mt-2 flex items-center justify-between gap-3">
                      <span className="text-[11px] uppercase px-2 py-1 rounded bg-primary-fixed/30 text-primary">{a.status}</span>
                      <span className="text-xs text-on-surface-variant">VAS: {a.vas_score.toFixed(4)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardWrapper>
        </GridWrapper>
      )}
    </>
  );
}

