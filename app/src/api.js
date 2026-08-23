// Client API — mirror ui/src/api.js, tapi base URL absolut (RN gak punya proxy Vite).
// Backend: indonime/server.py via indonime/app.py --dev (port 8756, bind 127.0.0.1).
//   - Emulator Android: 10.0.2.2 = loopback host → otomatis.
//   - Device fisik/Expo Go di HP: set EXPO_PUBLIC_API_URL=http://<IP-LAN-host>:8756
//     (dan server harus bind 0.0.0.0 dulu supaya kebuka dari HP).
import { Platform } from 'react-native'

export const API_URL =
  process.env.EXPO_PUBLIC_API_URL ||
  (Platform.OS === 'android' ? 'http://10.0.2.2:8756' : 'http://127.0.0.1:8756')

async function get(path) {
  const r = await fetch(`${API_URL}${path}`)
  const j = await r.json()
  if (!r.ok) throw new Error(j.error || r.status)
  return j
}

async function post(path, body) {
  const r = await fetch(`${API_URL}${path}`, {
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
  // identitas discovery → detail URL provider (multi-provider). title wajib.
  resolve: (id, title) => post('/api/resolve', { id, title }),
  info: (u, p) => get(`/api/info?url=${encodeURIComponent(u)}&provider=${p}`),
  episodes: (u, p) => get(`/api/episodes?url=${encodeURIComponent(u)}&provider=${p}`),
  downloads: (u, p) => get(`/api/downloads?url=${encodeURIComponent(u)}&provider=${p}`),
  play: (u, l) => post('/api/play', { server_url: u, label: l }),
  download: (u, t) => post('/api/download', { server_url: u, title: t }),
  jobs: () => get('/api/jobs'),
}
