import { useMemo } from 'react';

import { useAppData } from '@/providers/AppDataProvider';

export function VolunteersPage() {
  const { volunteers, status, networkError, refresh } = useAppData();

  const deployed = useMemo(() => volunteers.filter((v) => v.status === 'deployed').length, [volunteers]);
  const highRisk = useMemo(() => volunteers.filter((v) => v.burnout_score >= 0.8).length, [volunteers]);

  return (
    <>
      <div className="mb-8 flex justify-between items-end">
        <div>
          <p className="text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">Personnel Module</p>
          <h2 className="text-headline text-3xl font-bold tracking-tight text-on-surface">NGO Volunteers</h2>
        </div>
        <div className="flex items-center gap-4 border border-outline-variant/30 bg-surface-container-highest px-4 py-2 rounded-lg">
          <div className="text-center px-4 border-r border-outline-variant/30">
            <p className="text-xs uppercase tracking-widest font-bold text-on-surface-variant">Deployed</p>
            <p className="font-extrabold text-tertiary-fixed text-xl">{deployed}</p>
          </div>
          <div className="text-center px-4">
            <p className="text-xs uppercase tracking-widest font-bold text-on-surface-variant">Burnout Risk</p>
            <p className="font-extrabold text-error text-xl">{highRisk}</p>
          </div>
        </div>
      </div>

      {status === 'loading' && <p className="text-on-surface-variant">Loading volunteers...</p>}

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

      {status !== 'loading' && volunteers.length === 0 && !networkError && (
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">
          <h3 className="font-bold text-on-surface mb-2">No volunteers available</h3>
          <p className="text-sm text-on-surface-variant">
            Register volunteers under this NGO to enable skill matching, burnout tracking, and fair assignment distribution.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {volunteers.map((volunteer) => (
          <div key={volunteer.id} className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-on-surface">{volunteer.name}</h3>
                <p className="text-sm text-on-surface-variant">{volunteer.email || 'No email provided'}</p>
              </div>
              <span className="text-xs uppercase px-2 py-1 rounded bg-primary-fixed text-primary">{volunteer.status}</span>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-on-surface-variant">
              <p>Availability: {(volunteer.availability * 100).toFixed(0)}%</p>
              <p>Reliability: {(volunteer.reliability * 100).toFixed(0)}%</p>
              <p>Burnout: {(volunteer.burnout_score * 100).toFixed(0)}%</p>
              <p>Active assignments: {volunteer.active_assignments}</p>
              <p>Total assignments: {volunteer.total_assignments}</p>
              <p>Area: {volunteer.area || 'unavailable'}</p>
              <p className="col-span-2">Skills: {volunteer.skills.length ? volunteer.skills.join(', ') : 'No skills tagged'}</p>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
