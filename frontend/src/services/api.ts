const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export type TrafficStatus = {
  source: 'simulated' | 'TomTom' | string;
  available: boolean;
  status: string;
  message?: string;
  city?: string;
};

export type NetworkStatus = {
  status: string;
  city: string;
  nodes: number;
  edges: number;
  source: string;
  fallback_reason?: string;
  fallback_message?: string;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || payload.message || 'Request failed');
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function healthCheck() {
  return api<{ status: string; service: string; version: string }>('/api/health');
}

export async function loadNetwork(city: string, offlineOnly = true) {
  return api<NetworkStatus & { loaded: boolean }>('/api/network/load', {
    method: 'POST',
    body: JSON.stringify({ city, offline_only: offlineOnly }),
  });
}

export async function getNetworkStatus() {
  return api<NetworkStatus>('/api/network/status');
}

export async function getLocations() {
  return api<{ city: string; depot: [number, number]; stops: [number, number][] }>('/api/locations');
}

export async function saveLocations(depot?: [number, number], stops?: [number, number][]) {
  return api<{ city: string; depot: [number, number]; stops: [number, number][] }>('/api/locations', {
    method: 'POST',
    body: JSON.stringify({
      depot: depot ? { latitude: depot[0], longitude: depot[1] } : null,
      stops: stops?.map(([latitude, longitude]) => ({ latitude, longitude })) || [],
    }),
  });
}

export async function optimizeRoute(request: any) {
  return api<{ job_id: string; status: string }>('/api/routes/optimize', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function pollJob(jobId: string): Promise<any> {
  return api<any>(`/api/jobs/${jobId}`);
}

export async function getCurrentRoute() {
  return api<any>('/api/routes/current');
}

export async function getRouteHistory() {
  return api<any[]>('/api/routes/history');
}

export async function simulateTraffic(level: string, fraction = 0.25) {
  return api<any>('/api/traffic/simulate', {
    method: 'POST',
    body: JSON.stringify({ level, fraction }),
  });
}

export async function resetTraffic() {
  return api<any>('/api/traffic/reset', { method: 'POST' });
}

export async function getTrafficStatus() {
  return api<TrafficStatus>('/api/traffic/status');
}

export async function getAnalytics() {
  return api<any>('/api/analytics');
}

export async function replanRoute(completed: number[], config: any) {
  return api<any>('/api/routes/replan', {
    method: 'POST',
    body: JSON.stringify({ completed, config }),
  });
}
