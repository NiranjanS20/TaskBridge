import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '@/providers/AuthProvider';

type RegisterMode = 'admin' | 'volunteer';

export function RegisterPage() {
  const navigate = useNavigate();
  const { registerAdmin, registerVolunteer, isLoading, authError } = useAuth();

  const [mode, setMode] = useState<RegisterMode>('admin');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [ngoName, setNgoName] = useState('');
  const [ngoEmail, setNgoEmail] = useState('');
  const [skillsRaw, setSkillsRaw] = useState('');
  const [password, setPassword] = useState('');
  const [latitude, setLatitude] = useState<number | undefined>(undefined);
  const [longitude, setLongitude] = useState<number | undefined>(undefined);
  const [area, setArea] = useState('');
  const [ngoDescription, setNgoDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [capturingLocation, setCapturingLocation] = useState(false);

  const captureLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported in this browser.');
      return;
    }
    setCapturingLocation(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        setLatitude(lat);
        setLongitude(lng);
        setArea(`${lat.toFixed(4)}, ${lng.toFixed(4)}`);
        setCapturingLocation(false);
      },
      () => {
        setError('Unable to get location. Please allow GPS permission or enter manually.');
        setCapturingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!fullName.trim() || !ngoName.trim() || !ngoEmail.trim() || !password.trim()) {
      setError('Please fill all required fields.');
      return;
    }

    try {
      if (mode === 'admin') {
        await registerAdmin({
          full_name: fullName.trim(),
          ngo_name: ngoName.trim(),
          ngo_email: ngoEmail.trim(),
          password,
          latitude,
          longitude,
          area: area || undefined,
          ngo_description: ngoDescription || undefined,
        });
        navigate('/dashboard');
        return;
      }

      if (!email.trim()) {
        setError('Volunteer email is required.');
        return;
      }

      const skills = skillsRaw
        .split(',')
        .map((skill) => skill.trim())
        .filter(Boolean);

      await registerVolunteer({
        full_name: fullName.trim(),
        email: email.trim(),
        ngo_name: ngoName.trim(),
        ngo_email: ngoEmail.trim(),
        skills,
        password,
        latitude,
        longitude,
        area: area || undefined,
      });
      navigate('/tasks');
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Registration failed';
      setError(message);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-2xl bg-surface-container-lowest rounded-2xl border border-outline-variant/30 p-8 shadow-[0_20px_60px_rgba(0,0,0,0.08)]">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-lg bg-primary text-on-primary flex items-center justify-center font-bold text-xl">T</div>
          <span className="text-2xl font-bold tracking-tight text-primary">TASKBRIDGE</span>
        </div>

        <h1 className="text-3xl font-extrabold text-on-surface mb-2">Create Account</h1>
        <p className="text-on-surface-variant mb-6">Register as NGO Admin or Volunteer with real organization mapping.</p>

        <div className="grid grid-cols-2 gap-2 p-1 bg-surface-container-high rounded-lg mb-6">
          <button
            type="button"
            onClick={() => setMode('admin')}
            className={`py-2 rounded-md text-sm font-semibold ${mode === 'admin' ? 'bg-primary text-on-primary' : 'text-on-surface-variant'}`}
          >
            NGO Admin
          </button>
          <button
            type="button"
            onClick={() => setMode('volunteer')}
            className={`py-2 rounded-md text-sm font-semibold ${mode === 'volunteer' ? 'bg-primary text-on-primary' : 'text-on-surface-variant'}`}
          >
            Volunteer
          </button>
        </div>

        {(error || authError) && (
          <div className="bg-error-container text-on-error-container px-4 py-3 rounded-lg text-sm mb-5">
            {error || authError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">Full Name</label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
                placeholder="Your full name"
              />
            </div>

            {mode === 'volunteer' && (
              <div>
                <label className="block text-sm font-semibold text-on-surface mb-1">Volunteer Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
                  placeholder="volunteer@ngo.org"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">NGO Name</label>
              <input
                value={ngoName}
                onChange={(e) => setNgoName(e.target.value)}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
                placeholder="Organization name"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">NGO Email</label>
              <input
                type="email"
                value={ngoEmail}
                onChange={(e) => setNgoEmail(e.target.value)}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
                placeholder="ngo@organization.org"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
                placeholder="Minimum 8 characters"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-on-surface mb-1">Area</label>
              <input
                value={area}
                onChange={(e) => setArea(e.target.value)}
                className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
                placeholder="Auto-filled from GPS or type manually"
              />
            </div>

            {mode === 'volunteer' && (
              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-on-surface mb-1">Skills (comma separated)</label>
                <input
                  value={skillsRaw}
                  onChange={(e) => setSkillsRaw(e.target.value)}
                  className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
                  placeholder="medical, logistics, triage"
                />
              </div>
            )}

            {mode === 'admin' && (
              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-on-surface mb-1">NGO Description</label>
                <textarea
                  value={ngoDescription}
                  onChange={(e) => setNgoDescription(e.target.value)}
                  className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5 min-h-24"
                  placeholder="Mission, operating region, and response scope"
                />
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={captureLocation}
              className="px-4 py-2 rounded-lg border border-outline-variant/40 text-sm font-semibold"
              disabled={capturingLocation}
            >
              {capturingLocation ? 'Getting GPS...' : 'Use GPS Location'}
            </button>
            {latitude !== undefined && longitude !== undefined && (
              <p className="text-xs text-on-surface-variant">
                Latitude: {latitude.toFixed(4)} | Longitude: {longitude.toFixed(4)}
              </p>
            )}
          </div>

          <button type="submit" disabled={isLoading} className="w-full py-3 bg-primary text-on-primary rounded-lg font-semibold disabled:opacity-50">
            {isLoading ? 'Creating account...' : mode === 'admin' ? 'Register NGO Admin' : 'Register Volunteer'}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-on-surface-variant">
          Already have an account?{' '}
          <Link to="/login" className="text-primary font-semibold hover:underline">
            Sign In
          </Link>
        </p>
        <Link to="/" className="block text-center mt-3 text-xs text-on-surface-variant hover:text-primary">
          Back to landing page
        </Link>
      </div>
    </div>
  );
}
