// Indonime — React Native (Expo SDK 57)
// Port pixel-faithful dari ui/ (React web). Backend: Python (indonime/), port 8756.
import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import {
  Animated, BackHandler, Modal, Platform, Pressable, ScrollView,
  StyleSheet, Text, TextInput, useWindowDimensions, View,
} from 'react-native'
import { LinearGradient } from 'expo-linear-gradient'
import { Image } from 'expo-image'
import { VideoView, useVideoPlayer } from 'expo-video'
import { StatusBar } from 'expo-status-bar'
import Svg, { Defs, LinearGradient as SvgGrad, RadialGradient, Rect, Stop, Text as SvgText } from 'react-native-svg'
import { useFonts, Outfit_500Medium, Outfit_700Bold, Outfit_800ExtraBold } from '@expo-google-fonts/outfit'
import { Rubik_400Regular, Rubik_500Medium, Rubik_600SemiBold } from '@expo-google-fonts/rubik'

import { api, API_URL } from './src/api'
import { Ic } from './src/icons'
import { C, F } from './src/theme'
import { s } from './src/styles'

const HERO_MS = 6000
const BRK = 900 // breakpoint web @media (max-width: 900px)

// Breakpoint context: desktop = lebar ≥ 900px (layout web penuh); else layout mobile
const Brk = createContext({ desktop: false, width: 0 })
const useBrk = () => useContext(Brk)

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
  const [top, setTop] = useState([])
  const [seasonal, setSeasonal] = useState([])
  const [latest, setLatest] = useState(null)
  const [genres, setGenres] = useState(['Semua'])
  const [genre, setGenre] = useState('Semua')
  const [genreItems, setGenreItems] = useState(null)
  const [genreLoading, setGenreLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [cands, setCands] = useState(null)
  const [view, setView] = useState('home')
  const [anime, setAnime] = useState(null)
  const [stream, setStream] = useState(null)
  const [streamError, setStreamError] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState(null)
  const [jobs, setJobs] = useState([])
  const scrollRef = useRef(null)

  const scrollTop = () => scrollRef.current?.scrollTo({ y: 0, animated: false })

  useEffect(() => {
    let alive = true
    api.discover('top').then(r => alive && setTop(r.items)).catch(() => {})
    api.discover('season').then(r => alive && setSeasonal(r.items)).catch(() => {})
    api.discover('latest').then(r => alive && setLatest(r.items)).catch(() => {})
    api.discover('genres').then(r => alive && setGenres(['Semua', ...r.genres])).catch(() => {})
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
    setSearching(true)
    api.discover('search', 'q=' + encodeURIComponent(q))
      .then(r => setResults(r.results))
      .catch(err => setError(err.message))
      .finally(() => setSearching(false))
  }

  const goHome = () => { setView('home'); setResults(null); setQuery(''); setCands(null); setGenre('Semua'); scrollTop() }

  const pickGenre = g => {
    setGenre(g); setGenreItems(null)
    if (g === 'Semua') return
    setGenreLoading(true)
    api.discover('genre', 'genre=' + encodeURIComponent(g))
      .then(r => setGenreItems(r.items))
      .catch(err => setError(err.message))
      .finally(() => setGenreLoading(false))
  }

  const openDetail = (item, prov, url) => {
    setBusy('Memuat detail...')
    Promise.all([api.info(url, prov), api.episodes(url, prov)])
      .then(([info, eps]) => {
        setAnime({ item, provider: prov, url, info: info.info, episodes: eps.episodes })
        setView('anime'); setResults(null); setCands(null)
        scrollTop()
      })
      .catch(err => setError(err.message))
      .finally(() => setBusy(''))
  }

  const pickAnime = async item => {
    setBusy('Mencari sumber...')
    try {
      if (item.url) {  // shape Rilis Terbaru: url provider langsung
        const prov = item.url.includes('otakudesu') ? 'otakudesu' : 'anoboy'
        return openDetail(item, prov, item.url)
      }
      const { sources, candidates } = await api.resolve(item.id, item.title)
      for (const [prov, url] of Object.entries(sources)) {
        // gap-fill: provider pertama yang sukses; gagal → coba berikutnya
        try {
          const [info, eps] = await Promise.all([api.info(url, prov), api.episodes(url, prov)])
          setAnime({ item, provider: prov, url, info: info.info, episodes: eps.episodes })
          setView('anime'); setResults(null); setCands(null)
          scrollTop()
          return
        } catch { /* coba provider lain */ }
      }
      setCands(candidates)  // resolve kosong / semua gagal → pilih manual
    } catch (err) { setError(err.message) }
    finally { setBusy('') }
  }

  const pickCandidate = (prov, url) => openDetail(null, prov, url)

  const handlePlay = async (url, label) => {
    // Langsung pindah ke halaman nonton — loading resolve stream di player.
    setView('player'); setStream(null); setStreamError(null); scrollTop()
    try {
      const r = await api.play(url, label)
      if (r.stream) setStream(r.stream.startsWith('http') ? r.stream : API_URL + r.stream)
      else setStreamError(r.error || 'Gagal memutar')
    } catch (err) { setStreamError(err.message) }
  }

  const handleDownload = (opt, ep) => {
    const base = (anime.info.title || (anime.item && anime.item.title) || '').replace(/\s+Subtitle Indonesia.*$/i, '')
    api.download(opt.url, `${base} — ${ep.title}`).catch(err => setError(err.message))
  }

  if (!fontsLoaded) return null

  return (
    <View style={s.app}>
      {Platform.OS !== 'web' && <StatusBar style="light" backgroundColor={C.bg} />}
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
          <PlayerView stream={stream} error={streamError} onBack={() => setView('anime')} />
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
const sectionY = {}

/* ── Header ─────────────────────────────────────────────── */

function Topbar({ query, setQuery, onSubmit, onHome }) {
  const { desktop, width } = useBrk()
  if (desktop) {
    // Layout desktop: satu baris 64px — logo | search (flex, max 360, kanan)
    return (
      <View style={[s.topbar, { paddingVertical: 0 }]}>
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
    <View style={s.topbar}>
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

function LogoButton({ onPress }) {
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

function SearchBox({ query, setQuery, onSubmit, style }) {
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

function HomeView({ top, seasonal, latest, genres, genre, onGenrePick, genreItems, genreLoading, results, searching, query, onPick, scrollRef }) {
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

function StatCard({ value, label, style }) {
  return (
    <View style={[s.statCard, style]}>
      <LinearGradient colors={[C.card, C.bg2]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[StyleSheet.absoluteFill, Platform.OS === 'web' && { zIndex: -1 }]} />
      <GradText style={s.statNum} size={26}>{String(value)}</GradText>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  )
}

function Rail({ title, icon, toolbar, children, wide }) {
  const { desktop } = useBrk()
  const scroll = useRef(null)
  const xRef = useRef(0)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(true)
  const step = wide ? 360 : 200

  const evalArrows = e => {
    const x = e.nativeEvent.contentOffset.x
    const mw = e.nativeEvent.layoutMeasurement.width
    const cw = e.nativeEvent.contentSize.width
    xRef.current = x
    setCanLeft(x > 4)
    setCanRight(x < cw - mw - 4)
  }
  const go = d => scroll.current?.scrollTo({ x: Math.max(0, xRef.current + d * step), animated: true })

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

function Hero({ items, onPick }) {
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
    if (next?.image_full || next?.image) Image.prefetch(next.image_full || next.image)
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

function HeroImg({ it, style }) {
  const [src, setSrc] = useState(it.image_full || it.image || '')
  useEffect(() => { setSrc(it.image_full || it.image || '') }, [it])
  if (!src) return null
  return <Image source={{ uri: src }} contentFit="cover" blurRadius={28} transition={300} style={style} onError={() => setSrc('')} />
}

/* ── Cards & sections ───────────────────────────────────── */

function SectionTitle({ children, icon }) {
  return (
    <View style={s.sectionTitleRow}>
      {icon && <View style={s.sectionIcon}>{icon}</View>}
      <Text style={s.sectionTitle}>{children}</Text>
      <LinearGradient colors={[C.border, 'transparent']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ flex: 1, height: 1, marginLeft: 8 }} />
    </View>
  )
}

function GenreChips({ genres, active, onPick }) {
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

function Card({ item, badge, sub, meta, i, onPick, style }) {
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
        {sub && <Text style={s.cardSub}>{sub}</Text>}
        {meta && <Text style={s.cardMeta}>{meta}</Text>}
      </View>
    </Pressable>
  )
}

function SkeletonRail({ n, wide }) {
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

function RankCard({ item, i, onPick }) {
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

function Poster({ item, style, children }) {
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

function Btn({ primary, play, ghost, small, disabled, onPress, icon, children, style }) {
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

function ResSelect({ options, value, onChange }) {
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

function AnimeView({ anime, onPlay, onDownload, onBack }) {
  const { desktop, width } = useBrk()
  const [opts, setOpts] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [sel, setSel] = useState({})
  const item = anime.item || {}
  const { info, episodes, provider } = anime
  const title = info.title || item.title

  const pick = async ep => {
    setBusy(true); setErr(null); setOpts(null)
    try { setOpts({ ep, options: (await api.downloads(ep.url, provider)).options }) }
    catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  const pickList = useMemo(() => (opts ? [...opts.options].reverse() : []), [opts])

  const groups = useMemo(() => {
    const map = new Map()
    // Browser tak bisa decode MKV — sama spt web, hidden utk player mobile.
    // TUI/mpv path tetap nge-serve.
    pickList.filter(o => !/mkv/i.test(o.label)).forEach(o => {
      const m = o.label.match(/^\[(.+?)\]\s*(.*)$/)
      const res = m ? m[1] : 'Lainnya'
      const name = m ? m[2] : o.label
      if (!map.has(res)) map.set(res, [])
      map.get(res).push({ name, url: o.url, label: o.label })
    })
    return [...map.entries()].map(([res, options]) => ({ res, options }))
  }, [pickList])

  const epCols = desktop ? Math.max(1, Math.floor((Math.min(width, 1200) - 40 + 8) / 268)) : 1
  const epW = epCols > 1 ? (Math.min(width, 1200) - 40 - 8 * (epCols - 1)) / epCols : null

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
            <Btn primary disabled={!episodes.length} onPress={() => episodes[0] && pick(episodes[0])}
                 icon={<Ic.playLg color={C.white} size={20} />}>Putar Episode 1</Btn>
            <Btn ghost onPress={onBack} icon={<Ic.home color={C.fg} size={18} />}>Beranda</Btn>
          </View>
        </View>
      </View>

      <SectionTitle>Episode</SectionTitle>
      {/* eps web: auto-fill minmax(260px,1fr) gap 8 — mobile 1 kolom */}
      <View style={[s.eps, desktop && { flexDirection: 'row', flexWrap: 'wrap' }]}>
        {episodes.map((ep, i) => (
          <Pressable key={ep.url} style={({ pressed }) => [s.ep, epW && { width: epW }, pressed && { backgroundColor: C.card2 }]} onPress={() => pick(ep)}>
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
                  const picked = g.options.find(o => o.url === cur)
                  return (
                    <View key={g.res} style={[s.optGroup, { marginBottom: 8 }, !desktop && { flexWrap: 'wrap' }]}>
                      <Text style={s.optGroupTitle}>{g.res}</Text>
                      <ResSelect options={g.options} value={cur} onChange={v => setSel(prev => ({ ...prev, [g.res]: v }))} />
                      <View style={[s.optBtns, !desktop && { width: '100%' }]}>
                        <Btn play small onPress={() => onPlay(cur, picked.label)} icon={<Ic.playLg color={C.white} size={16} />}>Play</Btn>
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

function PlayerView({ stream, error, onBack }) {
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
      <Text style={[s.hint, { textAlign: 'center', paddingVertical: 40 }]}>Video tidak muncul? Coba resolusi atau server lain.</Text>
    </View>
  )
}

// VideoWrapper terpisah biar useVideoPlayer (hook) gak pernah conditional.
function VideoCore({ stream }) {
  const player = useVideoPlayer(stream, p => { p.loop = false; p.play() })
  return <VideoView player={player} style={s.video} contentFit="contain" nativeControls />
}

/* ── Jobs & footer ──────────────────────────────────────── */

function JobToasts({ jobs }) {
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

function pct(j) {
  return j.total ? `${Math.round((j.done / j.total) * 100)}%` : '…'
}
function pctWidth(j) {
  const done = j.total ? Math.min(1, j.done / j.total) : 0
  return `${Math.round(done * 100)}%`
}

function Footer({ onJump }) {
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

/* Ambient glow — radial gradients body web (violet kanan-atas, rose kiri-tengah) */
function AmbientGlow() {
  return (
    <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, pointerEvents: 'none' }}>
      <Svg style={StyleSheet.absoluteFill} width="100%" height="100%">
        <Defs>
          <RadialGradient id="glowViolet" cx="80%" cy="0%" r="75%">
            <Stop offset="0" stopColor="rgba(124,58,237,0.14)" />
            <Stop offset="0.6" stopColor="rgba(124,58,237,0)" />
          </RadialGradient>
          <RadialGradient id="glowRose" cx="0%" cy="35%" r="60%">
            <Stop offset="0" stopColor="rgba(244,63,94,0.08)" />
            <Stop offset="0.55" stopColor="rgba(244,63,94,0)" />
          </RadialGradient>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#glowViolet)" />
        <Rect width="100%" height="100%" fill="url(#glowRose)" />
      </Svg>
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

function Shimmer({ style, children, delay = 0 }) {
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
function GradText({ children, style, size = 22, center = false, width, colors = [C.primary2, C.accent], horizontal = true, weight = 800 }) {
  const id = useRef(`gt${++_gid}`).current
  const w = width || Math.ceil(String(children).length * size * 0.62)
  const h = Math.ceil(size * 1.2)
  return (
    <View style={[style, { width: w, height: h }]}>
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
