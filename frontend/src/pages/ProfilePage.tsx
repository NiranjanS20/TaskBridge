import { useEffect, useMemo, useState } from 'react';

import { CardWrapper } from '@/components/ui/CardWrapper';
import { GridWrapper } from '@/components/layout/GridWrapper';
import { useAuth } from '@/providers/AuthProvider';

export function ProfilePage() {
  const { user, refreshProfile, updateProfile, isLoading } = useAuth();
  const [fullName, setFullName] = useState('');
  const [area, setArea] = useState('');
  const [ngoDescription, setNgoDescription] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    void refreshProfile();
  }, [refreshProfile]);

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name ?? '');
    setArea(user.area ?? '');
    setNgoDescription(user.ngo_description ?? '');
    setLatitude(user.latitude == null ? '' : String(user.latitude));
    setLongitude(user.longitude == null ? '' : String(user.longitude));
  }, [user]);

  const roleLabel = useMemo(() => {
    if (!user) return '';
    return user.role === 'VOLUNTEER' ? 'Volunteer' : user.role === 'NGO_ADMIN' ? 'NGO Admin' : 'NGO Manager';
  }, [user]);

  const save = async () => {
    setSaving(true);
    setError(null);
    setOk(null);
    try {
      const lat = latitude.trim() ? Number(latitude) : undefined;
      const lng = longitude.trim() ? Number(longitude) : undefined;
      if (latitude.trim() && !Number.isFinite(lat)) throw new Error('Latitude must be a valid number.');
      if (longitude.trim() && !Number.isFinite(lng)) throw new Error('Longitude must be a valid number.');

      await updateProfile({
        full_name: fullName.trim() || undefined,
        area: area.trim() || undefined,
        ngo_description: user?.role === 'VOLUNTEER' ? undefined : (ngoDescription.trim() || undefined),
        latitude: lat,
        longitude: lng,
      });
      setOk('Profile updated.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  if (isLoading && !user) {
    return <div className="text-on-surface-variant">Loading profile...</div>;
  }

  if (!user) {
    return <div className="text-on-surface-variant">No profile available.</div>;
  }

  return (
    <>
      <div className="mb-8">
        <p className="text-label text-sm uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">Profile</p>
        <h2 className="text-headline text-3xl font-bold tracking-tight text-on-surface">Settings</h2>
      </div>

      {(error || ok) && (
        <div className={`mb-6 px-4 py-3 rounded-lg text-sm ${error ? 'bg-error-container text-on-error-container' : 'bg-primary-fixed/30 text-primary'}`}>
          {error ?? ok}
        </div>
      )}

      <GridWrapper>
        <CardWrapper className="col-span-12 lg:col-span-4">
          <h3 className="font-semibold text-on-surface mb-3">Account</h3>
          <div className="space-y-2 text-sm text-on-surface-variant">
            <p><span className="font-semibold text-on-surface">Role:</span> {roleLabel}</p>
            <p><span className="font-semibold text-on-surface">Email:</span> {user.email}</p>
            <p><span className="font-semibold text-on-surface">NGO:</span> {user.ngo_name ?? '—'}</p>
            <p><span className="font-semibold text-on-surface">NGO Email:</span> {user.ngo_email ?? '—'}</p>
          </div>
        </CardWrapper>

        <CardWrapper className="col-span-12 lg:col-span-8">
          <h3 className="font-semibold text-on-surface mb-4">Edit Profile</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">Full Name</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">Area</label>
              <input value={area} onChange={(e) => setArea(e.target.value)} className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5" placeholder="Sector / region / notes" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">Latitude</label>
              <input value={latitude} onChange={(e) => setLatitude(e.target.value)} className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5" placeholder="12.9716" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">Longitude</label>
              <input value={longitude} onChange={(e) => setLongitude(e.target.value)} className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5" placeholder="77.5946" />
            </div>
            {user.role !== 'VOLUNTEER' && (
              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-on-surface mb-1">NGO Description</label>
                <textarea
                  value={ngoDescription}
                  onChange={(e) => setNgoDescription(e.target.value)}
                  className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5 min-h-28"
                />
              </div>
            )}
          </div>

          <div className="mt-5">
            <button
              onClick={() => void save()}
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-semibold disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </CardWrapper>
      </GridWrapper>
    </>
  );
}

