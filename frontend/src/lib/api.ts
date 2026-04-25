function normalizeApiBase(raw: string): { origin: string; apiBase: string } {
  const trimmed = (raw || '').trim().replace(/\/+$/, '');
  const fallbackOrigin = 'http://127.0.0.1:8002';
  const base = trimmed || fallbackOrigin;

  if (base.endsWith('/api/v1')) {
    return { origin: base.slice(0, -'/api/v1'.length), apiBase: base };
  }

  if (base.startsWith('http://') || base.startsWith('https://')) {
    return { origin: base, apiBase: `${base}/api/v1` };
  }

  return { origin: fallbackOrigin, apiBase: `${fallbackOrigin}/api/v1` };
}

const { origin: API_ORIGIN, apiBase: API_BASE } = normalizeApiBase(import.meta.env.VITE_API_BASE_URL ?? '');
export { API_BASE, API_ORIGIN };

let authToken: string | null = localStorage.getItem('taskbridge_token');

export type UserRole = 'NGO_ADMIN' | 'NGO_MANAGER' | 'VOLUNTEER';

export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  ngo_id: string | null;
  ngo_name: string | null;
  ngo_email: string | null;
  ngo_description: string | null;
  latitude: number | null;
  longitude: number | null;
  area: string | null;
  skills: string[];
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface AdminRegisterPayload {
  full_name: string;
  ngo_name: string;
  ngo_email: string;
  password: string;
  latitude?: number;
  longitude?: number;
  area?: string;
  ngo_description?: string;
}

export interface VolunteerRegisterPayload {
  full_name: string;
  email: string;
  ngo_name: string;
  ngo_email: string;
  skills: string[];
  password: string;
  latitude?: number;
  longitude?: number;
  area?: string;
}

export interface TaskRecord {
  id: string;
  title: string;
  description: string | null;
  category: string;
  required_skills: string[];
  urgency: number;
  complexity: number;
  team_size: number;
  latitude: number;
  longitude: number;
  region: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface VolunteerRecord {
  id: string;
  name: string;
  email: string | null;
  skills: string[];
  latitude: number;
  longitude: number;
  area: string | null;
  availability: number;
  reliability: number;
  burnout_score: number;
  total_assignments: number;
  active_assignments: number;
  status: string;
  is_active: boolean;
  is_deployable: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssignmentRecord {
  id: string;
  task_id: string;
  volunteer_id: string;
  vas_score: number;
  status: string;
  assigned_at: string;
  completed_at: string | null;
}

export interface ExplainResponse {
  task_id: string;
  chosen_volunteer_id: string | null;
  chosen_volunteer_name: string | null;
  reason: string;
  confidence: number;
  factors: {
    skill_match: number;
    proximity: number;
    reliability: number;
    availability: number;
    burnout_adjustment: number;
    volunteer_fit: number;
    final_vas_score: number;
  } | null;
  alternatives: Array<{
    volunteer_id: string;
    volunteer_name: string;
    vas_score: number;
    rejection_reason: string;
  }>;
}

export interface AnalyticsOverview {
  total_active_tasks: number;
  volunteers_available: number;
  assignments_in_progress: number;
  total_tasks: number;
  completed_tasks: number;
  total_assignments: number;
  assignment_success_rate: number;
  tasks_per_volunteer: Record<string, number>;
  gini_coefficient: number;
  burnout_distribution: Array<{ burnout_score: number; count: number }>;
  avg_response_time: number;
  queue_latency: number;
  recent_activity?: Array<{ id: string; type: string; task_id: string; message: string; created_at: string }>;
  volunteer_health?: { avg_burnout: number; engagement_score: number };
}

export interface TaskCreatePayload {
  title: string;
  description?: string;
  category: string;
  required_skills: string[];
  urgency: number;
  complexity: number;
  team_size: number;
  latitude: number;
  longitude: number;
  region?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public isNetworkError: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let globalErrorHandler: ((error: ApiError) => void) | null = null;

export function setGlobalErrorHandler(handler: (error: ApiError) => void) {
  globalErrorHandler = handler;
}

function handleError(error: unknown): never {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    const apiError = new ApiError(
      'Unable to connect to server. Please check your network connection.',
      undefined,
      true
    );
    globalErrorHandler?.(apiError);
    throw apiError;
  }

  if (error instanceof ApiError) {
    globalErrorHandler?.(error);
    throw error;
  }

  if (error instanceof Error) {
    const apiError = new ApiError(error.message);
    globalErrorHandler?.(apiError);
    throw apiError;
  }

  const apiError = new ApiError('An unexpected error occurred');
  globalErrorHandler?.(apiError);
  throw apiError;
}

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('taskbridge_token', token);
  } else {
    localStorage.removeItem('taskbridge_token');
  }
}

export function getAuthToken() {
  return authToken;
}

const RETRY_ATTEMPTS = 1;
const RETRY_DELAY_MS = 1000;

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request<T>(path: string, init?: RequestInit, attempt: number = 0): Promise<T> {
  let headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(init?.headers ?? {}),
  };
  if (authToken) {
    headers = { ...headers, Authorization: `Bearer ${authToken}` };
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        const text = await response.text();
        if (text) {
          errorMessage = text;
        }
      }
      throw new ApiError(errorMessage, response.status);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.isNetworkError && attempt < RETRY_ATTEMPTS) {
        await delay(RETRY_DELAY_MS);
        return request<T>(path, init, attempt + 1);
      }
      throw error;
    }

    if (error instanceof TypeError) {
      if (attempt < RETRY_ATTEMPTS) {
        await delay(RETRY_DELAY_MS);
        return request<T>(path, init, attempt + 1);
      }
      return handleError(error) as never;
    }

    return handleError(error) as never;
  }
}

export const api = {
  login(email: string, password: string) {
    return request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  registerAdmin(payload: AdminRegisterPayload) {
    return request<AuthResponse>('/auth/register/admin', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  registerVolunteer(payload: VolunteerRegisterPayload) {
    return request<AuthResponse>('/auth/register/volunteer', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getMe() {
    return request<UserProfile>('/auth/me');
  },

  updateMe(payload: Partial<Pick<UserProfile, 'full_name' | 'latitude' | 'longitude' | 'area' | 'ngo_description'>>) {
    return request<UserProfile>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  getTasks(page = 1, pageSize = 100) {
    return request<{ tasks: TaskRecord[]; total: number; page: number; page_size: number }>(`/tasks?page=${page}&page_size=${pageSize}`);
  },

  createTask(payload: TaskCreatePayload) {
    return request<TaskRecord>('/tasks/create', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateTask(taskId: string, payload: Partial<Pick<TaskRecord, 'urgency' | 'complexity' | 'status' | 'team_size'>>) {
    return request<TaskRecord>(`/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  getVolunteers(page = 1, pageSize = 100) {
    return request<{ volunteers: VolunteerRecord[]; total: number; page: number; page_size: number }>(
      `/volunteers?page=${page}&page_size=${pageSize}`
    );
  },

  updateVolunteer(volunteerId: string, payload: Partial<Pick<VolunteerRecord, 'availability' | 'status' | 'skills' | 'latitude' | 'longitude' | 'area'>>) {
    return request<VolunteerRecord>(`/volunteers/${volunteerId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  getAssignments() {
    return request<AssignmentRecord[]>('/allocate/assignments');
  },

  runAllocationCycle() {
    return request<{
      assignments_created: number;
      assignments_reassigned: number;
      tasks_unmatched: number;
      cycle_duration_ms: number;
      details: AssignmentRecord[];
    }>('/allocate/run', {
      method: 'POST',
    });
  },

  getExplainability(taskId: string) {
    return request<ExplainResponse>(`/explain/${taskId}`);
  },

  getAnalyticsOverview() {
    return request<AnalyticsOverview>('/analytics/overview');
  },

  getPredictionHeat() {
    return request<{
      points: Array<{
        region: string;
        latitude: number;
        longitude: number;
        risk_score: number;
        predicted_tasks_24h: number;
        trend: string;
      }>;
    }>('/predict/heat');
  },

  chat(query: string) {
    return request<{ provider: string; intent: string; answer: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  },
};

export function websocketUrl(role: UserRole, userId: string): string {
  const wsBase = API_ORIGIN.replace('http://', 'ws://').replace('https://', 'wss://');
  const q = new URLSearchParams({ role, user_id: userId });
  if (authToken) {
    q.set('token', authToken);
  }
  return `${wsBase}/api/v1/ws/connect?${q.toString()}`;
}

export function simulationStreamUrl(simulationId: string): string {
  return `${API_ORIGIN}/api/v1/simulate/${encodeURIComponent(simulationId)}/stream`;
}