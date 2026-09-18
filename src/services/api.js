const API_BASE_URL = (import.meta.env.API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function getToken() {
  return window.localStorage.getItem('darukaa_token')
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  if (response.status === 204) return null

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const message = typeof body?.detail === 'string' ? body.detail : 'The request could not be completed.'
    if (response.status === 401) window.dispatchEvent(new CustomEvent('darukaa:unauthorized'))
    throw new ApiError(response.status, message)
  }
  return body
}

export const api = {
  login: (credentials) => request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  register: (credentials) => request('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(credentials) }),
  me: () => request('/api/v1/auth/me'),
  projects: () => request('/api/v1/projects'),
  project: (id) => request(`/api/v1/projects/${id}`),
  createProject: (data) => request('/api/v1/projects', { method: 'POST', body: JSON.stringify(data) }),
  deleteProject: (id) => request(`/api/v1/projects/${id}`, { method: 'DELETE' }),
  dashboard: (id) => request(`/api/v1/projects/${id}/dashboard`),
  createSite: (projectId, data) => request(`/api/v1/projects/${projectId}/sites`, { method: 'POST', body: JSON.stringify(data) }),
  deleteSite: (projectId, siteId) => request(`/api/v1/projects/${projectId}/sites/${siteId}`, { method: 'DELETE' }),
  siteAnalytics: (siteId) => request(`/api/v1/sites/${siteId}/analytics`),
  siteTimeseries: (siteId) => request(`/api/v1/sites/${siteId}/analytics/timeseries`),
  siteDetails: (siteId) => request(`/api/v1/sites/${siteId}/analytics/details`),
  datasets: () => request('/api/v1/analytics/datasets'),
}
