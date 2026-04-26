import type { BigBang, BigBangCreatePayload, BootstrapPayload, Job, TickSnapshot, WorkspacePayload } from './types';

let configuredApiPrefix = '/api';

function normalizeApiPrefix(prefix: unknown): string {
  if (typeof prefix !== 'string') return configuredApiPrefix;
  const trimmed = prefix.trim();
  if (!trimmed || trimmed === '/') return '';
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}`;
}

export function apiPath(path: string): string {
  if (/^(https?:)?\/\//.test(path)) return path;
  if (path === '/api') return configuredApiPrefix || '/';
  if (path.startsWith('/api/')) return `${configuredApiPrefix}${path.slice(4)}`;
  return path;
}

export function configureApiPrefix(prefix: unknown): void {
  configuredApiPrefix = normalizeApiPrefix(prefix);
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(apiPath(path), {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let body: any = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) {
    const detail = body?.detail ?? response.statusText;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(', ') : String(detail));
  }
  return body as T;
}

export const Api = {
  bootstrap: async () => {
    const payload = await api<BootstrapPayload>('/api/frontend/bootstrap');
    configureApiPrefix(payload.settings?.api_prefix);
    return payload;
  },
  settings: () => api<Record<string, any>>('/api/settings'),
  bigBangs: () => api<BigBang[]>('/api/big-bangs'),
  createBigBang: (payload: BigBangCreatePayload) => api<BigBang>('/api/big-bangs', { method: 'POST', body: JSON.stringify(payload) }),
  createScenarioBigBang: (scenarioId: string) => api<{ big_bang_id: string; scenario_id: string }>(`/api/scenario-bank/${scenarioId}/big-bang`, { method: 'POST', body: '{}' }),
  workspace: (bigBangId: string) => api<WorkspacePayload>(`/api/frontend/workspace/${bigBangId}`),
  inspect: (type: string, id: string) => api<any>(`/api/frontend/inspect/${type}/${id}`),
  status: (bigBangId: string, action: 'start' | 'pause' | 'resume') => api<BigBang>(`/api/big-bangs/${bigBangId}/${action}`, { method: 'POST', body: '{}' }),
  simulateNextTick: (multiverseId: string) => api<TickSnapshot>(`/api/multiverses/${multiverseId}/simulate-next-tick`, { method: 'POST', body: JSON.stringify({ force: false }) }),
  multiverseReport: (multiverseId: string) => api<any>(`/api/multiverses/${multiverseId}/report`, { method: 'POST', body: '{}' }),
  runUntilComplete: (bigBangId: string, payload: { max_total_ticks?: number } = {}) => api<any>(`/api/big-bangs/${bigBangId}/run-until-complete`, { method: 'POST', body: JSON.stringify(payload) }),
  createJob: (payload: { job_type: string; big_bang_id?: string; payload?: Record<string, unknown>; idempotency_key?: string }) =>
    api<Job>('/api/jobs', { method: 'POST', body: JSON.stringify({ payload: {}, ...payload }) }),
  job: (jobId: string) => api<Job>(`/api/jobs/${jobId}`),
  reports: (bigBangId: string) => api<any[]>(`/api/big-bangs/${bigBangId}/reports`),
  finalReport: (bigBangId: string) => api<any>(`/api/big-bangs/${bigBangId}/reports/final`, { method: 'POST', body: '{}' }),
  jobs: () => api<Job[]>('/api/jobs'),
  jobTypes: () => api<string[]>('/api/jobs/types'),
  runJob: (jobId: string) => api<any>(`/api/jobs/${jobId}/run`, { method: 'POST', body: '{}' }),
  artifactText: async (artifactId: string) => {
    const response = await fetch(apiPath(`/api/artifacts/${encodeURIComponent(artifactId)}`));
    if (!response.ok) throw new Error(await response.text() || response.statusText);
    return response.text();
  },
};
