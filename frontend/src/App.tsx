import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { TasksPage } from './pages/TasksPage';
import { VolunteersPage } from './pages/VolunteersPage';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { SimulationPage } from './pages/SimulationPage';
import { ExplainDashboardPage } from './pages/ExplainDashboardPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ProfilePage } from './pages/ProfilePage';
import { AppDataProvider } from './providers/AppDataProvider';
import { AuthProvider } from './providers/AuthProvider';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { NotificationsProvider, useNotifications } from './context/NotificationsContext';
import { setGlobalErrorHandler, ApiError } from './lib/api';

function GlobalErrorHandler() {
  const { push } = useNotifications();

  useEffect(() => {
    setGlobalErrorHandler((error: ApiError) => {
      push({
        title: error.isNetworkError ? 'Connection Error' : 'API Error',
        detail: error.message,
        level: error.isNetworkError ? 'critical' : 'warning',
      });
    });
  }, [push]);

  return null;
}

function App() {
  return (
    <NotificationsProvider>
      <GlobalErrorHandler />
      <AuthProvider>
        <AppDataProvider>
          <BrowserRouter>
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              {/* Protected Dashboard Routes */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <MainLayout>
                      <DashboardPage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/tasks"
                element={
                  <ProtectedRoute>
                    <MainLayout>
                      <TasksPage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/volunteers"
                element={
                  <ProtectedRoute allowedRoles={['NGO_ADMIN', 'NGO_MANAGER']}>
                    <MainLayout>
                      <VolunteersPage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/simulate"
                element={
                  <ProtectedRoute allowedRoles={['NGO_ADMIN', 'NGO_MANAGER']}>
                    <MainLayout>
                      <SimulationPage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/explain"
                element={
                  <ProtectedRoute>
                    <MainLayout>
                      <ExplainDashboardPage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/analytics"
                element={
                  <ProtectedRoute allowedRoles={['NGO_ADMIN', 'NGO_MANAGER']}>
                    <MainLayout>
                      <AnalyticsPage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analytics"
                element={
                  <ProtectedRoute allowedRoles={['NGO_ADMIN', 'NGO_MANAGER']}>
                    <MainLayout>
                      <AnalyticsPage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <MainLayout>
                      <ProfilePage />
                    </MainLayout>
                  </ProtectedRoute>
                }
              />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AppDataProvider>
      </AuthProvider>
    </NotificationsProvider>
  );
}

export default App;
