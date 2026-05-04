import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '@/providers/AuthProvider';

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading, authError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.');
      return;
    }

    try {
      const user = await login(email.trim(), password);
      if (user.role === 'VOLUNTEER') {
        navigate('/tasks');
      } else {
        navigate('/dashboard');
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unable to login';
      setError(message);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md bg-surface-container-lowest rounded-2xl border border-outline-variant/30 p-8 shadow-[0_20px_60px_rgba(0,0,0,0.08)]">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-lg bg-primary text-on-primary flex items-center justify-center font-bold text-xl">T</div>
          <span className="text-2xl font-bold tracking-tight text-primary">TASKBRIDGE</span>
        </div>

        <h1 className="text-3xl font-extrabold text-on-surface mb-2">Sign In</h1>
        <p className="text-on-surface-variant mb-8">Use your registered account to access live allocation dashboards.</p>

        {(error || authError) && (
          <div className="bg-error-container text-on-error-container px-4 py-3 rounded-lg text-sm mb-5">
            {error || authError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
              placeholder="name@ngo.org"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface border border-outline-variant/40 rounded-lg px-3 py-2.5"
              placeholder="Enter password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-primary text-on-primary rounded-lg font-semibold disabled:opacity-50"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-on-surface-variant">
          New to TASKBRIDGE?{' '}
          <Link to="/register" className="text-primary font-semibold hover:underline">
            Create account
          </Link>
        </p>
        <Link to="/" className="block text-center mt-3 text-xs text-on-surface-variant hover:text-primary">
          Back to landing page
        </Link>
      </div>
    </div>
  );
}
