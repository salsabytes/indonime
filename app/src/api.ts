// Client API — mirror ui/src/api.js, tapi base URL absolut (RN gak punya proxy Vite).
// Backend: indonime/server.py via indonime/app.py --dev (port 8756, bind 127.0.0.1).
//   - Emulator Android: 10.0.2.2 = loopback host → otomatis.
//   - Device fisik/Expo Go di HP: set EXPO_PUBLIC_API_URL=http://<IP-LAN-host>:8756
//     (dan server harus bind 0.0.0.0 dulu supaya kebuka dari HP).
import { Platform } from 'react-native'

export interface Item {
  id?: string
  url?: string
  title: string
  image?: string
  image_full?: string
  synopsis?: string
  score?: number | string
  year?: number | string
  ep?: string
  genres?: string[]
  genre?: string[]
}

export interface Ep {
  url: string
  title: string
}

export interface AnimeInfo {
  title?: string
  synopsis?: string
  image?: string
}

export interface DownloadOpt {
  label: string
  url: string
}

export interface Job {
  id: string
  title: string
  status: string
  done: number
  total: number
  error?: string
}

export interface PlayResp {
  stream?: string
  error?: string
}

export interface SourcesResp {
  sources: Record<string, string>
  candidates: [string, string, string][]
}

export interface DiscoverResp {
  items?: Item[]
  genres?: string[]
  results?: Item[]
}

let _webBase: string | null = null

// Base API di-resolve runtime, bukan build-time: native → host backend; web → cek dulu
// apakah page ini di-serve oleh kita (desktop/exe: same-origin, port apapun bisa acak →
// relative '' benar) atau di-serve expo dev (:8081, gak nge-proxy /api → fallback
// http://127.0.0.1:8756). Probe sekali, hasil di-cache.
export async function resolveBase(): Promise<string> {
  if (Platform.OS === 'android') return 'http://127.0.0.1:8756'  // backend tertanam (Chaquopy) di proses app
  if (Platform.OS !== 'web') return 'http://127.0.0.1:8756'
  if (process.env.EXPO_PUBLIC_API_URL) return process.env.EXPO_PUBLIC_API_URL
  if (_webBase !== null) return _webBase
  const origin = typeof window === 'undefined' ? '' : window.location.origin
  try {
    const r = await fetch(`${origin}/api/jobs`)
    if (r.ok && (r.headers.get('content-type') || '').includes('json')) { _webBase = ''; return '' }
    throw new Error('bukan backend indonime')
  } catch {
    _webBase = 'http://127.0.0.1:8756'
    return _webBase
  }
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${await resolveBase()}${path}`)
  const j = await r.json()
  if (!r.ok) throw new Error(j.error || r.status)
  return j
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${await resolveBase()}${path}`, {
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
  discover: (tab: string, params = '') =>
    get<DiscoverResp>(`/api/discover?tab=${tab}${params ? '&' + params : ''}`),
  // identitas discovery → detail URL provider (multi-provider). title wajib.
  resolve: (id: string, title: string) => post<SourcesResp>('/api/resolve', { id, title }),
  info: (u: string, p: string) => get<{ info: AnimeInfo }>(`/api/info?url=${encodeURIComponent(u)}&provider=${p}`),
  episodes: (u: string, p: string) => get<{ episodes: Ep[] }>(`/api/episodes?url=${encodeURIComponent(u)}&provider=${p}`),
  downloads: (u: string, p: string) => get<{ options: DownloadOpt[] }>(`/api/downloads?url=${encodeURIComponent(u)}&provider=${p}`),
  play: (u: string, l: string) => post<PlayResp>('/api/play', { server_url: u, label: l }),
  download: (u: string, t: string) => post<unknown>('/api/download', { server_url: u, title: t }),
  jobs: () => get<{ jobs: Job[] }>('/api/jobs'),
}