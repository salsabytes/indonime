import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'

const _noPoster = new Set()  // URLs confirmed without a cover — never refetch
const _synCache = new Map()  // detail URL → synopsis — never refetch
const HERO_MS = 6000

const Ic = {
  search: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>,
  play: <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M8 5.14v13.72a1 1 0 0 0 1.5.86l11-6.86a1 1 0 0 0 0-1.72l-11-6.86a1 1 0 0 0-1.5.86Z" /></svg>,
  down: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12" /><path d="m7 11 5 5 5-5" /><path d="M4 21h16" /></svg>,
  back: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5" /><path d="m12 19-7-7 7-7" /></svg>,
  home: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 10 9-7 9 7v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" /></svg>,
  x: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>,
  grid: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>,
}

export default function App() {
  const [providers, setProviders] = useState([])
  const [provider, setProvider] = useState('otakudesu')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [catalog, setCatalog] = useState(null)
  const [featured, setFeatured] = useState([])
  const [view, setView] = useState('home')        // home | anime | player
  const [anime, setAnime] = useState(null)        // {item, info, episodes}
  const [stream, setStream] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState(null)
  const [jobs, setJobs] = useState([])

  useEffect(() => {
    api.providers().then(r => setProviders(r.providers)).catch(() => {})
  }, [])

  useEffect(() => {
    setCatalog(null); setFeatured([]); setResults(null)
    api.catalog(provider).then(r => setCatalog(r.catalog)).catch(e => setError(e.message))
    api.home(provider).then(r => setFeatured(r.items)).catch(() => {})
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

  const activeJobs = jobs.filter(j => j.status === 'running' || j.status === 'failed')

  return (
    <div className="app">
      <header className="topbar">
        <button className="logo" onClick={goHome}>INDONIME</button>
        <nav className="tabs" role="tablist" aria-label="Provider">
          {providers.map(p => (
            <button key={p} role="tab" aria-selected={p === provider}
                    className={`tab ${p === provider ? 'on' : ''}`}
                    onClick={() => setProvider(p)}>{p}</button>
          ))}
        </nav>
        <form className="search" onSubmit={onSearch} role="search">
          <input value={query} onChange={e => setQuery(e.target.value)}
                 placeholder="Cari anime…" aria-label="Cari anime" />
          <button type="submit" aria-label="Cari">{Ic.search}</button>
        </form>
        <button className="icon-btn" onClick={goHome} aria-label="Beranda">{Ic.home}</button>
      </header>

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Tutup">{Ic.x}</button>
        </div>
      )}
      {busy && <div className="busy"><span className="spinner" />{busy}</div>}

      <main>
        {view === 'home' && (
          <HomeView catalog={catalog} results={results} searching={searching}
                    featured={featured} query={query} provider={provider}
                    onPick={pickAnime} />
        )}
        {view === 'anime' && anime && (
          <AnimeView anime={anime} onPlay={handlePlay} onDownload={handleDownload}
                     onBack={goHome} />
        )}
        {view === 'player' && stream && (
          <div className="player">
            <video src={stream} controls autoPlay className="video" />
            <p className="hint">Video tidak muncul? Coba resolusi atau server lain.</p>
            <button className="btn ghost" onClick={() => setView('anime')}>
              {Ic.back} Kembali
            </button>
          </div>
        )}
      </main>

      {activeJobs.length > 0 && (
        <footer className="jobs">
          {activeJobs.slice(-4).map(j => (
            <div key={j.id} className="job">
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
        </footer>
      )}
    </div>
  )
}

function pct(j) {
  return j.total ? `${Math.round((j.done / j.total) * 100)}%` : '…'
}

function HomeView({ catalog, results, searching, featured, query, provider, onPick }) {
  if (searching) return <p className="hint"><span className="spinner" />Mencari…</p>
  if (results) {
    if (!results.length) return <p className="hint">Tidak ada hasil untuk “{query}”.</p>
    return (
      <section>
        <SectionTitle>Hasil pencarian “{query}”</SectionTitle>
        <div className="grid">{results.map((it, i) => <PosterCard key={i} item={it} i={i} provider={provider} onPick={onPick} />)}</div>
      </section>
    )
  }
  if (!catalog) {
    return (
      <div className="grid" aria-hidden="true">
        {Array.from({ length: 24 }, (_, i) => (
          <div key={i} className="card skeleton" style={{ animationDelay: `${Math.min(i, 14) * 40}ms` }}>
            <div className="poster shimmer" />
            <span className="card-title skeleton-line" />
          </div>
        ))}
      </div>
    )
  }
  return (
    <>
      {featured.length > 0 && (
        <Hero items={featured} provider={provider} onPick={onPick} />
      )}
      <section>
        <SectionTitle>Katalog</SectionTitle>
        <CatalogGrid catalog={catalog} provider={provider} onPick={onPick} />
      </section>
    </>
  )
}

const PAGE_SIZE = 48

function CatalogGrid({ catalog, provider, onPick }) {
  const [page, setPage] = useState(1)
  const total = Math.ceil(catalog.length / PAGE_SIZE)

  useEffect(() => { setPage(1) }, [catalog])

  useEffect(() => {
    document.querySelector('main')?.scrollTo({ top: 0 })
  }, [page])

  const pages = useMemo(() => {
    const out = []
    const lo = Math.max(1, page - 2)
    const hi = Math.min(total, page + 2)
    if (lo > 1) out.push(1)
    if (lo > 2) out.push('…')
    for (let i = lo; i <= hi; i++) out.push(i)
    if (hi < total - 1) out.push('…')
    if (hi < total) out.push(total)
    return out
  }, [page, total])

  const start = (page - 1) * PAGE_SIZE

  return (
    <>
      <div className="grid">
        {catalog.slice(start, start + PAGE_SIZE).map((it, i) => (
          <PosterCard key={i} item={it} i={i} provider={provider} onPick={onPick} />
        ))}
      </div>
      <nav className="pager" aria-label="Halaman">
        <button className="pg" onClick={() => setPage(page - 1)} disabled={page === 1}
                aria-label="Sebelumnya">‹</button>
        {pages.map((p, i) => (
          p === '…'
            ? <span key={`e${i}`} className="pg-ellipsis">…</span>
            : <button key={p} className={`pg ${p === page ? 'on' : ''}`}
                      onClick={() => setPage(p)} aria-current={p === page ? 'page' : undefined}>{p}</button>
        ))}
        <button className="pg" onClick={() => setPage(page + 1)} disabled={page === total}
                aria-label="Berikutnya">›</button>
      </nav>
    </>
  )
}

function SectionTitle({ children }) {
  return <h2 className="section-title">{children}</h2>
}

function PosterCard({ item, i, provider, onPick }) {
  return (
    <button className="card" onClick={() => onPick(item)}
            style={{ animationDelay: `${Math.min(i, 14) * 40}ms` }}>
      <Poster item={item} provider={provider} />
      <span className="card-title">{item.title}</span>
    </button>
  )
}

function Hero({ items, provider, onPick }) {
  const [idx, setIdx] = useState(0)
  const [paused, setPaused] = useState(false)
  const [syn, setSyn] = useState('')
  const slides = items.slice(0, 6)
  const n = slides.length
  const it = slides[idx]
  const go = i => setIdx((i + n) % n)

  useEffect(() => {
    if (!it) return
    if (_synCache.has(it.url)) { setSyn(_synCache.get(it.url)); return }
    setSyn('')
    api.info(it.url, provider)
      .then(r => { _synCache.set(it.url, r.info.synopsis || ''); setSyn(_synCache.get(it.url)) })
      .catch(() => _synCache.set(it.url, ''))
  }, [idx, it, provider])

  useEffect(() => {
    if (n < 2) return
    const img = new Image()
    img.src = slides[(idx + 1) % n].image_full || slides[(idx + 1) % n].image || ''
  }, [idx, slides, n])

  // prefers-reduced-motion: CSS auto-advance is disabled → drive it by timer.
  useEffect(() => {
    const rm = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (!rm.matches || paused || n < 2) return
    const t = setInterval(() => setIdx(i => (i + 1) % n), HERO_MS)
    return () => clearInterval(t)
  }, [paused, n])

  if (!it) return null

  return (
    <div className="spotlight"
         onMouseEnter={() => setPaused(true)}
         onMouseLeave={() => setPaused(false)}>
      <div className="spotlight-backdrop" key={`b${idx}`} aria-hidden="true">
        <HeroImg it={it} fallback className="spotlight-backdrop-img" />
        <div className="spotlight-veil" />
      </div>

      <div className="spotlight-content" key={`c${idx}`}>
        <span className="spotlight-chip"><i aria-hidden="true" />{provider}</span>
        <h2>{it.title}</h2>
        {syn && <p className="spotlight-synopsis">{syn}</p>}
        <div className="spotlight-actions">
          <button className="spotlight-cta" onClick={() => onPick(it)}>{Ic.play} Lihat Detail</button>
        </div>
      </div>

      <div className="spotlight-poster-wrap" key={`p${idx}`}>
        <button className="spotlight-poster" onClick={() => onPick(it)}
                aria-label={`Lihat detail: ${it.title}`}>
          <HeroImg it={it} fallback className="spotlight-poster-img" />
          <span className="spotlight-poster-play">{Ic.play}</span>
        </button>
      </div>

      {n > 1 && (
        <>
          <button className="spotlight-arrow left" onClick={() => go(idx - 1)}
                  aria-label="Slide sebelumnya">‹</button>
          <button className="spotlight-arrow right" onClick={() => go(idx + 1)}
                  aria-label="Slide berikutnya">›</button>
          <div className="spotlight-segs" role="tablist" aria-label="Navigasi slide">
            {slides.map((s, i) => (
              <button key={i} className={`spotlight-seg${i === idx ? ' on' : i < idx ? ' done' : ''}`}
                      onClick={() => go(i)} aria-label={`Slide ${i + 1}`}
                      aria-current={i === idx ? 'true' : undefined}>
                {i === idx && (
                  <span key={`f${idx}`} className="spotlight-seg-fill"
                        style={{ animationPlayState: paused ? 'paused' : 'running' }}
                        onAnimationEnd={() => go(idx + 1)} />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function HeroImg({ it, className, fallback }) {
  const [src, setSrc] = useState(it.image_full || it.image || '')
  useEffect(() => { setSrc(it.image_full || it.image || '') }, [it])
  if (!src) return null
  return (
    <img src={src} alt="" loading="lazy" className={className}
         onError={() => {
           if (fallback && src !== it.image && it.image) setSrc(it.image)
           else setSrc('')
         }} />
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
  }, [inView, url, img, provider])

  if (img) {
    return (
      <div className="poster" ref={ref}>
        <img src={img} alt="" loading="lazy" />
        <span className="poster-overlay">{Ic.play}</span>
      </div>
    )
  }
  return (
    <div className="poster placeholder shimmer" ref={ref} aria-hidden="true">
      <span>{item.title.slice(0, 2)}</span>
    </div>
  )
}

function AnimeView({ anime, onPlay, onDownload, onBack }) {
  const [opts, setOpts] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const { item, info, episodes } = anime
  const title = info.title || item.title

  const pick = async ep => {
    setBusy(true); setErr(null); setOpts(null)
    try { setOpts({ ep, options: (await api.downloads(ep.url, '')).options }) }
    catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  const pickList = useMemo(
    () => opts ? [...opts.options].reverse() : [],
    [opts],
  )

  return (
    <div className="anime">
      <button className="btn ghost back" onClick={onBack}>{Ic.back} Kembali</button>

      <header className="hero">
        {info.image ? (
          <div className="hero-poster"><img src={info.image} alt={title} /></div>
        ) : (
          <div className="hero-poster placeholder">{title.slice(0, 2)}</div>
        )}
        <div className="hero-body">
          <h1>{title}</h1>
          <p className="hero-synopsis">{info.synopsis || '—'}</p>
          <p className="hero-count dim">{episodes.length} episode</p>
        </div>
      </header>

      <h2 className="section-title">Episode</h2>
      <div className="eps">
        {episodes.map((ep, i) => (
          <button key={ep.url} className="ep" onClick={() => pick(ep)}>
            <span className="ep-num">{i + 1}</span>
            <span className="ep-title">{ep.title}</span>
            <span className="ep-go">{Ic.play}</span>
          </button>
        ))}
      </div>

      {busy && <p className="hint"><span className="spinner" />Mengambil link download…</p>}
      {err && <p className="bad">{err}</p>}

      {opts && (
        <div className="opts">
          <div className="opts-head">
            <h3>{opts.ep.title}</h3>
            <button className="btn ghost" onClick={() => setOpts(null)} aria-label="Tutup">{Ic.x}</button>
          </div>
          {!opts.options.length && <p className="hint">Tidak ada server kompatibel.</p>}
          {pickList.map(o => (
            <div key={o.url} className="opt">
              <span>{o.label}</span>
              <div className="opt-btns">
                <button className="btn play" onClick={() => onPlay(o.url)}>{Ic.play} Play</button>
                <button className="btn ghost" onClick={() => onDownload(o, opts.ep)}>{Ic.down} Download</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}