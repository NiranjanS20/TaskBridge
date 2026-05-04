import { NavLink, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useAuth } from '@/providers/AuthProvider';

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/'); };
  const isAdmin = user?.role === 'NGO_ADMIN' || user?.role === 'NGO_MANAGER';

  return (
    <nav 
      aria-label="Sidebar" 
      className="h-screen w-64 fixed left-0 top-0 bg-surface-container-low flex flex-col py-8 px-4 gap-1 z-50 border-r border-transparent"
    >
      {/* Brand Header */}
      <div className="px-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-primary text-on-primary flex items-center justify-center font-bold text-lg">
            I
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tighter text-primary leading-none">
              TaskBridge
            </h1>
            <p className="font-sans font-medium text-xs tracking-tight text-on-background/70 mt-1">
              Operational Serenity
            </p>
          </div>
        </div>
      </div>

      {/* CTA Button */}
      <button className="mb-6 mx-2 py-2.5 px-4 rounded-lg bg-gradient-to-r from-primary to-primary-container text-on-primary font-medium text-sm shadow-[0_4px_16px_rgba(0,60,157,0.2)] hover:opacity-90 transition-opacity flex items-center justify-center gap-2">
        <span className="material-symbols-outlined text-[18px]">add</span>
        New Incident
      </button>

      {/* Navigation Links */}
      <div className="flex flex-col gap-1 flex-grow">
        <NavLink 
          to="/dashboard"
          className={({ isActive }) => cn(
            "flex items-center gap-3 rounded-lg px-4 py-2.5 font-bold transition-all duration-200",
            isActive 
              ? "bg-primary-fixed text-primary hover:bg-surface-container-high" 
              : "text-on-surface-variant hover:bg-surface-container-high/50"
          )}
        >
          <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
            dashboard
          </span>
          <span className="text-sm">Dashboard</span>
        </NavLink>
        
        <NavLink 
          to="/tasks"
          className={({ isActive }) => cn(
            "flex items-center gap-3 rounded-lg px-4 py-2.5 font-bold transition-all duration-200",
            isActive 
              ? "bg-primary-fixed text-primary hover:bg-surface-container-high" 
              : "text-on-surface-variant hover:bg-surface-container-high/50 font-medium"
          )}
        >
          <span className="material-symbols-outlined">task_alt</span>
          <span className="text-sm">Tasks</span>
        </NavLink>

        {isAdmin && (
          <NavLink 
            to="/volunteers"
            className={({ isActive }) => cn(
              "flex items-center gap-3 rounded-lg px-4 py-2.5 font-bold transition-all duration-200",
              isActive 
                ? "bg-primary-fixed text-primary hover:bg-surface-container-high" 
                : "text-on-surface-variant hover:bg-surface-container-high/50 font-medium"
            )}
          >
            <span className="material-symbols-outlined">group</span>
            <span className="text-sm">Volunteers</span>
          </NavLink>
        )}

        {isAdmin && (
          <NavLink 
            to="/simulate"
            className={({ isActive }) => cn(
              "flex items-center gap-3 rounded-lg px-4 py-2.5 font-bold transition-all duration-200",
              isActive 
                ? "bg-primary-fixed text-primary hover:bg-surface-container-high" 
                : "text-on-surface-variant hover:bg-surface-container-high/50 font-medium"
            )}
          >
            <span className="material-symbols-outlined">model_training</span>
            <span className="text-sm">Simulate</span>
          </NavLink>
        )}

        <NavLink 
          to="/dashboard/explain"
          className={({ isActive }) => cn(
            "flex items-center gap-3 rounded-lg px-4 py-2.5 font-bold transition-all duration-200",
            isActive 
              ? "bg-primary-fixed text-primary hover:bg-surface-container-high" 
              : "text-on-surface-variant hover:bg-surface-container-high/50 font-medium"
          )}
        >
          <span className="material-symbols-outlined">psychology</span>
          <span className="text-sm">Explain</span>
        </NavLink>

        {isAdmin && (
          <NavLink 
            to="/dashboard/analytics"
            className={({ isActive }) => cn(
              "flex items-center gap-3 rounded-lg px-4 py-2.5 font-bold transition-all duration-200",
              isActive 
                ? "bg-primary-fixed text-primary hover:bg-surface-container-high" 
                : "text-on-surface-variant hover:bg-surface-container-high/50 font-medium"
            )}
          >
            <span className="material-symbols-outlined">monitoring</span>
            <span className="text-sm">Analytics</span>
          </NavLink>
        )}
      </div>

      {/* Bottom User + Logout */}
      <div className="mt-auto space-y-1">
        {user && (
          <div className="px-4 py-2 mb-1">
            <p className="text-sm font-bold text-on-surface truncate">{user.full_name}</p>
            <p className="text-xs text-on-surface-variant capitalize">{user.role}</p>
          </div>
        )}
        <NavLink
          to="/profile"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200",
              isActive ? "bg-primary-fixed text-primary" : "text-on-surface-variant hover:bg-surface-container-high/50"
            )
          }
        >
          <span className="material-symbols-outlined">settings</span>
          <span className="text-sm font-medium">Settings</span>
        </NavLink>
        <button onClick={handleLogout} className="flex items-center gap-3 text-error px-4 py-2.5 hover:bg-error-container/30 rounded-lg transition-all duration-200 w-full">
          <span className="material-symbols-outlined">logout</span>
          <span className="text-sm font-medium">Sign Out</span>
        </button>
      </div>
    </nav>
  );
}
