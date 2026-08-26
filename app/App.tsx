// Indonime — React Native (Expo SDK 57) web/native app.
// Port pixel-faithful; desktop GUI (app.py + server.py) nyaji app/dist (RN web),
// React web Vite lama (ui/) sudah dihapus. Backend: Python (indonime/), port 8756.
import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactElement, ReactNode, RefObject } from 'react'
import {
  Animated, BackHandler, Modal, Platform, Pressable, ScrollView,
  StatusBar as RNStatusBar, StyleSheet, Text, TextInput, useWindowDimensions, View,
} from 'react-native'
import type { ImageStyle, NativeScrollEvent, NativeSyntheticEvent, StyleProp, TextStyle, ViewStyle } from 'react-native'
import { LinearGradient } from 'expo-linear-gradient'
import { Image } from 'expo-image'
import { VideoView, useVideoPlayer } from 'expo-video'
import { StatusBar } from 'expo-status-bar'
import Svg, { Defs, LinearGradient as SvgGrad, Stop, Text as SvgText } from 'react-native-svg'
import { useFonts, Outfit_500Medium, Outfit_700Bold, Outfit_800ExtraBold } from '@expo-google-fonts/outfit'
import { Rubik_400Regular, Rubik_500Medium, Rubik_600SemiBold } from '@expo-google-fonts/rubik'

import { api, resolveBase } from './src/api'
import type { AnimeInfo, DownloadOpt, Ep, Item, Job } from './src/api'
import { Ic } from './src/icons'
import { C, F } from './src/theme'
import { s } from './src/styles'

const HERO_MS = 6000
const BRK = 900 // breakpoint web @media (max-width: 900px)

// Breakpoint context: desktop = lebar ≥ 900px (layout web penuh); else layout mobile
const Brk = createContext({ desktop: false, width: 0 })
const useBrk = () => useContext(Brk)

type ViewName = 'home' | 'anime' | 'player'

interface AnimeState {
  item: Item | null
  provider: string
  url: string
  info: AnimeInfo
  episodes: Ep[]
}

export default function App() {
  const { width } = useWindowDimensions()
  return (
    <Brk.Provider value={{ desktop: width >= BRK, width }}>
      <AppInner />
    </Brk.Provider>
  )
}

function AppInner() {
  const [fontsLoaded] = useFonts({
    Outfit_500Medium, Outfit_700Bold, Outfit_800ExtraBold,
    Rubik_400Regular, Rubik_500Medium, Rubik_600SemiBold,
  })
  const [top, setTop] = useState<Item[]>([])
  const [seasonal, setSeasonal] = useState<Item[]>([])
  const [latest, setLatest] = useState<Item[] | null>(null)
  const [genres, setGenres] = useState<string[]>(['Semua'])
  const [genre, setGenre] = useState('Semua')
  const [genreItems, setGenreItems] = useState<Item[] | null>(null)
  const [genreLoading, setGenreLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Item[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [cands, setCands] = useState<[string, string, string][] | null>(null)
  const [view, setView] = useState<ViewName>('home')
  const [anime, setAnime] = useState<AnimeState | null>(null)
  const [stream, setStream] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [currentEpIdx, setCurrentEpIdx] = useState<number | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const scrollRef = useRef<ScrollView>(null)

  const scrollTop = () => scrollRef.current?.scrollTo({ y: 0, animated: false })

  useEffect(() => {
    let alive = true
    api.discover('top').then(r => alive && setTop(r.items ?? [])).catch(() => {})
    api.discover('season').then(r => alive && setSeasonal(r.items ?? [])).catch(() => {})
    api.discover('latest').then(r => alive && setLatest(r.items ?? [])).catch(() => {})
    api.discover('genres').then(r => alive && setGenres(['Semua', ...(r.genres ?? [])])).catch(() => {})
    return () => { alive = false }
  }, [])

  useEffect(() => {
    const t = setInterval(() => api.jobs().then(r => setJobs(r.jobs)).catch(() => {}), 1500)
    return () => clearInterval(t)
  }, [])

  // BackHandler Android: player → anime → home
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (view === 'player') { setView('anime'); return true }
      if (view === 'anime') { goHome(); return true }
      return false
    })
    return () => sub.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view])

  const submit = () => {
    const q = query.trim()
    if (!q) return setResults(null)
    setView('home'); scrollTop()  // search harus keluar dari halaman anime/player dulu
    setSearching(true)
    api.discover('search', 'q=' + encodeURIComponent(q))
      .then(r => setResults(r.results ?? []))
      .catch(err => setError(eMsg(err)))
      .finally(() => setSearching(false))
  }

  const goHome = () => { setView('home'); setResults(null); setQuery(''); setCands(null); setGenre('Semua'); scrollTop() }

  const pickGenre = (g: string) => {
    setGenre(g); setGenreItems(null)
    if (g === 'Semua') return
    setGenreLoading(true)
    api.discover('genre', 'genre=' + encodeURIComponent(g))
      .then(r => setGenreItems(r.items ?? []))
      .catch(err => setError(eMsg(err)))
      .finally(() => setGenreLoading(false))
  }

  const openDetail = (item: Item | null, prov: string, url: string) => {
    setBusy('Memuat detail...')
    return Promise.all([api.info(url, prov), api.episodes(url, prov)])
      .then(([info, eps]) => {
        setAnime({ item, provider: prov, url, info: info.info, episodes: eps.episodes })
        setView('anime'); setResults(null); setCands(null)
        scrollTop()
      })
      // reraise so pickAnime can fall back to the next provider
      .catch(err => { setError(err.message); throw err })
      .finally(() => setBusy(''))
  }

  // True only when the provider really serves sources: a live page is not
  // enough — probe a single episode's download options (dead Mega links are
  // already filtered server-side, so non-empty == at least one live link).
  const tryOpen = async (item: Item, prov: string, url: string): Promise<boolean> => {
    try {
      const [info, eps] = await Promise.all([api.info(url, prov), api.episodes(url, prov)])
      const list = eps.episodes || []
      const ep = list[0]
      let active = false
      if (ep) {
        const res = await api.downloads(ep.url, prov)
        active = !!res.options?.length
      }
      if (!active) return false
      setAnime({ item, provider: prov, url, info: info.info, episodes: list })
      setView('anime'); setResults(null); setCands(null)
      scrollTop()
      return true
    } catch { return false }  // page error -> provider nonaktif, coba yang lain
  }

  const pickAnime = async (item: Item) => {
    setBusy('Mencari sumber...')
    try {
      const direct = item.url ? [{
        prov: item.url.includes('otakudesu') ? 'otakudesu' : 'anoboy',
        url: item.url,
      }] : []
      // Rilis Terbaru: coba url langsung dulu, resolve jadi fallback
      for (const d of direct) {
        if (await tryOpen(item, d.prov, d.url)) return
      }
      // multi-provider: search semua provider, gap-fill yang sukses
      const { sources, candidates } = await api.resolve(item.id ?? '', item.title)
      for (const [prov, url] of Object.entries(sources)) {
        if (await tryOpen(item, prov, url)) return
      }
      setCands(candidates)  // semua provider tanpa sumber aktif -> pilih manual
    } catch (err) { setError(eMsg(err)) }
    finally { setBusy('') }
  }

  const pickCandidate = (prov: string, url: string) => openDetail(null, prov, url).catch(() => {})

  const handlePlay = async (url: string, label: string, epIdx?: number) => {
    // Langsung pindah ke halaman nonton — loading resolve stream di player.
    if (epIdx !== undefined) setCurrentEpIdx(epIdx)
    setView('player'); setStream(null); setStreamError(null); scrollTop()
    try {
      const r = await api.play(url, label)
      if (r.stream) setStream(r.stream.startsWith('http') ? r.stream : (await resolveBase()) + r.stream)
      else setStreamError(r.error || 'Gagal memutar')
    } catch (err) { setStreamError(eMsg(err)) }
  }

  // Auto-play episode by index (prev/next nav)
  const playEp = async (idx: number) => {
    if (!anime || idx < 0 || idx >= anime.episodes.length) return
    const ep = anime.episodes[idx]
    setCurrentEpIdx(idx)
    setView('player'); setStream(null); setStreamError(null); scrollTop()
    try {
      const res = await api.downloads(ep.url, anime.provider)
      const opt = res.options?.[0]
      if (!opt) { setStreamError('Tidak ada server tersedia'); return }
      const r = await api.play(opt.url, opt.label)
      if (r.stream) setStream(r.stream.startsWith('http') ? r.stream : (await resolveBase()) + r.stream)
      else setStreamError(r.error || 'Gagal memutar')
    } catch (err) { setStreamError(eMsg(err)) }
  }

  const handleDownload = (opt: DownloadOpt, ep: Ep) => {
    const base = (anime?.info.title || (anime?.item && anime.item.title) || '').replace(/\s+Subtitle Indonesia.*$/i, '')
    api.download(opt.url, `${base} — ${ep.title}`).catch(err => setError(eMsg(err)))
  }

  if (!fontsLoaded) return null

  return (
    <View style={s.app}>
      {Platform.OS !== 'web' && <StatusBar style="light" />}
      <AmbientGlow />

      <Topbar query={query} setQuery={setQuery} onSubmit={submit} onHome={goHome} />

      <ScrollView ref={scrollRef} style={s.scroll} keyboardShouldPersistTaps="handled"
                  showsVerticalScrollIndicator={false}>
        {view === 'home' && (
          <HomeView top={top} seasonal={seasonal} latest={latest}
                    genres={genres} genre={genre} onGenrePick={pickGenre}
                    genreItems={genreItems} genreLoading={genreLoading}
                    results={results} searching={searching} query={query}
                    onPick={pickAnime} scrollRef={scrollRef} />
        )}
        {view === 'anime' && anime && (
          <AnimeView anime={anime} onPlay={handlePlay}
                     onDownload={handleDownload} onBack={goHome} />
        )}
        {view === 'player' && (
          <PlayerView stream={stream} error={streamError} onBack={() => setView('anime')}
                      episodes={anime?.episodes || []} currentEpIdx={currentEpIdx} onPlayEp={playEp} />
        )}
        {view === 'home' && <Footer onJump={label => scrollRef.current?.scrollTo({ y: sectionY[label] || 0, animated: true })} />}
      </ScrollView>

      {!!error && (
        <View style={[s.toast, s.errorToast]}>
          <Text style={s.toastText} numberOfLines={2}>{error}</Text>
          <Pressable style={s.iconBtn} onPress={() => setError(null)} hitSlop={8}>
            <Ic.x color={C.fgDim} size={16} />
          </Pressable>
        </View>
      )}
      {!!busy && (
        <View style={s.toast}>
          <Spinner />
          <Text style={s.toastText} numberOfLines={2}>{busy}</Text>
        </View>
      )}

      {cands && (
        <Modal visible transparent animationType="fade" onRequestClose={() => setCands(null)}>
          <Pressable style={s.modalOverlay} onPress={() => setCands(null)}>
            <Pressable style={s.modalCard} onPress={() => {}}>
              <View style={s.optsHead}>
                <Text style={s.optsTitle} numberOfLines={1}>Pilih judul yang sesuai</Text>
                <Pressable style={s.iconBtn} onPress={() => setCands(null)} hitSlop={8} accessibilityLabel="Tutup">
                  <Ic.x color={C.fgDim} size={16} />
                </Pressable>
              </View>
              <ScrollView showsVerticalScrollIndicator={false}>
                {!cands.length && <Text style={[s.hint, { textAlign: 'center', paddingVertical: 12 }]}>Belum ada di provider. Coba judul lain atau nanti lagi.</Text>}
                {cands.map((c, i) => (
                  <Pressable key={i} style={({ pressed }) => [s.ep, pressed && { backgroundColor: C.card2 }]}
                             onPress={() => { setCands(null); openDetail(null, c[0], c[2]) }}>
                    <Text style={s.epNum}>{c[0]}</Text>
                    <Text style={s.epTitle} numberOfLines={1}>{c[1]}</Text>
                    <Ic.chev color={C.muted} size={16} />
                  </Pressable>
                ))}
              </ScrollView>
            </Pressable>
          </Pressable>
        </Modal>
      )}

      {jobs.length > 0 && <JobToasts jobs={jobs} />}
    </View>
  )
}

/* Section y-offsets utk Footer jump (pengganti anchor #latest-title / #popular-title) */
const sectionY: Record<string, number> = {}

// catch clause di TS strict = unknown; fetch error selalu Error
const eMsg = (e: unknown) => (e instanceof Error ? e.message : String(e))

/* ── Header ─────────────────────────────────────────────── */

interface TopbarProps {
  query: string
  setQuery: (v: string) => void
  onSubmit: () => void
  onHome: () => void
}

// ponystail: padding atas status bar — StatusBar.currentHeight cuma reliable di Android
const ANDROID_SB_TOP = Platform.OS === 'android' ? (RNStatusBar.currentHeight ?? 24) : 0

function Topbar({ query, setQuery, onSubmit, onHome }: TopbarProps) {
  const { desktop, width } = useBrk()
  if (desktop) {
    // Layout desktop: satu baris 64px — logo | search (flex, max 360, kanan)
    return (
      <View style={[s.topbar, { paddingTop: ANDROID_SB_TOP, paddingVertical: 0 }]}>
        <View style={s.topbarInner}>
          <LogoButton onPress={onHome} />
          <SearchBox query={query} setQuery={setQuery} onSubmit={onSubmit}
                     style={{ flex: 1, maxWidth: 360, marginLeft: 'auto' }} />
        </View>
      </View>
    )
  }
  // Layout mobile: 2 baris — logo+home / search
  return (
    <View style={[s.topbar, { paddingTop: ANDROID_SB_TOP + 10 }]}>
      <View style={s.topbarRow}>
        <LogoButton onPress={onHome} />
        {width <= 480 && (
          <Pressable style={s.iconBtn} onPress={onHome} hitSlop={8} accessibilityLabel="Beranda">
            <Ic.home color={C.fgDim} size={18} />
          </Pressable>
        )}
      </View>
      <SearchBox query={query} setQuery={setQuery} onSubmit={onSubmit} />
    </View>
  )
}

function LogoButton({ onPress }: { onPress: () => void }) {
  return (
    <Pressable style={s.logo} onPress={onPress} hitSlop={8}>
      <LinearGradient colors={[C.primary, C.accent]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={s.logoMark}>
        <Ic.playLg color={C.white} size={20} />
      </LinearGradient>
      <View style={{ flexDirection: 'row', alignItems: 'flex-end' }}>
        <Text style={s.logoText}>INDO</Text>
        <GradText style={s.logoText} size={18}>NIME</GradText>
      </View>
    </Pressable>
  )
}

interface SearchBoxProps {
  query: string
  setQuery: (v: string) => void
  onSubmit: () => void
  style?: StyleProp<ViewStyle>
}

function SearchBox({ query, setQuery, onSubmit, style }: SearchBoxProps) {
  return (
    <View style={[s.searchBox, style]}>
      <TextInput value={query} onChangeText={setQuery} placeholder="Cari anime…"
                 placeholderTextColor={C.muted} style={s.searchInput}
                 returnKeyType="search" onSubmitEditing={onSubmit} />
      <Pressable style={s.searchBtn} onPress={onSubmit} accessibilityLabel="Cari" hitSlop={6}>
        <Ic.search color={C.fgDim} size={18} />
      </Pressable>
    </View>
  )
}

/* ── Home ───────────────────────────────────────────────── */

interface HomeViewProps {
  top: Item[]
  seasonal: Item[]
  latest: Item[] | null
  genres: string[]
  genre: string
  onGenrePick: (g: string) => void
  genreItems: Item[] | null
  genreLoading: boolean
  results: Item[] | null
  searching: boolean
  query: string
  onPick: (item: Item) => void
  scrollRef: RefObject<ScrollView | null>
}

function HomeView({ top, seasonal, latest, genres, genre, onGenrePick, genreItems, genreLoading, results, searching, query, onPick, scrollRef }: HomeViewProps) {
  const { desktop, width } = useBrk()
  // grid web: base auto-fill minmax(160px,1fr) gap 18; ≤480px: minmax(120px,1fr) gap 12
  // container dibatasi wrap max-width 1200 (web .wrap)
  const cw = Math.min(width, 1200) - 40
  const gap = width <= 480 ? 12 : 18
  const min = width <= 480 ? 120 : 160
  const cols = Math.max(1, Math.floor((cw + gap) / (min + gap)))
  const gridCard = { width: (cw - gap * (cols - 1)) / cols }
  const gridStyle = [s.grid, { columnGap: gap, rowGap: gap }]

  if (searching || genreLoading) {
    return (
      <View style={[s.wrap, s.pagePad]}>
        <View style={[s.hintCenter, { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }]}>
          <Spinner />
          <Text style={[s.hint, { textAlign: 'center' }]}>{searching ? 'Mencari…' : 'Memuat genre…'}</Text>
        </View>
      </View>
    )
  }

  if (results) {
    return (
      <View style={[s.wrap, s.pagePad]}>
        <SectionTitle icon={<Ic.search color={C.primary2} />}>Hasil untuk “{query}”</SectionTitle>
        {results.length === 0
          ? <Text style={[s.hint, s.hintCenter, { textAlign: 'center' }]}>Tidak ada hasil. Coba judul lain.</Text>
          : (
            <View style={gridStyle}>
              {results.map((it, i) => <Card key={it.id} item={it} i={i} onPick={onPick} style={{ width: gridCard.width }} meta={it.score ? `★ ${it.score}` : ''} />)}
            </View>
          )}
      </View>
    )
  }

  if (genre !== 'Semua' && genreItems) {
    return (
      <View style={[s.wrap, s.pagePad]}>
        <SectionTitle icon={<Ic.flame color={C.primary2} />}>Genre: {genre}</SectionTitle>
        {genreItems.length === 0
          ? <Text style={[s.hint, s.hintCenter, { textAlign: 'center' }]}>Tidak ada judul untuk genre ini.</Text>
          : (
            <View style={gridStyle}>
              {genreItems.map((it, i) => <Card key={it.id} item={it} i={i} onPick={onPick} style={{ width: gridCard.width }} meta={`${it.score ? '★ ' + it.score : ''}${it.year ? ' · ' + it.year : ''}`} />)}
            </View>
          )}
      </View>
    )
  }

  return (
    <>
      {top.length > 0 && <Hero items={top} onPick={onPick} />}

      <View style={[s.wrap, s.pagePad]}>
        <View style={s.stats} accessibilityLabel="Statistik">
          <StatCard style={{ flex: 1, minWidth: width <= 480 ? '100%' : 140 }} value={top.length || '—'} label="Judul top" />
          <StatCard style={{ flex: 1, minWidth: width <= 480 ? '100%' : 140 }} value="4K" label="Kualitas stream" />
          <StatCard style={{ flex: 1, minWidth: width <= 480 ? '100%' : 140 }} value="24/7" label="Update episode" />
        </View>

        <View onLayout={e => { sectionY.latest = e.nativeEvent.layout.y }}>
          <Rail title="Rilis Terbaru" icon={<Ic.clock color={C.primary2} />}
                toolbar={genres.length > 1
                  ? <GenreChips genres={genres} active={genre} onPick={onGenrePick} />
                  : null}>
            {!latest
              ? <SkeletonRail n={8} />
              : latest.map((it, i) => <Card key={it.url} item={it} i={i} onPick={onPick} style={s.railCard} />)}
          </Rail>
        </View>

        <View style={{ marginTop: 56 }} onLayout={e => { sectionY.season = e.nativeEvent.layout.y }}>
          <Rail title="Musim Ini" icon={<Ic.flame color={C.primary2} />}>
            {!seasonal.length
              ? <SkeletonRail n={8} />
              : seasonal.map((it, i) => <Card key={it.id} item={it} i={i} onPick={onPick} style={s.railCard} meta={`${it.score ? '★ ' + it.score : ''}${it.year ? ' · ' + it.year : ''}`} />)}
          </Rail>
        </View>

        <View style={{ marginTop: 56 }} onLayout={e => { sectionY.popular = e.nativeEvent.layout.y }}>
          <Rail title="Paling Populer" icon={<Ic.flame color={C.primary2} />} wide>
            {!top.length
              ? <SkeletonRail n={5} wide />
              : top.slice(0, 8).map((it, i) => <RankCard key={it.id} item={it} i={i} onPick={onPick} />)}
          </Rail>
        </View>
      </View>
    </>
  )
}

interface StatCardProps {
  value: string | number
  label: string
  style?: StyleProp<ViewStyle>
}

function StatCard({ value, label, style }: StatCardProps) {
  return (
    <View style={[s.statCard, style]}>
      <LinearGradient colors={[C.card, C.bg2]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
      <GradText style={s.statNum} size={26}>{String(value)}</GradText>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  )
}

interface RailProps {
  title: string
  icon: ReactNode
  toolbar?: ReactNode
  children: ReactNode
  wide?: boolean
}

function Rail({ title, icon, toolbar, children, wide }: RailProps) {
  const { desktop } = useBrk()
  const scroll = useRef<ScrollView>(null)
  const xRef = useRef(0)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(true)
  const step = wide ? 360 : 200

  const evalArrows = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const x = e.nativeEvent.contentOffset.x
    const mw = e.nativeEvent.layoutMeasurement.width
    const cw = e.nativeEvent.contentSize.width
    xRef.current = x
    setCanLeft(x > 4)
    setCanRight(x < cw - mw - 4)
  }
  const go = (d: number) => scroll.current?.scrollTo({ x: Math.max(0, xRef.current + d * step), animated: true })

  return (
    <View>
      <View style={s.sectionHead}>
        <SectionTitle icon={icon}>{title}</SectionTitle>
        {desktop && (
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Pressable style={[s.railBtn, !canLeft && s.railBtnDisabled]} onPress={() => go(-1)}
                       disabled={!canLeft} accessibilityLabel={`Geser ${title} ke kiri`}>
              <Text style={s.railBtnText}>‹</Text>
            </Pressable>
            <Pressable style={[s.railBtn, !canRight && s.railBtnDisabled]} onPress={() => go(1)}
                       disabled={!canRight} accessibilityLabel={`Geser ${title} ke kanan`}>
              <Text style={s.railBtnText}>›</Text>
            </Pressable>
          </View>
        )}
      </View>
      {toolbar}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} ref={scroll} onScroll={evalArrows}
                  scrollEventThrottle={64}
                  contentContainerStyle={s.rail} snapToInterval={step} snapToAlignment="start"
                  decelerationRate="fast">
        {children}
      </ScrollView>
    </View>
  )
}

interface HeroProps {
  items: Item[]
  onPick: (item: Item) => void
}

function Hero({ items, onPick }: HeroProps) {
  const { desktop, width } = useBrk()
  const [idx, setIdx] = useState(0)
  const slides = items.slice(0, 6)
  const n = slides.length
  const it = slides[idx]
  const scale = useRef(new Animated.Value(1.06)).current
  const fill = useRef(new Animated.Value(0)).current
  // clamp() web: title 2.2–3.6rem (5.5vw), cover 150–230 (22vw) desktop / 120–180 (28vw) mobile, gap 20–56 (4vw)
  const titleSize = Math.min(57.6, Math.max(35.2, width * 0.055))
  const coverW = desktop
    ? Math.min(230, Math.max(150, width * 0.22))
    : Math.min(180, Math.max(120, width * 0.28))
  const gap = Math.min(56, Math.max(20, width * 0.04))

  useEffect(() => {
    if (n < 2) return
    const t = setInterval(() => setIdx(i => (i + 1) % n), HERO_MS)
    return () => clearInterval(t)
  }, [n])

  useEffect(() => {
    if (!it) return
    scale.setValue(1.06); fill.setValue(0)
    Animated.timing(scale, { toValue: 1, duration: 8000, useNativeDriver: Platform.OS !== 'web' }).start()
    Animated.timing(fill, { toValue: 1, duration: HERO_MS, useNativeDriver: Platform.OS !== 'web' }).start()
    const next = slides[(idx + 1) % n]
    const nxt = next?.image_full || next?.image
    if (nxt) Image.prefetch(nxt)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx])

  if (!it) return null

  return (
    <View style={[s.hero, desktop && { minHeight: 560 }]}>
      <View style={s.heroBackdrop}>
        <Animated.View style={{ flex: 1, transform: [{ scale }] }}>
          <HeroImg it={it} style={s.heroBg} />
        </Animated.View>
        <LinearGradient colors={['rgba(15,15,35,0.92)', 'rgba(15,15,35,0.6)', 'rgba(15,15,35,0.25)']}
                        locations={[0, 0.45, 1]} start={{ x: 0, y: 0.5 }} end={{ x: 1, y: 0.5 }} style={s.heroVeilH} />
        <LinearGradient colors={['rgba(15,15,35,0)', C.bg]} locations={[0.35, 1]}
                        start={{ x: 0, y: 0 }} end={{ x: 0, y: 1 }} style={s.heroVeilV} />
      </View>

      <View style={[s.heroContent, { gap }]}>
        <View style={s.heroText}>
          <View style={s.heroChip}>
            <View style={s.heroChipDot} />
            <Text style={s.heroChipText}>{it.score ? `★ ${it.score}` : 'AniList'}</Text>
          </View>
          <Text style={[s.heroTitle, { fontSize: titleSize, lineHeight: Math.round(titleSize * 1.08) }]} numberOfLines={2}>{it.title}</Text>
          {!!it.synopsis && <Text style={[s.heroSynopsis, desktop && { maxWidth: 364 }]} numberOfLines={3}>{it.synopsis}</Text>}
          <View style={s.heroActions}>
            <Btn primary onPress={() => onPick(it)} icon={<Ic.playLg color={C.white} size={20} />}>
              Lihat Detail
            </Btn>
            {!!it.ep && desktop && (
              <Btn ghost onPress={() => onPick(it)} icon={<Ic.clock color={C.fg} size={18} />}>
                Episode {it.ep}
              </Btn>
            )}
          </View>
        </View>
        <Image source={{ uri: it.image_full || it.image }} contentFit="cover"
               transition={300} style={[s.heroCover, { width: coverW }, desktop && { borderColor: 'rgba(167,139,250,0.22)' }]} />
      </View>

      {n > 1 && (
        <>
          {desktop && (
            <>
              <Pressable style={[s.heroArrow, s.heroArrowLeft]} onPress={() => setIdx(idx => (idx - 1 + n) % n)}
                         accessibilityLabel="Slide sebelumnya">
                <Text style={s.heroArrowText}>‹</Text>
              </Pressable>
              <Pressable style={[s.heroArrow, s.heroArrowRight]} onPress={() => setIdx(idx => (idx + 1) % n)}
                         accessibilityLabel="Slide berikutnya">
                <Text style={s.heroArrowText}>›</Text>
              </Pressable>
            </>
          )}
          <View style={s.heroSegs} accessibilityRole="tablist" accessibilityLabel="Navigasi slide">
            {slides.map((slide, i) => (
              <Pressable key={i} style={[s.heroSeg, i === idx && { backgroundColor: 'rgba(255,255,255,0.4)' }]}
                         onPress={() => setIdx(i)} accessibilityLabel={`Slide ${i + 1}: ${slide.title}`}>
                {i === idx && (
                  <Animated.View key={`f${idx}`} style={[s.heroSegFill, { transform: [{ scaleX: fill }], transformOrigin: 'left' }]}>
                    <LinearGradient colors={[C.primary2, C.accent]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={StyleSheet.absoluteFill} />
                  </Animated.View>
                )}
              </Pressable>
            ))}
          </View>
        </>
      )}
    </View>
  )
}

interface HeroImgProps {
  it: Item
  style?: StyleProp<ViewStyle>
}

function HeroImg({ it, style }: HeroImgProps) {
  const [src, setSrc] = useState(it.image_full || it.image || '')
  useEffect(() => { setSrc(it.image_full || it.image || '') }, [it])
  if (!src) return null
  // Image style cuma terima ImageStyle; callers kirim ViewStyle (s.heroBg) — runtime sama
  return <Image source={{ uri: src }} contentFit="cover" blurRadius={28} transition={300} style={style as StyleProp<ImageStyle>} onError={() => setSrc('')} />
}

/* ── Cards & sections ───────────────────────────────────── */

interface SectionTitleProps {
  children: ReactNode
  icon?: ReactNode
}

function SectionTitle({ children, icon }: SectionTitleProps) {
  return (
    <View style={s.sectionTitleRow}>
      {icon && <View style={s.sectionIcon}>{icon}</View>}
      <Text style={s.sectionTitle}>{children}</Text>
      <LinearGradient colors={[C.border, 'transparent']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ flex: 1, height: 1, marginLeft: 8 }} />
    </View>
  )
}

interface GenreChipsProps {
  genres: string[]
  active: string
  onPick: (g: string) => void
}

function GenreChips({ genres, active, onPick }: GenreChipsProps) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 0 }}>
      <View style={s.chips}>
        {genres.map(g => (
          <Pressable key={g} onPress={() => onPick(g)} style={[s.chip, g === active && { boxShadow: '0 4px 16px rgba(124,58,237,0.4)' }]}
                     accessibilityRole="button" accessibilityState={{ selected: g === active }}>
            {g === active && (
              <LinearGradient colors={[C.primary, C.primaryV2]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
            )}
            <Text style={g === active ? s.chipOnText : s.chipText}>{g}</Text>
          </Pressable>
        ))}
      </View>
    </ScrollView>
  )
}

interface CardProps {
  item: Item
  badge?: string
  sub?: string
  meta?: string
  i?: number
  onPick: (item: Item) => void
  style?: StyleProp<ViewStyle>
}

function Card({ item, badge, sub, meta, i, onPick, style }: CardProps) {
  return (
    <Pressable style={[s.card, style]} onPress={() => onPick(item)}>
      <View style={s.cardPoster}>
        <Poster item={item} />
        {badge && (
          <View style={s.epBadge}>
            <LinearGradient colors={[C.accent, C.accent2]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
            <Text style={s.epBadgeText}>{badge}</Text>
          </View>
        )}
      </View>
      <View style={s.cardBody}>
        <Text style={s.cardTitle} numberOfLines={2}>{item.title}</Text>
        {sub ? <Text style={s.cardSub}>{sub}</Text> : null}
        {meta ? <Text style={s.cardMeta}>{meta}</Text> : null}
      </View>
    </Pressable>
  )
}

interface SkeletonRailProps {
  n: number
  wide?: boolean
}

function SkeletonRail({ n, wide }: SkeletonRailProps) {
  return (
    <View style={[s.rail, { flexDirection: 'row' }]} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {Array.from({ length: n }, (_, i) => (
        <View key={i} style={[wide ? s.railRank : s.railCard]}>
          <Shimmer><View style={s.skeletonPoster} /></Shimmer>
          <Shimmer delay={i * 60}><View style={s.skeletonLine} /></Shimmer>
          <Shimmer delay={i * 60}><View style={[s.skeletonLine, s.skeletonLineShort]} /></Shimmer>
        </View>
      ))}
    </View>
  )
}

interface RankCardProps {
  item: Item
  i: number
  onPick: (item: Item) => void
}

function RankCard({ item, i, onPick }: RankCardProps) {
  return (
    <Pressable style={s.rankCard} onPress={() => onPick(item)}>
      <GradText style={s.popRank} size={26} center colors={[C.primary2, C.accent]} horizontal={false}>
        {String(i + 1).padStart(2, '0')}
      </GradText>
      <View style={s.popPoster}>
        <Poster item={item} style={{ width: 64, height: 88, borderRadius: 10 }}>
          <View style={s.popPlay}><Ic.play color={C.white} size={16} /></View>
        </Poster>
      </View>
      <View style={s.popBody}>
        <Text style={s.popTitle} numberOfLines={1}>{item.title}</Text>
        {(item.ep || (item.genres || item.genre || []).length > 0) && (
          <Text style={s.popMeta}>
            {[item.ep ? `${item.ep} episode` : '', (item.genres || item.genre || []).slice(0, 2).join(' · '),
              item.score ? `★ ${item.score}` : ''].filter(Boolean).join(' · ')}
          </Text>
        )}
      </View>
      <View style={s.popGo}><Ic.chev color={C.muted} size={18} /></View>
    </Pressable>
  )
}

interface PosterProps {
  item: Item
  style?: StyleProp<ViewStyle>
  children?: ReactNode
}

function Poster({ item, style, children }: PosterProps) {
  const img = item.image || ''
  if (img) {
    return (
      <View style={[s.poster, style]}>
        <Image source={{ uri: img }} contentFit="cover" transition={200} style={StyleSheet.absoluteFill} />
        {children}
      </View>
    )
  }
  return (
    <Shimmer style={[s.poster, s.posterPlaceholder, style]}>
      <Text style={s.posterPhText}>{item.title.slice(0, 2)}</Text>
      {children}
    </Shimmer>
  )
}

/* ── Buttons ────────────────────────────────────────────── */

interface BtnProps {
  primary?: boolean
  play?: boolean
  ghost?: boolean
  small?: boolean
  disabled?: boolean
  onPress?: () => void
  icon?: ReactNode
  children: ReactNode
  style?: StyleProp<ViewStyle>
}

function Btn({ primary, play, ghost, small, disabled, onPress, icon, children, style }: BtnProps) {
  const grad = primary
    ? <LinearGradient colors={[C.primary, C.primaryV2]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
    : play
      ? <LinearGradient colors={[C.accent, C.accent2]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
      : null
  const textStyle = primary ? s.btnPrimaryText : play ? s.btnPlayText : s.btnGhostText
  return (
    <Pressable onPress={onPress} disabled={disabled}
               style={({ pressed }) => [
                 s.btn, small && s.btnSmall,
                 primary ? s.btnPrimary : play ? s.btnPlay : s.btnGhost,
                 Platform.OS === 'web' && { zIndex: 0 },
                 disabled && s.btnDisabled,
                 pressed && { transform: [{ scale: 0.97 }] },
                 style,
               ]}>
      {grad}
      {icon}
      <Text style={[textStyle, small && s.btnTextSmall]}>{children}</Text>
    </Pressable>
  )
}

/* ── Anime detail ───────────────────────────────────────── */

interface ResSelectProps {
  options: ResOption[]
  value: string
  onChange: (v: string) => void
}

function ResSelect({ options, value, onChange }: ResSelectProps) {
  const [open, setOpen] = useState(false)
  const cur = options.find(o => o.url === value) || options[0]

  useEffect(() => {
    if (!open) return
    const sub = BackHandler.addEventListener('hardwareBackPress', () => { setOpen(false); return true })
    return () => sub.remove()
  }, [open])

  return (
    <>
      <Pressable style={[s.rselectBtn, open && { borderColor: C.primary }]} onPress={() => setOpen(o => !o)}
                 accessibilityRole="button" accessibilityState={{ expanded: open }}>
        <Text style={s.rselectText} numberOfLines={1}>{cur?.name}</Text>
        <View style={{ transform: [{ rotate: open ? '180deg' : '0deg' }] }}>
          <Ic.chev color={C.primary2} size={18} />
        </View>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={s.rselectBackdrop} onPress={() => setOpen(false)}>
          <Pressable style={s.rselectSheet} onPress={() => {}}>
            {options.map(o => (
              <Pressable key={o.url} style={[s.rselectItem, o.url === cur?.url && s.rselectItemOn]}
                         onPress={() => { onChange(o.url); setOpen(false) }}>
                <Text style={o.url === cur?.url ? s.rselectItemOnText : s.rselectItemText} numberOfLines={1}>{o.name}</Text>
              </Pressable>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </>
  )
}

interface AnimeViewProps {
  anime: AnimeState
  onPlay: (url: string, label: string, epIdx: number) => void
  onDownload: (opt: DownloadOpt, ep: Ep) => void
  onBack: () => void
}

// Opsi server di modal: name = teks bersih (tanpa [res] prefix), label = raw server label
interface ResOption {
  name: string
  url: string
  label: string
}

function AnimeView({ anime, onPlay, onDownload, onBack }: AnimeViewProps) {
  const { desktop, width } = useBrk()
  const [opts, setOpts] = useState<{ ep: Ep; options: DownloadOpt[] } | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [sel, setSel] = useState<Record<string, string>>({})
  const [pickedEpIdx, setPickedEpIdx] = useState<number>(0)
  const item = anime.item || ({} as Item)
  const { info, episodes, provider } = anime
  const title = info.title || item.title || ''

  const pick = async (ep: Ep, idx: number) => {
    setPickedEpIdx(idx)
    setBusy(true); setErr(null); setOpts(null)
    try { setOpts({ ep, options: (await api.downloads(ep.url, provider)).options }) }
    catch (e) { setErr(eMsg(e)) }
    finally { setBusy(false) }
  }

  const pickList = useMemo(() => (opts ? [...opts.options].reverse() : []), [opts])

  const groups = useMemo(() => {
    const map = new Map<string, ResOption[]>()
    // Browser tak bisa decode MKV — sama spt web, hidden utk player mobile.
    // TUI/mpv path tetap nge-serve.
    pickList.filter(o => !/mkv/i.test(o.label)).forEach(o => {
      const m = o.label.match(/^\[(.+?)\]\s*(.*)$/)
      const res = m ? m[1] : 'Lainnya'
      const name = m ? m[2] : o.label
      if (!map.has(res)) map.set(res, [])
      map.get(res)!.push({ name, url: o.url, label: o.label })
    })
    return [...map.entries()].map(([res, options]) => ({ res, options }))
  }, [pickList])

  useEffect(() => {
    if (!opts) return
    const sub = BackHandler.addEventListener('hardwareBackPress', () => { setOpts(null); return true })
    return () => sub.remove()
  }, [opts])

  return (
    <View style={[s.wrap, s.pagePad]}>
      <Btn ghost style={s.back} onPress={onBack} icon={<Ic.back color={C.fg} size={18} />}>Kembali</Btn>

      <View style={[s.detailHero, desktop ? { flexDirection: 'row', alignItems: 'flex-start' } : { flexDirection: 'column' }]}>
        <LinearGradient colors={[C.card, C.bg2]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
        <View style={[s.detailPosterWrap, desktop && { width: 220, alignItems: 'flex-start' }]}>
          <View style={[s.detailPoster, s.detailPosterPh, desktop && { width: 220, maxWidth: 220 }]}>
            {(item.image_full || item.image || info.image)
              ? <Image source={{ uri: item.image_full || item.image || info.image }} contentFit="cover" transition={300} style={StyleSheet.absoluteFill} />
              : <Text style={s.detailPhText}>{title.slice(0, 2)}</Text>}
          </View>
        </View>
        <View style={{ flex: 1 }}>
          <View style={s.heroChip}><View style={s.heroChipDot} /><Text style={s.heroChipText}>{provider}</Text></View>
          <Text style={[s.detailTitle, { fontSize: Math.min(38.4, Math.max(25.6, width * 0.035)), lineHeight: Math.round(Math.min(38.4, Math.max(25.6, width * 0.035)) * 1.5) }]}>{title}</Text>
          <Text style={s.detailSynopsis}>{item.synopsis || info.synopsis || '—'}</Text>
          <View style={s.detailMeta}>
            <View style={s.pill}><Text style={s.pillText}>{episodes.length} episode</Text></View>
            {(item.genres || item.genre || []).map(g => <View key={g} style={s.pill}><Text style={s.pillText}>{g}</Text></View>)}
            {!!item.score && <View style={s.pill}><Text style={s.pillText}>★ {item.score}</Text></View>}
            {!!item.year && <View style={s.pill}><Text style={s.pillText}>{item.year}</Text></View>}
          </View>
          <View style={s.detailActions}>
            <Btn primary disabled={!episodes.length} onPress={() => episodes[0] && pick(episodes[0], 0)}
                 icon={<Ic.playLg color={C.white} size={20} />}>Putar Episode 1</Btn>
            <Btn ghost onPress={onBack} icon={<Ic.home color={C.fg} size={18} />}>Beranda</Btn>
          </View>
        </View>
      </View>

      <SectionTitle>Episode</SectionTitle>
      {/* eps: auto-fill grid (flex-wrap, min 260px) — semua ukuran layar */}
      <View style={s.eps}>
        {episodes.map((ep, i) => (
          <Pressable key={ep.url} style={({ pressed }) => [s.ep, pressed && { backgroundColor: C.card2 }]} onPress={() => pick(ep, i)}>
            <Text style={s.epNum}>{String(i + 1).padStart(2, '0')}</Text>
            <Text style={s.epTitle} numberOfLines={1}>{ep.title}</Text>
            <Ic.play color={C.muted} size={16} />
          </Pressable>
        ))}
      </View>

      {err && <Text style={[s.hint, s.hintCenter, s.hintCenterBad, { textAlign: 'center' }]}>{err}</Text>}

      <Modal visible={busy} transparent animationType="fade" onRequestClose={() => {}}>
        <View style={s.modalOverlay}>
          <View style={s.modalCard}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12, paddingVertical: 12 }}>
              <Spinner />
              <Text style={s.hint}>Mengambil link download…</Text>
            </View>
          </View>
        </View>
      </Modal>

      {opts && (
        <Modal visible transparent animationType="fade" onRequestClose={() => setOpts(null)}>
          <Pressable style={s.modalOverlay} onPress={() => setOpts(null)}>
            <Pressable style={s.modalCard} onPress={() => {}}>
              <View style={s.optsHead}>
                <Text style={s.optsTitle} numberOfLines={1}>{opts.ep.title}</Text>
                <Pressable style={s.iconBtn} onPress={() => setOpts(null)} hitSlop={8} accessibilityLabel="Tutup pilihan server">
                  <Ic.x color={C.fgDim} size={16} />
                </Pressable>
              </View>
              <ScrollView showsVerticalScrollIndicator={false}>
                {!opts.options.length && <Text style={[s.hint, { textAlign: 'center', paddingVertical: 12 }]}>Tidak ada server kompatibel.</Text>}
                {groups.map(g => {
                  const cur = sel[g.res] || g.options[0].url
                  const picked = g.options.find(o => o.url === cur) ?? g.options[0]
                  return (
                    <View key={g.res} style={[s.optGroup, { marginBottom: 8 }, !desktop && { flexWrap: 'wrap' }]}>
                      <Text style={s.optGroupTitle}>{g.res}</Text>
                      <ResSelect options={g.options} value={cur} onChange={v => setSel(prev => ({ ...prev, [g.res]: v }))} />
                      <View style={[s.optBtns, !desktop && { width: '100%' }]}>
                        <Btn play small onPress={() => onPlay(cur, picked.label, pickedEpIdx)} icon={<Ic.playLg color={C.white} size={16} />}>Play</Btn>
                        <Btn ghost small onPress={() => onDownload({ url: cur, label: picked.label }, opts.ep)} icon={<Ic.down color={C.fg} size={16} />}>Download</Btn>
                      </View>
                    </View>
                  )
                })}
              </ScrollView>
            </Pressable>
          </Pressable>
        </Modal>
      )}
    </View>
  )
}

/* ── Player ─────────────────────────────────────────────── */

interface PlayerViewProps {
  stream: string | null
  error: string | null
  onBack: () => void
  episodes: Ep[]
  currentEpIdx: number | null
  onPlayEp: (idx: number) => void
}

function PlayerView({ stream, error, onBack, episodes, currentEpIdx, onPlayEp }: PlayerViewProps) {
  const hasPrev = (currentEpIdx ?? 0) > 0
  const hasNext = currentEpIdx !== null && currentEpIdx < episodes.length - 1
  const ep = currentEpIdx !== null ? episodes[currentEpIdx] : null
  const loading = !stream && !error

  return (
    <View style={[s.wrap, s.pagePad, s.player]}>
      <Btn ghost style={s.back} onPress={onBack} icon={<Ic.back color={C.fg} size={18} />}>Kembali</Btn>
      {error
        ? <Text style={[s.hint, s.hintCenter, { textAlign: 'center' }]}>{error}</Text>
        : !stream
          ? (
            <View style={[s.hintCenter, { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 80 }]}>
              <Spinner />
              <Text style={s.hint}>Menghubungi server…</Text>
            </View>
          )
          : <VideoCore stream={stream} />}
      {episodes.length > 1 && currentEpIdx !== null && (
        <View style={s.epNav}>
          <Btn ghost small disabled={loading || !hasPrev}
               onPress={() => onPlayEp(currentEpIdx - 1)}
               icon={<Ic.back color={hasPrev ? C.fg : C.muted} size={16} />}>Prev</Btn>
          <Text style={s.epNavTitle} numberOfLines={1}>Ep {currentEpIdx + 1} — {ep?.title || ''}</Text>
          <Btn ghost small disabled={loading || !hasNext}
               onPress={() => onPlayEp(currentEpIdx + 1)}
               icon={<Ic.forward color={hasNext ? C.fg : C.muted} size={16} />}>Next</Btn>
        </View>
      )}
      <Text style={[s.hint, { textAlign: 'center', paddingVertical: 40 }]}>Video tidak muncul? Coba resolusi atau server lain.</Text>
    </View>
  )
}

// VideoWrapper terpisah biar useVideoPlayer (hook) gak pernah conditional.
function VideoCore({ stream }: { stream: string }) {
  const player = useVideoPlayer(stream, p => { p.loop = false; p.play() })
  return <VideoView player={player} style={s.video} contentFit="contain" nativeControls />
}

/* ── Jobs & footer ──────────────────────────────────────── */

interface JobToastsProps {
  jobs: Job[]
}

function JobToasts({ jobs }: JobToastsProps) {
  return (
    <View style={[s.jobToasts, { pointerEvents: 'none' }]}>
      {jobs.slice(-3).map(j => (
        <View key={j.id} style={s.jobToast}>
          <Text style={s.jobTitle} numberOfLines={1}>{j.title}</Text>
          {j.status === 'running' && (
            <>
              <View style={s.bar}>
                <LinearGradient colors={[C.primary, C.accent]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
                                style={[s.barFill, { width: pctWidth(j) }]} />
              </View>
              <Text style={s.dim}>{pct(j)}</Text>
            </>
          )}
          {j.status === 'failed' && <Text style={s.badText}>{j.error}</Text>}
        </View>
      ))}
    </View>
  )
}

function pct(j: Job) {
  return j.total ? `${Math.round((j.done / j.total) * 100)}%` : '…'
}
function pctWidth(j: Job): `${number}%` {
  const done = j.total ? Math.min(1, j.done / j.total) : 0
  return `${Math.round(done * 100)}%`
}

interface FooterProps {
  onJump: (k: string) => void
}

function Footer({ onJump }: FooterProps) {
  const { desktop } = useBrk()
  return (
    <View style={s.footer}>
      <LinearGradient colors={['transparent', 'rgba(0,0,0,0.4)']} start={{ x: 0, y: 0 }} end={{ x: 0, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
      {/* web: grid 2fr 1fr 1fr (desktop) / 1 kolom (mobile) */}
      <View style={[s.footerGrid, desktop ? { flexDirection: 'row', gap: 32 } : { gap: 32 }]}>
        <View style={desktop && { flex: 2 }}>
          <View style={s.logo}>
            <LinearGradient colors={[C.primary, C.accent]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={s.logoMark}>
              <Ic.playLg color={C.white} size={20} />
            </LinearGradient>
            <View style={{ flexDirection: 'row', alignItems: 'flex-end' }}>
              <Text style={s.logoText}>INDO</Text>
              <GradText style={s.logoText} size={18}>NIME</GradText>
            </View>
          </View>
          <Text style={[s.dim, { marginTop: 12 }]}>Streaming anime sub Indo, gratis dan update tiap hari.</Text>
        </View>
        <View style={[s.footerCol, desktop && { flex: 1 }]}>
          <Text style={s.footerTitle}>Jelajah</Text>
          {[
            ['Rilis Terbaru', 'latest'], ['Paling Populer', 'popular'],
          ].map(([text, key]) => (
            <Pressable key={key} onPress={() => onJump(key)}>
              <Text style={s.footerLinkText}>{text}</Text>
            </Pressable>
          ))}
          <Pressable onPress={() => onJump('latest')}>
            <Text style={s.footerLinkText}>Daftar Anime</Text>
          </Pressable>
        </View>
        <View style={[s.footerCol, desktop && { flex: 1 }]}>
          <Text style={s.footerTitle}>Bantuan</Text>
          {['Cara Nonton', 'Lapor Error', 'Disclaimer'].map(t => (
            <Pressable key={t} onPress={() => {}}>
              <Text style={s.footerLinkText}>{t}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      <View style={[s.footerCopy, { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }]}>
        <Text style={s.footerCopyText}>© 2026 Indonime. Dibuat dengan</Text>
        <Ic.star color={C.accent} size={13} />
        <Text style={s.footerCopyText}>untuk pecinta anime.</Text>
      </View>
    </View>
  )
}

/* Ambient glow — LinearGradient replacement for SVG RadialGradient
   (RN SVG RadialGradient percentage attrs unreliable on Android → solid fills) */
function AmbientGlow() {
  return (
    <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, pointerEvents: 'none' }} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <LinearGradient colors={['rgba(124,58,237,0.12)', 'transparent']} start={{ x: 1, y: 0 }} end={{ x: 0.3, y: 0.5 }} style={StyleSheet.absoluteFill} />
      <LinearGradient colors={['rgba(244,63,94,0.06)', 'transparent']} start={{ x: 0, y: 0.3 }} end={{ x: 0.5, y: 0.7 }} style={StyleSheet.absoluteFill} />
    </View>
  )
}

/* ── UI atoms ───────────────────────────────────────────── */

function Spinner() {
  const a = useRef(new Animated.Value(0)).current
  useEffect(() => {
    const anim = Animated.loop(Animated.timing(a, { toValue: 1, duration: 800, useNativeDriver: Platform.OS !== 'web' }))
    anim.start()
    return () => anim.stop()
  }, [a])
  const rotate = a.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] })
  return <Animated.View style={[s.spinner, { transform: [{ rotate }] }]} />
}

interface ShimmerProps {
  style?: StyleProp<ViewStyle>
  children?: ReactNode
  delay?: number
}

function Shimmer({ style, children, delay = 0 }: ShimmerProps) {
  const o = useRef(new Animated.Value(0.55)).current
  useEffect(() => {
    const anim = Animated.loop(Animated.sequence([
      Animated.delay(delay),
      Animated.timing(o, { toValue: 1, duration: 600, useNativeDriver: Platform.OS !== 'web' }),
      Animated.timing(o, { toValue: 0.55, duration: 600, useNativeDriver: Platform.OS !== 'web' }),
    ]))
    anim.start()
    return () => anim.stop()
  }, [o, delay])
  return <Animated.View style={[style, { opacity: o }]}>{children}</Animated.View>
}

/* Text gradien (pengganti background-clip: text) — logo NIME, angka stats, rank.
   Baseline SvgText = 0.97em di box 1.2em (≈ web line box: baseline ~0.97em, descender 0.23em).
   Callers yang menyandingkan GradText dgn Text asli (logo INDO+NIME) harus align bottom
   (flex-end) — RN tidak bisa baseline-align View. Ponytail: lebar dihitung heuristik
   (chars × size × 0.62); kalau butuh tepat, callers bisa kasih prop `width`. */
let _gid = 0
interface GradTextProps {
  children: ReactNode
  style?: StyleProp<ViewStyle> | StyleProp<TextStyle>
  size?: number
  center?: boolean
  width?: number
  colors?: [string, string]
  horizontal?: boolean
  weight?: number | string
}

function GradText({ children, style, size = 22, center = false, width, colors = [C.primary2, C.accent], horizontal = true, weight = 800 }: GradTextProps) {
  const id = useRef(`gt${++_gid}`).current
  const w = width || Math.ceil(String(children).length * size * 0.62)
  const h = Math.ceil(size * 1.2)
  return (
    // callers kirim TextStyle (logoText/statNum/popRank); View terima keduanya di runtime
    <View style={[style, { width: w, height: h }] as unknown as StyleProp<ViewStyle>}>
      <Svg width={w} height={h}>
        <Defs>
          <SvgGrad id={id} x1="0" y1="0" x2={horizontal ? '1' : '0'} y2={horizontal ? '0' : '1'}>
            <Stop offset="0" stopColor={colors[0]} />
            <Stop offset="1" stopColor={colors[1]} />
          </SvgGrad>
        </Defs>
        <SvgText x={center ? w / 2 : 0} y={size * 0.97} textAnchor={center ? 'middle' : 'start'}
                 fontSize={size} fontFamily="Outfit_800ExtraBold" fontWeight={weight} fill={`url(#${id})`}>
          {children}
        </SvgText>
      </Svg>
    </View>
  )
}