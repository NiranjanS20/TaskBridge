import { useMemo, useState } from 'react';

import { api } from '@/lib/api';
import { useAppData } from '@/providers/AppDataProvider';

interface TaskFormState {
  title: string;
  description: string;
  category: string;
  urgency: number;
  complexity: number;
  locationMode: 'gps' | 'manual';
  latitude: string;
  longitude: string;
  requiredSkills: string;
  teamSize: number;
  region: string;
}

const initialForm: TaskFormState = {
  title: '',
  description: '',
  category: 'general',
  urgency: 3,
  complexity: 5,
  locationMode: 'gps',
  latitude: '',
  longitude: '',
  requiredSkills: '',
  teamSize: 1,
  region: '',
};

export function TasksPage() {
  const { tasks, assignments, refresh, status, networkError } = useAppData();
  const [openForm, setOpenForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<TaskFormState>(initialForm);

  const assignmentMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const assignment of assignments) {
      map.set(assignment.task_id, (map.get(assignment.task_id) || 0) + 1);
    }
    return map;
  }, [assignments]);

  const captureGps = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by this browser.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((prev) => ({
          ...prev,
          latitude: position.coords.latitude.toString(),
          longitude: position.coords.longitude.toString(),
        }));
      },
      () => {
        setError('Unable to read current location. Enter coordinates manually.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!form.title.trim()) {
      setError('Task description/title is required.');
      return;
    }

    const latitude = Number(form.latitude);
    const longitude = Number(form.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      setError('Valid latitude and longitude are required.');
      return;
    }

    try {
      setSubmitting(true);
      await api.createTask({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        category: form.category.trim() || 'general',
        urgency: form.urgency,
        complexity: form.complexity,
        team_size: form.teamSize,
        latitude,
        longitude,
        region: form.region.trim() || undefined,
        required_skills: form.requiredSkills
          .split(',')
          .map((skill) => skill.trim())
          .filter(Boolean),
      });

      await api.runAllocationCycle();
      await refresh();
      setForm(initialForm);
      setOpenForm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Task creation failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="mb-8 flex justify-between items-end gap-4">
        <div>
          <p className="text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">Management</p>
          <h2 className="text-headline text-3xl font-bold tracking-tight text-on-surface">Active Tasks</h2>
        </div>
        <button
          onClick={() => {
            setOpenForm((prev) => !prev);
            setError(null);
            if (!openForm && form.locationMode === 'gps') {
              captureGps();
            }
          }}
          className="bg-primary hover:bg-primary-container text-on-primary px-4 py-2 rounded-lg font-bold text-sm"
        >
          {openForm ? 'Close Form' : 'Create Task'}
        </button>
      </div>

      {openForm && (
        <form onSubmit={onSubmit} className="mb-8 bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-5 space-y-4">
          {error && <p className="text-sm text-error">{error}</p>}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold mb-1">Description</label>
              <input
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
                placeholder="Medical support at flood shelter"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Category</label>
              <input
                value={form.category}
                onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
                placeholder="medical"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Urgency (1-5)</label>
              <input
                type="number"
                min={1}
                max={5}
                value={form.urgency}
                onChange={(e) => setForm((prev) => ({ ...prev, urgency: Number(e.target.value) }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Complexity (1-10)</label>
              <input
                type="number"
                min={1}
                max={10}
                value={form.complexity}
                onChange={(e) => setForm((prev) => ({ ...prev, complexity: Number(e.target.value) }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Required Skills</label>
              <input
                value={form.requiredSkills}
                onChange={(e) => setForm((prev) => ({ ...prev, requiredSkills: e.target.value }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
                placeholder="triage, logistics"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Team Size</label>
              <input
                type="number"
                min={1}
                max={50}
                value={form.teamSize}
                onChange={(e) => setForm((prev) => ({ ...prev, teamSize: Number(e.target.value) }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Region (optional)</label>
              <input
                value={form.region}
                onChange={(e) => setForm((prev) => ({ ...prev, region: e.target.value }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
                placeholder="sector_4"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Location Mode</label>
              <select
                value={form.locationMode}
                onChange={(e) => setForm((prev) => ({ ...prev, locationMode: e.target.value as 'gps' | 'manual' }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
              >
                <option value="gps">Use GPS</option>
                <option value="manual">Manual coordinates</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-semibold mb-1">Latitude</label>
              <input
                value={form.latitude}
                onChange={(e) => setForm((prev) => ({ ...prev, latitude: e.target.value }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
                placeholder="12.9716"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Longitude</label>
              <input
                value={form.longitude}
                onChange={(e) => setForm((prev) => ({ ...prev, longitude: e.target.value }))}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2"
                placeholder="77.5946"
              />
            </div>
            <div className="flex items-end">
              <button
                type="button"
                onClick={captureGps}
                className="w-full border border-outline-variant/40 rounded-lg px-3 py-2 text-sm font-semibold"
              >
                Use Current GPS
              </button>
            </div>
          </div>

          <button type="submit" disabled={submitting} className="px-4 py-2 rounded-lg bg-primary text-on-primary font-semibold">
            {submitting ? 'Creating...' : 'Submit Task'}
          </button>
        </form>
      )}

      {status === 'loading' && <p className="text-on-surface-variant">Loading tasks...</p>}

      {status === 'error' && networkError && (
        <div className="bg-error-container text-on-error-container rounded-xl border border-error/30 p-6 mb-4">
          <h3 className="font-bold text-on-error-container mb-2">Connection Error</h3>
          <p className="text-sm text-on-error-container mb-3">{networkError}</p>
          <button
            onClick={() => refresh()}
            className="px-3 py-1.5 bg-error text-on-error-container text-sm font-semibold rounded-lg"
          >
            Retry Connection
          </button>
        </div>
      )}

      {status !== 'loading' && tasks.length === 0 && !networkError && (
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">
          <h3 className="font-bold text-on-surface mb-2">No tasks yet</h3>
          <p className="text-sm text-on-surface-variant">Create your first task to trigger the allocation engine and notify volunteers in real time.</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {tasks.map((task) => (
          <div key={task.id} className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-on-surface">{task.title}</h3>
                <p className="text-sm text-on-surface-variant mt-1">{task.description || 'No description provided.'}</p>
              </div>
              <span className="text-xs uppercase px-2 py-1 rounded bg-primary-fixed text-primary">{task.status}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-on-surface-variant">
              <p>Category: {task.category}</p>
              <p>Urgency: {task.urgency}</p>
              <p>Team size: {task.team_size}</p>
              <p>Assignments: {assignmentMap.get(task.id) || 0}</p>
              <p>Location: {task.latitude.toFixed(3)}, {task.longitude.toFixed(3)}</p>
              <p>Skills: {task.required_skills.length ? task.required_skills.join(', ') : 'none'}</p>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
