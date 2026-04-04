/**
 * Base URL for the Django API. Leave empty in dev to use the Vite proxy (see vite.config.js).
 * For production, set VITE_API_BASE_URL (e.g. https://api.example.com).
 */
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export function apiUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${p}`
}

async function parseErrorResponse(res) {
  const body = await res.json().catch(() => ({}))
  if (body && typeof body === 'object') {
    if (body.detail) return String(body.detail)
    const parts = []
    for (const [key, val] of Object.entries(body)) {
      if (Array.isArray(val)) parts.push(...val.map((m) => `${key}: ${m}`))
      else if (val != null) parts.push(`${key}: ${val}`)
    }
    if (parts.length) return parts.join(' ')
    if (body.message) return String(body.message)
  }
  return `Request failed (${res.status})`
}

export async function fetchProjects(accessToken) {
  const res = await fetch(apiUrl('/api/user-projects/'), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: 'application/json',
    },
  })
  if (!res.ok) throw new Error(await parseErrorResponse(res))
  return res.json()
}

export async function createProject(accessToken, payload) {
  const body = {
    name: payload.name,
    description: payload.description || '',
    sshKey: payload.sshKey,
    serverIp: payload.serverIp,
    rootDirectory: payload.rootDirectory,
    userDeployCommands:
      payload.userDeployCommands?.trim() ||
      'npm install && npm run build > logs/build.log 2>&1 && npm start',
  }
  const res = await fetch(apiUrl('/api/user-projects/'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseErrorResponse(res))
  return res.json()
}
