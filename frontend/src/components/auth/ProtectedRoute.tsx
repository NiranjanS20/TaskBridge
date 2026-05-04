import { Navigate } from 'react-router-dom';
import { useAuth } from '@/providers/AuthProvider';

interface Props {
  children: React.ReactNode;
  allowedRoles?: ('NGO_ADMIN' | 'NGO_MANAGER' | 'VOLUNTEER')[];
}

export function ProtectedRoute({ children, allowedRoles }: Props) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-background">
        <div className="w-10 h-10 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (allowedRoles && user && !allowedRoles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
