// Real API — talks to the Python backend (indonime/server.py, port 8756).
// Vite proxies /api → http://127.0.0.1:8756 (see vite.config.js).

async function get(path) {
  const r = await fetch(path)
  const j = await r.json()
  if (!r.ok) throw new Error(j.error || r.status)
  return j
}

async function post(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const j = await r.json()
  if (!r.ok) throw new Error(j.error || r.status)
  return j
}

export const api = {
  // Discovery (AniList): top|season|genre|search|latest|genres
  discover: (tab, params = '') =>
    get(`/api/discover?tab=${tab}${params ? '&' + params : ''}`),
  // Jikan-style id → provider detail URLs (multi-provider). title wajib (resolve by title).
  resolve: (id, title) => post('/api/resolve', { id, title }),
  info: (u, p) => get(`/api/info?url=${encodeURIComponent(u)}&provider=${p}`),
  episodes: (u, p) => get(`/api/episodes?url=${encodeURIComponent(u)}&provider=${p}`),
  downloads: (u, p) => get(`/api/downloads?url=${encodeURIComponent(u)}&provider=${p}`),
  play: (u, l) => post('/api/play', { server_url: u, label: l }),
  download: (u, t) => post('/api/download', { server_url: u, title: t }),
  jobs: () => get('/api/jobs'),
}
