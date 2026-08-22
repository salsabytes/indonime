import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'

const _noPoster = new Set()
const HERO_MS = 6000

const Ic = {
  search: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>,
  play: <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M8 5.14v13.72a1 1 0 0 0 1.5.86l11-6.86a1 1 0 0 0 0-1.72l-11-6.86a1 1 0 0 0-1.5.86Z" /></svg>,
  playLg: <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M8 5.14v13.72a1 1 0 0 0 1.5.86l11-6.86a1 1 0 0 0 0-1.72l-11-6.86a1 1 0 0 0-1.5.86Z" /></svg>,
  down: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3v12" /><path d="m7 11 5 5 5-5" /><path d="M4 21h16" /></svg>,
  back: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M19 12H5" /><path d="m12 19-7-7 7-7" /></svg>,
  home: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3 10 9-7 9 7v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" /></svg>,
  x: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>,
  chev: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>,
  flame: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" /></svg>,
  clock: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>,
  star: <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>,
  chev: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>,
}

export default function App() {
  const [providers, setProviders] = useState([])
  const [provider, setProvider] = useState('otakudesu')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [catalog, setCatalog] = useState(null)
  const [featured, setFeatured] = useState([])
  const [latest, setLatest] = useState(null)
  const [genre, setGenre] = useState('Semua')
  const [view, setView] = useState('home')
  const [anime, setAnime] = useState(null)
  const [stream, setStream] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState(null)
  const [jobs, setJobs] = useState([])
  const searchRef = useRef(null)

  useEffect(() => {
    api.providers().then(r => setProviders(r.providers)).catch(() => {})
  }, [])

  useEffect(() => {
    let alive = true
    setCatalog(null); setFeatured([]); setLatest(null)
    api.catalog(provider).then(r => alive && setCatalog(r.catalog)).catch(() => {})
    api.home(provider).then(r => alive && setFeatured(r.items)).catch(() => {})
    api.latest(provider).then(r => alive && setLatest(r.items)).catch(() => {})
    return () => { alive = false }
  }, [provider])

  useEffect(() => {
    const t = setInterval(() => api.jobs().then(r => setJobs(r.jobs)).catch(() => {}), 1500)
    return () => clearInterval(t)
  }, [])

  const onSearch = async e => {
    e.preventDefault()
    const q = query.trim()
    if (!q) return setResults(null)
    setSearching(true)
    try { setResults((await api.search(q, provider)).results) }
    catch (err) { setError(err.message) }
    finally { setSearching(false) }
  }

  const goHome = () => { setView('home'); setResults(null); setQuery('') }

  const pickAnime = async item => {
    setBusy('Memuat detail...')
    try {
      const [info, eps] = await Promise.all([
        api.info(item.url, provider), api.episodes(item.url, provider),
      ])
      setAnime({ item, info: info.info, episodes: eps.episodes })
      setView('anime'); setResults(null)
      window.scrollTo({ top: 0 })
    } catch (err) { setError(err.message) }
    finally { setBusy('') }
  }

  const handlePlay = async url => {
    setBusy('Menghubungi server...')
    try {
      const r = await api.play(url)
      if (r.stream) { setStream(r.stream); setView('player') }
      else if (r.mpv) setBusy('Diputar di mpv — tutup mpv untuk lanjut')
      else setError(r.error || 'Gagal memutar')
    } catch (err) { setError(err.message) }
    finally { setBusy('') }
  }

  const handleDownload = (opt, ep) => {
    const base = (anime.info.title || anime.item.title).replace(/\s+Subtitle Indonesia.*$/i, '')
    api.download(opt.url, `${base} — ${ep.title}`).catch(err => setError(err.message))
  }

  const genres = useMemo(() => {
    const s = new Set((catalog || []).flatMap(i => i.genre || []))
    return ['Semua', ...s]
  }, [catalog])

  const onPickResult = item => {
    pickAnime(item)
    if (searchRef.current) searchRef.current.focus()
  }

  return (
    <div className="app">
      <Header providers={providers} provider={provider} setProvider={setProvider}
              query={query} setQuery={setQuery} onSearch={onSearch} onHome={goHome}
              searchRef={searchRef} />

      {error && (
        <div className="toast error-toast" role="alert">
          <span>{error}</span>
          <button className="icon-btn" onClick={() => setError(null)} aria-label="Tutup">{Ic.x}</button>
        </div>
      )}
      {busy && (
        <div className="toast busy-toast" role="status">
          <span className="spinner" />{busy}
        </div>
      )}

      <main>
        {view === 'home' && (
          <HomeView featured={featured} catalog={catalog} latest={latest}
                    results={results} searching={searching} query={query}
                    provider={provider} genres={genres} genre={genre} setGenre={setGenre}
                    onPick={onPickResult} />
        )}
        {view === 'anime' && anime && (
          <AnimeView anime={anime} provider={provider} onPlay={handlePlay}
                     onDownload={handleDownload} onBack={goHome} />
        )}
        {view === 'player' && stream && (
          <PlayerView stream={stream} onBack={() => setView('anime')} />
        )}
      </main>

      {view === 'home' && <Footer />}
      {jobs.length > 0 && <JobToasts jobs={jobs} />}
    </div>
  )
}

/* ── Header ─────────────────────────────────────────────── */

function Header({ providers, provider, setProvider, query, setQuery, onSearch, onHome, searchRef }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button className="logo" onClick={onHome} aria-label="Indonime — beranda">
          <span className="logo-mark">{Ic.playLg}</span>
          <span className="logo-text">INDO<span>NIME</span></span>
        </button>
        <nav className="tabs" role="tablist" aria-label="Pilih sumber">
          {providers.map(p => (
            <button key={p} role="tab" aria-selected={p === provider}
                    className={`tab ${p === provider ? 'on' : ''}`}
                    onClick={() => setProvider(p)}>{p}</button>
          ))}
        </nav>
        <form className="search" onSubmit={onSearch} role="search">
          <input ref={searchRef} value={query} onChange={e => setQuery(e.target.value)}
                 placeholder="Cari anime…" aria-label="Cari anime" />
          <button type="submit" aria-label="Cari">{Ic.search}</button>
        </form>
        <button className="icon-btn home-btn" onClick={onHome} aria-label="Beranda">{Ic.home}</button>
      </div>
    </header>
  )
}

/* ── Home ───────────────────────────────────────────────── */

function HomeView({ featured, catalog, latest, results, searching, query, provider, genres, genre, setGenre, onPick }) {
  if (searching) return <p className="hint center"><span className="spinner" />Mencari…</p>

  if (results) {
    return (
      <div className="wrap page-pad">
        <section>
          <SectionTitle icon={Ic.search}>Hasil untuk “{query}”</SectionTitle>
          {results.length === 0
            ? <p className="hint center">Tidak ada hasil. Coba judul lain.</p>
            : <div className="grid">{results.map((it, i) => <Card key={it.url} item={it} i={i} provider={provider} onPick={onPick} />)}</div>}
        </section>
      </div>
    )
  }

  return (
    <>
      {featured.length > 0 && <Hero items={featured} provider={provider} onPick={onPick} />}

      <div className="wrap page-pad">
        <section className="stats" aria-label="Statistik">
          <div><strong>{catalog?.length || '—'}</strong><span>Judul anime</span></div>
          <div><strong>4K</strong><span>Kualitas stream</span></div>
          <div><strong>24/7</strong><span>Update episode</span></div>
        </section>

        <section aria-labelledby="latest-title">
          <Rail title="Rilis Terbaru" icon={Ic.clock} id="latest-title"
                toolbar={genres.length > 1
                  ? <GenreChips genres={genres} active={genre} onPick={setGenre} />
                  : null}>
            {!latest
              ? <SkeletonRail n={8} />
              : latest.filter(i => genre === 'Semua' || (i.genre || []).includes(genre)).map((it, i) => (
                  <Card key={it.url} item={it} i={i} provider={provider} onPick={onPick} />
                ))}
          </Rail>
        </section>

        <section aria-labelledby="popular-title">
          <Rail title="Paling Populer" icon={Ic.flame} id="popular-title" wide>
            {!catalog
              ? <SkeletonRail n={5} wide />
              : catalog.slice(0, 8).map((it, i) => (
                  <RankCard key={it.url} item={it} i={i} provider={provider} onPick={onPick} />
                ))}
          </Rail>
        </section>
      </div>
    </>
  )
}

function Rail({ title, icon, id, toolbar, children, wide }) {
  const ref = useRef(null)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(true)

  const onScroll = () => {
    const el = ref.current
    if (!el) return
    setCanLeft(el.scrollLeft > 4)
    setCanRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4)
  }

  useEffect(() => {
    onScroll()
    const el = ref.current
    el?.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      el?.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [children])

  const step = wide ? 360 : 200
  const go = d => ref.current?.scrollBy({ left: d * step, behavior: 'smooth' })

  return (
    <section aria-labelledby={id}>
      <div className="section-head">
        <SectionTitle id={id} icon={icon}>{title}</SectionTitle>
        <div className="rail-arrows">
          <button className="rail-btn" onClick={() => go(-1)} disabled={!canLeft}
                  aria-label={`Geser ${title} ke kiri`}>‹</button>
          <button className="rail-btn" onClick={() => go(1)} disabled={!canRight}
                  aria-label={`Geser ${title} ke kanan`}>›</button>
        </div>
      </div>
      {toolbar}
      <div className={`rail${wide ? ' wide' : ''}`} ref={ref}>{children}</div>
    </section>
  )
}

function Hero({ items, provider, onPick }) {
  const [idx, setIdx] = useState(0)
  const [paused, setPaused] = useState(false)
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const slides = items.slice(0, 6)
  const n = slides.length
  const it = slides[idx]
  const go = i => setIdx((i + n) % n)

  useEffect(() => {
    if (reduced || paused || n < 2) return
    const t = setInterval(() => setIdx(i => (i + 1) % n), HERO_MS)
    return () => clearInterval(t)
  }, [paused, n, reduced])

  useEffect(() => {
    if (n < 2) return
    const img = new Image()
    img.src = slides[(idx + 1) % n].image_full || slides[(idx + 1) % n].image || ''
  }, [idx, slides, n])

  if (!it) return null

  return (
    <section className="hero"
             onMouseEnter={() => setPaused(true)}
             onMouseLeave={() => setPaused(false)}>
      <div className="hero-backdrop" key={`b${idx}`} aria-hidden="true">
        <HeroImg it={it} className="hero-bg" />
        <div className="hero-veil" />
      </div>

      <div className="hero-content wrap" key={`c${idx}`}>
        <div className="hero-text">
          <span className="hero-chip"><i aria-hidden="true" />{provider}</span>
          <h1>{it.title}</h1>
          {it.synopsis && <p className="hero-synopsis">{it.synopsis}</p>}
          <div className="hero-actions">
            <button className="btn primary" onClick={() => onPick(it)}>{Ic.playLg} Lihat Detail</button>
            {it.ep && <button className="btn ghost" onClick={() => onPick(it)}>{Ic.clock} Episode {it.ep}</button>}
          </div>
        </div>
        <img className="hero-cover" src={it.image_full || it.image} alt=""
             onError={e => (e.currentTarget.style.display = 'none')} />
      </div>

      {n > 1 && (
        <>
          <button className="hero-arrow left" onClick={() => go(idx - 1)} aria-label="Slide sebelumnya">‹</button>
          <button className="hero-arrow right" onClick={() => go(idx + 1)} aria-label="Slide berikutnya">›</button>
          <div className="hero-segs" role="tablist" aria-label="Navigasi slide">
            {slides.map((s, i) => (
              <button key={i} className={`hero-seg${i === idx ? ' on' : ''}`}
                      onClick={() => go(i)} aria-label={`Slide ${i + 1}: ${s.title}`}
                      aria-current={i === idx ? 'true' : undefined}>
                {i === idx && (
                  <span key={`f${idx}`} className="hero-seg-fill"
                        style={{ animationPlayState: paused ? 'paused' : 'running' }}
                        onAnimationEnd={reduced ? null : () => go(idx + 1)} />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  )
}

function HeroImg({ it, className }) {
  const [src, setSrc] = useState(it.image_full || it.image || '')
  useEffect(() => { setSrc(it.image_full || it.image || '') }, [it])
  if (!src) return null
  // otakudesu covers are low-res; always blur so the full-bleed hero never shows pixels.
  return <img src={src} alt="" className={className} onError={() => setSrc('')} />
}

/* ── Cards & sections ───────────────────────────────────── */

function SectionTitle({ children, icon, id }) {
  return (
    <h2 className="section-title" id={id}>
      <span className="section-icon">{icon}</span>
      {children}
    </h2>
  )
}

function GenreChips({ genres, active, onPick }) {
  return (
    <div className="chips" role="list" aria-label="Filter genre">
      {genres.map(g => (
        <button key={g} role="listitem"
                className={`chip ${g === active ? 'on' : ''}`}
                aria-pressed={g === active}
                onClick={() => onPick(g)}>{g}</button>
      ))}
    </div>
  )
}

function Card({ item, badge, sub, meta, i, onPick, provider }) {
  return (
    <button className="card" onClick={() => onPick(item)}
            style={{ animationDelay: `${Math.min(i, 14) * 40}ms` }}>
      <span className="card-poster">
        <Poster item={item} provider={provider} />
        {badge && <span className="ep-badge">{badge}</span>}
      </span>
      <span className="card-body">
        <span className="card-title">{item.title}</span>
        {sub && <span className="card-sub">{sub}</span>}
        {meta && <span className="card-meta">{meta}</span>}
      </span>
    </button>
  )
}

function SkeletonRail({ n, wide }) {
  return (
    <div className={`rail${wide ? ' wide' : ''}`} aria-hidden="true">
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className={`card skeleton${wide ? ' rank' : ''}`}
             style={{ animationDelay: `${Math.min(i, 14) * 40}ms` }}>
          <div className="poster shimmer" />
          <span className="skeleton-line" />
          <span className="skeleton-line short" />
        </div>
      ))}
    </div>
  )
}

function RankCard({ item, i, onPick, provider }) {
  return (
    <button className="rank-card" onClick={() => onPick(item)}
            style={{ animationDelay: `${Math.min(i, 14) * 40}ms` }}>
      <span className="pop-rank" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
      <span className="pop-poster">
        <Poster item={item} provider={provider} />
        <span className="pop-play">{Ic.play}</span>
      </span>
      <span className="pop-body">
        <span className="pop-title">{item.title}</span>
        {(item.ep || (item.genre || []).length > 0) && (
          <span className="pop-meta">
            {[item.ep ? `${item.ep} episode` : '', (item.genre || []).slice(0, 2).join(' · ')]
              .filter(Boolean).join(' · ')}
          </span>
        )}
      </span>
      <span className="pop-go">{Ic.chev}</span>
    </button>
  )
}

function useInView(ref) {
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ob = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setInView(true); ob.disconnect() }
    }, { rootMargin: '300px' })
    ob.observe(el)
    return () => ob.disconnect()
  }, [])
  return inView
}

function Poster({ item, provider }) {
  const ref = useRef(null)
  const inView = useInView(ref)
  const [img, setImg] = useState(item.image || '')
  const url = item.url

  useEffect(() => {
    if (img || !inView || _noPoster.has(url)) return
    let alive = true
    api.poster(url, provider)
      .then(r => {
        if (r.image) { if (alive) setImg(r.image) }
        else _noPoster.add(url)
      })
      .catch(() => _noPoster.add(url))
    return () => { alive = false }
  }, [inView, url, img])

  if (img) {
    return (
      <span className="poster" ref={ref}>
        <img src={img} alt="" loading="lazy" />
      </span>
    )
  }
  return (
    <span className="poster placeholder shimmer" ref={ref} aria-hidden="true">
      <span>{item.title.slice(0, 2)}</span>
    </span>
  )
}

/* ── Anime detail ───────────────────────────────────────── */

function ResSelect({ options, value, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const cur = options.find(o => o.url === value) || options[0]

  useEffect(() => {
    if (!open) return
    const out = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    const esc = e => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', out)
    window.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', out); window.removeEventListener('keydown', esc) }
  }, [open])

  return (
    <div className="rselect" ref={ref}>
      <button type="button" className="rselect-btn" aria-haspopup="listbox" aria-expanded={open}
              onClick={() => setOpen(o => !o)}>
        <span>{cur.name}</span>{Ic.chev}
      </button>
      {open && (
        <ul className="rselect-menu" role="listbox">
          {options.map(o => (
            <li key={o.url} role="option" aria-selected={o.url === cur.url}
                className={o.url === cur.url ? 'on' : ''}
                onClick={() => { onChange(o.url); setOpen(false) }}>
              {o.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function AnimeView({ anime, provider, onPlay, onDownload, onBack }) {
  const [opts, setOpts] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [sel, setSel] = useState({})
  const { item, info, episodes } = anime
  const title = info.title || item.title

  const pick = async ep => {
    setBusy(true); setErr(null); setOpts(null)
    try { setOpts({ ep, options: (await api.downloads(ep.url, '')).options }) }
    catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  const pickList = useMemo(() => (opts ? [...opts.options].reverse() : []), [opts])

  const groups = useMemo(() => {
    const map = new Map()
    // Browser can't decode MKV (Matroska) — hide those from web playback.
    // The TUI/mpv path still serves them.
    pickList.filter(o => !/mkv/i.test(o.label)).forEach(o => {
      const m = o.label.match(/^\[(.+?)\]\s*(.*)$/)
      const res = m ? m[1] : 'Lainnya'
      const name = m ? m[2] : o.label
      if (!map.has(res)) map.set(res, [])
      map.get(res).push({ name, url: o.url, label: o.label })
    })
    return [...map.entries()].map(([res, options]) => ({ res, options }))
  }, [pickList])

  useEffect(() => {
    if (!opts) return
    const h = e => { if (e.key === 'Escape') setOpts(null) }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [opts])

  return (
    <div className="wrap page-pad anime">
      <button className="btn ghost back" onClick={onBack}>{Ic.back} Kembali</button>

      <header className="detail-hero">
        <div className="detail-poster">
          {info.image
            ? <img src={info.image} alt={title} />
            : <div className="detail-poster placeholder">{title.slice(0, 2)}</div>}
        </div>
        <div className="detail-body">
          <span className="hero-chip"><i aria-hidden="true" />{provider}</span>
          <h1>{title}</h1>
          <p className="detail-synopsis">{info.synopsis || '—'}</p>
          <div className="detail-meta">
            <span className="pill">{episodes.length} episode</span>
            {(item.genre || []).map(g => <span key={g} className="pill">{g}</span>)}
          </div>
          <div className="detail-actions">
            <button className="btn primary" onClick={() => episodes[0] && pick(episodes[0])}
                    disabled={!episodes.length}>{Ic.playLg} Putar Episode 1</button>
            <button className="btn ghost" onClick={onBack}>{Ic.home} Beranda</button>
          </div>
        </div>
      </header>

      <h2 className="section-title">Episode</h2>
      <div className="eps">
        {episodes.map((ep, i) => (
          <button key={ep.url} className="ep" onClick={() => pick(ep)}>
            <span className="ep-num">{String(i + 1).padStart(2, '0')}</span>
            <span className="ep-title">{ep.title}</span>
            <span className="ep-go">{Ic.play}</span>
          </button>
        ))}
      </div>

      {err && <p className="hint center bad">{err}</p>}

      {busy && (
        <div className="modal"><div className="modal-card">
          <p className="hint center"><span className="spinner" />Mengambil link download…</p>
        </div></div>
      )}

      {opts && (
        <div className="modal" role="dialog" aria-modal="true"
             onClick={e => { if (e.target === e.currentTarget) setOpts(null) }}>
          <div className="modal-card">
            <div className="opts-head">
              <h3>{opts.ep.title}</h3>
              <button className="icon-btn" autoFocus onClick={() => setOpts(null)} aria-label="Tutup pilihan server">{Ic.x}</button>
            </div>
            <div className="modal-body">
              {!opts.options.length && <p className="hint center">Tidak ada server kompatibel.</p>}
              {groups.map(g => {
                const cur = sel[g.res] || g.options[0].url
                const picked = g.options.find(o => o.url === cur)
                return (
                  <div key={g.res} className="opt-group">
                    <span className="opt-group-title">{g.res}</span>
                    <ResSelect options={g.options} value={cur}
                               onChange={v => setSel(s => ({ ...s, [g.res]: v }))} />
                    <div className="opt-btns">
                      <button className="btn play" onClick={() => onPlay(cur)}>{Ic.playLg} Play</button>
                      <button className="btn ghost" onClick={() => onDownload({ url: cur, label: picked.label }, opts.ep)}>{Ic.down} Download</button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Player ─────────────────────────────────────────────── */

function PlayerView({ stream, onBack }) {
  return (
    <div className="wrap page-pad player">
      <button className="btn ghost back" onClick={onBack}>{Ic.back} Kembali</button>
      <video src={stream} controls autoPlay className="video" />
      <p className="hint center">Video tidak muncul? Coba resolusi atau server lain.</p>
    </div>
  )
}

/* ── Jobs & footer ──────────────────────────────────────── */

function JobToasts({ jobs }) {
  return (
    <div className="job-toasts" role="status" aria-live="polite">
      {jobs.slice(-3).map(j => (
        <div key={j.id} className="job-toast">
          <span className="job-title">{j.title}</span>
          {j.status === 'running' && (
            <>
              <div className="bar"><div style={{ width: pct(j) }} /></div>
              <span className="dim">{pct(j)}</span>
            </>
          )}
          {j.status === 'failed' && <span className="bad">{j.error}</span>}
        </div>
      ))}
    </div>
  )
}

function pct(j) {
  return j.total ? `${Math.round((j.done / j.total) * 100)}%` : '…'
}

function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer-grid">
        <div>
          <button className="logo" aria-label="Indonime">
            <span className="logo-mark">{Ic.playLg}</span>
            <span className="logo-text">INDO<span>NIME</span></span>
          </button>
          <p className="dim">Streaming anime sub Indo, gratis dan update tiap hari.</p>
        </div>
        <nav aria-label="Navigasi footer">
          <h3>Jelajah</h3>
          <a href="#latest-title">Rilis Terbaru</a>
          <a href="#popular-title">Paling Populer</a>
          <a href="#">Daftar Anime</a>
        </nav>
        <nav aria-label="Bantuan">
          <h3>Bantuan</h3>
          <a href="#">Cara Nonton</a>
          <a href="#">Lapor Error</a>
          <a href="#">Disclaimer</a>
        </nav>
      </div>
      <p className="footer-copy dim">© 2026 Indonime. Dibuat dengan {Ic.star} untuk pecinta anime.</p>
    </footer>
  )
}