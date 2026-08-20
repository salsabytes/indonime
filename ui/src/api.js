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
  providers: () => get('/api/providers'),
  catalog: p => get(`/api/catalog?provider=${p}`),
  home: p => get(`/api/home?provider=${p}`),
  poster: (u, p) => get(`/api/poster?url=${encodeURIComponent(u)}&provider=${p}`),
  search: (q, p) => get(`/api/search?q=${encodeURIComponent(q)}&provider=${p}`),
  info: (u, p) => get(`/api/info?url=${encodeURIComponent(u)}&provider=${p}`),
  episodes: (u, p) => get(`/api/episodes?url=${encodeURIComponent(u)}&provider=${p}`),
  downloads: (u, p) => get(`/api/downloads?url=${encodeURIComponent(u)}&provider=${p}`),
  play: u => post('/api/play', { server_url: u }),
  download: (u, t) => post('/api/download', { server_url: u, title: t }),
  jobs: () => get('/api/jobs'),
  // Backend has no /api/latest yet — the home endpoint IS the latest posts.
  latest: p => get(`/api/home?provider=${p}`),
}