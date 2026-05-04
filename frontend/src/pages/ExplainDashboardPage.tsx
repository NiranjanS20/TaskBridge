import { useState } from 'react';

import { GridWrapper } from '@/components/layout/GridWrapper';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { ScoreBreakdown } from '@/components/explain/ScoreBreakdown';
import { ComparisonTable } from '@/components/explain/ComparisonTable';
import { api, ExplainResponse } from '@/lib/api';
import { useAppData } from '@/providers/AppDataProvider';

export function ExplainDashboardPage() {
  const { tasks, status } = useAppData();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [data, setData] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadExplainability = async (taskId: string) => {
    setSelectedTaskId(taskId);
    setLoading(true);
    setError(null);
    try {
      const response = await api.getExplainability(taskId);
      setData(response);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : 'Failed to load explainability');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="mb-8">
        <p className="text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">Explainability</p>
        <h2 className="text-headline text-3xl font-bold tracking-tight text-on-surface">Decision Intelligence</h2>
      </div>

      <GridWrapper>
        <CardWrapper className="col-span-12 lg:col-span-4">
          <h3 className="font-semibold text-on-surface mb-3">Tasks</h3>
          {status === 'loading' && <p className="text-sm text-on-surface-variant">Loading tasks...</p>}
          {status !== 'loading' && tasks.length === 0 && (
            <p className="text-sm text-on-surface-variant">No tasks available for explainability.</p>
          )}
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {tasks.map((task) => (
              <button
                key={task.id}
                onClick={() => void loadExplainability(task.id)}
                className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
                  selectedTaskId === task.id ? 'border-primary bg-primary-fixed/30' : 'border-outline-variant/30 hover:bg-surface-container-high'
                }`}
              >
                <p className="font-semibold text-sm text-on-surface">{task.title}</p>
                <p className="text-xs text-on-surface-variant">{task.status} | urgency {task.urgency}</p>
              </button>
            ))}
          </div>
        </CardWrapper>

        <CardWrapper className="col-span-12 lg:col-span-8">
          {loading && <p className="text-sm text-on-surface-variant">Loading explainability...</p>}
          {error && <p className="text-sm text-error">{error}</p>}
          {!loading && !error && !data && (
            <p className="text-sm text-on-surface-variant">Select a task to inspect VAS reasoning and alternatives.</p>
          )}
          {data && (
            <div className="space-y-4">
              <p className="text-sm text-on-surface-variant">
                Assigned volunteer: <span className="font-semibold text-on-surface">{data.chosen_volunteer_name || 'Unassigned'}</span>
              </p>
              <p className="text-sm text-on-surface-variant">
                VAS score: <span className="font-semibold text-on-surface">{data.factors?.final_vas_score?.toFixed(4) ?? 'N/A'}</span>
              </p>
              <ScoreBreakdown factors={data.factors} />
              <ComparisonTable reason={data.reason} confidence={data.confidence} alternatives={data.alternatives} />
            </div>
          )}
        </CardWrapper>
      </GridWrapper>
    </>
  );
}
