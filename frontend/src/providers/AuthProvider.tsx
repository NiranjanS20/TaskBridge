import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';

import { api, AuthResponse, getAuthToken, setAuthToken, UserProfile } from '@/lib/api';

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  authError: string | null;
  login: (email: string, password: string) => Promise<UserProfile>;
  registerAdmin: (payload: {
    full_name: string;
    ngo_name: string;
    ngo_email: string;
    password: string;
    latitude?: number;
    longitude?: number;
    area?: string;
    ngo_description?: string;
  }) => Promise<UserProfile>;
  registerVolunteer: (payload: {
    full_name: string;
    email: string;
    ngo_name: string;
    ngo_email: string;
    skills: string[];
    password: string;
    latitude?: number;
    longitude?: number;
    area?: string;
  }) => Promise<UserProfile>;
  updateProfile: (payload: Partial<Pick<UserProfile, 'full_name' | 'latitude' | 'longitude' | 'area' | 'ngo_description'>>) => Promise<UserProfile>;
  refreshProfile: () => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function applyAuthResponse(response: AuthResponse, setUser: (user: UserProfile) => void) {
  setAuthToken(response.access_token);
  setUser(response.user);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const bootstrap = async () => {
      const token = getAuthToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const me = await api.getMe();
        if (active) {
          setUser(me);
        }
      } catch {
        setAuthToken(null);
        if (active) {
          setUser(null);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    void bootstrap();
    return () => {
      active = false;
    };
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const response = await api.login(email, password);
      applyAuthResponse(response, setUser);
      return response.user;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      setAuthError(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const registerAdmin = async (payload: {
    full_name: string;
    ngo_name: string;
    ngo_email: string;
    password: string;
    latitude?: number;
    longitude?: number;
    area?: string;
    ngo_description?: string;
  }) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const response = await api.registerAdmin(payload);
      applyAuthResponse(response, setUser);
      return response.user;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Registration failed';
      setAuthError(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const registerVolunteer = async (payload: {
    full_name: string;
    email: string;
    ngo_name: string;
    ngo_email: string;
    skills: string[];
    password: string;
    latitude?: number;
    longitude?: number;
    area?: string;
  }) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const response = await api.registerVolunteer(payload);
      applyAuthResponse(response, setUser);
      return response.user;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Registration failed';
      setAuthError(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateProfile = async (payload: Partial<Pick<UserProfile, 'full_name' | 'latitude' | 'longitude' | 'area' | 'ngo_description'>>) => {
    const updated = await api.updateMe(payload);
    setUser(updated);
    return updated;
  };

  const refreshProfile = async () => {
    if (!getAuthToken()) {
      return;
    }
    try {
      const me = await api.getMe();
      setUser(me);
    } catch {
      setAuthToken(null);
      setUser(null);
    }
  };

  const logout = () => {
    setAuthToken(null);
    setUser(null);
    setAuthError(null);
  };

  const value = useMemo<AuthContextType>(
    () => ({
      user,
      isLoading,
      authError,
      login,
      registerAdmin,
      registerVolunteer,
      updateProfile,
      refreshProfile,
      logout,
      isAuthenticated: !!user,
    }),
    [authError, isLoading, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
