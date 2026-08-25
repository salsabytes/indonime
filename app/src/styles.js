// StyleSheet — port ui/src/style.css ke layout mobile (setara @media max-width:900px,
// target utama RN: HP). Desktop-wide layout tdk relevan utk native.
import { Platform, StyleSheet } from 'react-native'
import { C, R, F } from './theme'

export const s = StyleSheet.create({
  // ── Root ──────────────────────────────────────────────
  app: { flex: 1, backgroundColor: C.bg },
  scroll: { flex: 1 },

  wrap: { paddingHorizontal: 20, width: '100%', maxWidth: 1200, alignSelf: 'center' },
  pagePad: { paddingTop: 28, paddingBottom: 64 },

  // ── Topbar (sticky → fixed di atas ScrollView) ────────
  topbar: {
    backgroundColor: C.bg,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
    paddingHorizontal: 20,
    paddingVertical: 10,
    gap: 10,
  },
  topbarInner: {
    width: '100%', maxWidth: 1200, alignSelf: 'center',
    flexDirection: 'row', alignItems: 'center', gap: 16,
    height: 64, paddingHorizontal: 0,
  },
  topbarRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  logo: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  logoMark: {
    width: 34, height: 34, borderRadius: 10,
    alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 4px 18px rgba(124,58,237,0.45)',
    elevation: 6,
  },
  logoText: { fontFamily: F.head, fontSize: 18, letterSpacing: 0.5, color: C.fg },
  iconBtn: {
    width: 40, height: 40, borderRadius: 20,
    alignItems: 'center', justifyContent: 'center',
  },
  tabs: { flexGrow: 0 },
  tabsInner: {
    flexDirection: 'row', gap: 4,
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
    borderRadius: 999, padding: 4, alignSelf: 'flex-start',
  },
  tab: { height: 30, paddingHorizontal: 16, borderRadius: 999, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  tabFill: { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0 },
  tabText: { fontFamily: F.bodyMed, fontSize: 13, color: C.fgDim },
  tabOnText: { fontFamily: F.bodyMed, fontSize: 13, color: C.white },
  searchBox: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
    borderRadius: 999, paddingLeft: 16, paddingRight: 4, height: 40,
  },
  // outlineStyle: hilangkan focus ring browser default di web (RNW bawa <input>)
  searchInput: {
    flex: 1, fontFamily: F.body, fontSize: 14, color: C.fg, paddingVertical: 0,
    ...(Platform.OS === 'web' ? { outlineStyle: 'none' } : {}),
  },
  searchBtn: {
    width: 32, height: 32, borderRadius: 16,
    alignItems: 'center', justifyContent: 'center',
  },

  // ── Hero ──────────────────────────────────────────────
  hero: { minHeight: 480, justifyContent: 'center', overflow: 'hidden' },
  heroBackdrop: { ...StyleSheet.absoluteFill },
  heroBg: { width: '100%', height: '100%' },
  heroVeilH: { ...StyleSheet.absoluteFill },
  heroVeilV: { position: 'absolute', left: 0, right: 0, bottom: 0, top: 0 },
  heroContent: {
    flexDirection: 'row', alignItems: 'flex-end',
    width: '100%', maxWidth: 1080, alignSelf: 'center',
    paddingHorizontal: 20, paddingTop: 48, paddingBottom: 88,
  },
  heroText: { flex: 1 },
  heroChip: {
    flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', gap: 8,
    paddingVertical: 6, paddingHorizontal: 14, borderRadius: 999,
    backgroundColor: 'rgba(124,58,237,0.14)', borderWidth: 1, borderColor: 'rgba(167,139,250,0.3)',
  },
  heroChipDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: C.green, boxShadow: '0 0 8px rgba(34,197,94,1)' },
  heroChipText: { fontFamily: F.bodySemibold, fontSize: 12, letterSpacing: 1, textTransform: 'uppercase', color: C.primary2 },
  heroTitle: { fontFamily: F.head, fontSize: 36, lineHeight: 40, letterSpacing: -0.5, color: C.fg, marginTop: 16, marginBottom: 12 },
  heroSynopsis: { fontFamily: F.body, fontSize: 14, lineHeight: 21, color: C.fgDim, marginBottom: 24, maxWidth: '100%' },
  heroActions: { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  heroCover: {
    width: 140, aspectRatio: 2 / 3, borderRadius: 14,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.14)',
    boxShadow: '0 24px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(167,139,250,0.22)',
    elevation: 12,
  },
  heroSegs: { position: 'absolute', bottom: 20, left: 0, right: 0, flexDirection: 'row', justifyContent: 'center', gap: 6 },
  heroSeg: { width: 44, height: 4, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.22)', overflow: 'hidden' },
  heroSegFill: { width: '100%', height: '100%', backgroundColor: 'transparent' },

  // ── Hero arrows (desktop only, .hero-arrow) ───────────
  heroArrow: {
    position: 'absolute', top: '50%', marginTop: -22, zIndex: 5,
    width: 44, height: 44, borderRadius: 22,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(15,15,35,0.5)', borderWidth: 1, borderColor: C.border,
  },
  heroArrowText: { fontFamily: F.body, fontSize: 22, color: C.fg },
  heroArrowLeft: { left: 16 },
  heroArrowRight: { right: 16 },

  // ── Rail arrows (desktop only, .rail-btn) ─────────────
  railBtn: {
    width: 40, height: 40, borderRadius: 20,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
  },
  railBtnText: { fontFamily: F.body, fontSize: 20, color: C.fgDim, lineHeight: 24 },
  railBtnDisabled: { opacity: 0.35 },

  // ── Stats ─────────────────────────────────────────────
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: 16, marginBottom: 56 },
  statCard: {
    paddingVertical: 18, paddingHorizontal: 22,
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border, borderRadius: R.lg,
    gap: 2, overflow: 'hidden',
  },
  statNum: { fontFamily: F.head, fontSize: 26, color: C.fg },
  statLabel: { fontFamily: F.body, fontSize: 13, color: C.muted },

  // ── Section ───────────────────────────────────────────
  sectionHead: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  sectionTitle: {
    fontFamily: F.headBold, fontSize: 22, letterSpacing: -0.3, color: C.fg,
  },
  sectionTitleRow: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
  sectionIcon: {
    width: 34, height: 34, borderRadius: 10,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(124,58,237,0.14)', borderWidth: 1, borderColor: 'rgba(167,139,250,0.25)',
  },

  // ── Chips ─────────────────────────────────────────────
  chips: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  chip: {
    height: 36, paddingHorizontal: 18, borderRadius: 999,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border, overflow: 'hidden',
  },
  chipText: { fontFamily: F.bodyMed, fontSize: 13, color: C.fgDim },
  chipOnText: { fontFamily: F.bodyMed, fontSize: 13, color: C.white },

  // ── Cards & grids ─────────────────────────────────────
  grid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: 18, columnGap: 12, marginTop: 16 },
  card: {},
  cardPoster: { position: 'relative' },
  epBadge: {
    position: 'absolute', top: 8, right: 8, zIndex: 2,
    paddingVertical: 4, paddingHorizontal: 10, borderRadius: 999, overflow: 'hidden',
    boxShadow: '0 4px 14px rgba(244,63,94,0.5)',
  },
  epBadgeText: { fontFamily: F.headBold, fontSize: 11, letterSpacing: 0.5, color: C.white },
  cardBody: { paddingHorizontal: 4, paddingTop: 10 },
  cardTitle: { fontFamily: F.bodyMed, fontSize: 14, lineHeight: 18.9, color: C.fg },
  cardSub: { fontFamily: F.body, fontSize: 12, color: C.muted, marginTop: 2 },
  cardMeta: { fontFamily: F.body, fontSize: 12, color: C.muted, marginTop: 2 },
  poster: {
    aspectRatio: 2 / 3, borderRadius: R.lg, overflow: 'hidden',
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
  },
  posterPlaceholder: { alignItems: 'center', justifyContent: 'center' },
  posterPhText: { fontFamily: F.head, fontSize: 22, color: C.muted },

  // ── Rail ──────────────────────────────────────────────
  rail: { paddingVertical: 4, paddingBottom: 12, gap: 18 },
  railCard: { width: 165 },
  railRank: { width: 340 },

  // ── Rank card ─────────────────────────────────────────
  rankCard: {
    width: 340,
    flexDirection: 'row', alignItems: 'center', gap: 14, padding: 10,
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border, borderRadius: R.lg,
  },
  popRank: { width: 40, textAlign: 'center' },
  popPoster: { width: 64, height: 88, position: 'relative' },
  popPlay: {
    position: 'absolute', top: 0, bottom: 0, left: 0, right: 0,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(15,15,35,0.4)', borderRadius: R.sm,
    // web: opacity 0 sampai hover — mobile tak ada hover, jadi sengaja disembunyikan
    opacity: 0,
  },
  popBody: { flex: 1, gap: 4 },
  popTitle: { fontFamily: F.bodyMed, fontSize: 14, color: C.fg },
  popMeta: { fontFamily: F.body, fontSize: 12, color: C.muted },
  popGo: { marginLeft: 4 },

  // ── Skeletons ─────────────────────────────────────────
  skeletonPoster: { aspectRatio: 2 / 3, borderRadius: R.lg, backgroundColor: C.card },
  skeletonLine: { height: 12, borderRadius: 6, backgroundColor: C.card, marginTop: 10 },
  skeletonLineShort: { width: '55%' },

  // ── Detail ────────────────────────────────────────────
  back: { marginBottom: 24 },
  detailHero: {
    gap: 28, padding: 24,
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border, borderRadius: 20, overflow: 'hidden',
  },
  detailPosterWrap: { alignItems: 'center' },
  detailPoster: {
    width: '100%', maxWidth: 240, aspectRatio: 2 / 3, borderRadius: R.lg, overflow: 'hidden',
    borderWidth: 1, borderColor: C.border,
    boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
    elevation: 10,
  },
  detailPosterPh: { alignItems: 'center', justifyContent: 'center' },
  detailPhText: { fontFamily: F.head, fontSize: 28, color: C.muted },
  detailTitle: { fontFamily: F.head, fontSize: 26, lineHeight: 32, letterSpacing: -0.4, color: C.fg, marginTop: 14, marginBottom: 10 },
  detailSynopsis: { fontFamily: F.body, fontSize: 14, lineHeight: 21, color: C.fgDim, marginBottom: 16 },
  detailMeta: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 18 },
  pill: {
    paddingVertical: 5, paddingHorizontal: 14, borderRadius: 999,
    backgroundColor: 'rgba(124,58,237,0.12)', borderWidth: 1, borderColor: 'rgba(167,139,250,0.25)',
  },
  pillText: { fontFamily: F.bodyMed, fontSize: 12, color: C.primary2 },
  detailActions: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },

  // ── Episode list ──────────────────────────────────────
  // auto-fill grid: min card 260px, wrap otomatis di semua ukuran layar
  // (desktop 4 kolom, tablet 2-3, HP 1) — pakai CSS, bukan hitung kolom manual
  eps: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  ep: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    flexGrow: 1, flexBasis: 260, flexShrink: 1, minWidth: 0,
    paddingVertical: 12, paddingHorizontal: 16, borderRadius: R.sm,
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border,
  },
  epNum: { fontFamily: F.headBold, fontSize: 13, color: C.muted, width: 28 },
  epTitle: { flex: 1, fontFamily: F.body, fontSize: 14, color: C.fg },
  epGo: { marginLeft: 4 },

  // ── Modal ─────────────────────────────────────────────
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15,15,35,0.7)', justifyContent: 'center', padding: 20 },
  modalCard: {
    maxHeight: '80%', padding: 20,
    width: '100%', maxWidth: 520, alignSelf: 'center',
    backgroundColor: C.card, borderWidth: 1, borderColor: C.border, borderRadius: R.lg,
    boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
    elevation: 16,
  },
  optsHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 14 },
  optsTitle: { fontFamily: F.headBold, fontSize: 16, color: C.fg, flex: 1 },
  modalBody: {},

  // ── Server options ────────────────────────────────────
  optGroup: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingVertical: 10, paddingHorizontal: 12,
    backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm,
  },
  optGroupTitle: { flex: 0, minWidth: 52, fontFamily: F.headBold, fontSize: 13, letterSpacing: 0.5, color: C.primary2 },
  rselectBtn: {
    flex: 1, minWidth: 0,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8,
    height: 38, paddingHorizontal: 12, backgroundColor: C.bg2,
    borderWidth: 1, borderColor: C.border, borderRadius: 10,
  },
  rselectText: { flex: 1, fontFamily: F.bodySemibold, fontSize: 13, color: C.fg },
  rselectBackdrop: { flex: 1, backgroundColor: 'rgba(15,15,35,0.5)', justifyContent: 'center', padding: 24 },
  rselectSheet: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 6, overflow: 'hidden', width: '100%', maxWidth: 420, alignSelf: 'center' },
  rselectItem: { paddingVertical: 12, paddingHorizontal: 12, borderRadius: 8 },
  rselectItemOn: { backgroundColor: 'rgba(124,58,237,0.16)' },
  rselectItemText: { fontFamily: F.bodyMed, fontSize: 13, color: C.fgDim },
  rselectItemOnText: { fontFamily: F.headBold, fontSize: 13, color: C.primary2 },
  optBtns: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8 },

  // ── Player ────────────────────────────────────────────
  player: {},
  video: {
    width: '100%', aspectRatio: 16 / 9, borderRadius: R.lg,
    backgroundColor: C.black, borderWidth: 1, borderColor: C.border, overflow: 'hidden',
    boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
  },

  // ── Toasts / busy / jobs ──────────────────────────────
  toast: {
    position: 'absolute', top: 76, alignSelf: 'center', zIndex: 100, maxWidth: '92%',
    flexDirection: 'row', alignItems: 'center', gap: 12,
    paddingVertical: 12, paddingHorizontal: 16, borderRadius: 999,
    backgroundColor: C.card2, borderWidth: 1, borderColor: C.border,
    boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
    elevation: 8,
  },
  toastText: { flex: 1, fontFamily: F.body, fontSize: 14, color: C.fg },
  errorToast: { borderColor: 'rgba(244,63,94,0.5)' },
  spinner: {
    width: 16, height: 16, borderRadius: 8,
    borderWidth: 2, borderColor: C.card2, borderTopColor: C.primary2,
  },
  jobToasts: { position: 'absolute', bottom: 16, left: 16, zIndex: 100, gap: 8 },
  jobToast: {
    width: 280, paddingVertical: 12, paddingHorizontal: 14,
    backgroundColor: C.card2, borderWidth: 1, borderColor: C.border, borderRadius: R.sm,
    boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
    elevation: 8,
  },
  jobTitle: { fontFamily: F.bodyMed, fontSize: 13, color: C.fg, marginBottom: 8 },
  bar: { height: 6, borderRadius: 3, backgroundColor: C.bg, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 3 },
  dim: { fontFamily: F.body, fontSize: 12, color: C.muted },
  badText: { fontFamily: F.body, fontSize: 12, color: C.accent },

  // ── Misc text ─────────────────────────────────────────
  hint: { fontFamily: F.body, fontSize: 14, color: C.fgDim },
  hintCenter: { textAlign: 'center', paddingVertical: 40 },
  hintCenterBad: { color: C.accent },

  // ── Buttons ───────────────────────────────────────────
  btn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    height: 46, paddingHorizontal: 22, borderRadius: 999,
  },
  btnSmall: { height: 38, paddingHorizontal: 16 },
  btnTextSmall: { fontFamily: F.bodySemibold, fontSize: 13 },
  btnPrimary: { overflow: 'hidden', boxShadow: '0 6px 24px rgba(124,58,237,0.45)', elevation: 6 },
  btnPrimaryText: { fontFamily: F.bodySemibold, fontSize: 14, color: C.white },
  btnGhost: { backgroundColor: 'rgba(255,255,255,0.06)', borderWidth: 1, borderColor: C.border },
  btnGhostText: { fontFamily: F.bodySemibold, fontSize: 14, color: C.fg },
  btnPlay: { overflow: 'hidden', boxShadow: '0 6px 24px rgba(244,63,94,0.4)', elevation: 6 },
  btnPlayText: { fontFamily: F.bodySemibold, fontSize: 13, color: C.white },
  btnDisabled: { opacity: 0.5 },

  // ── Footer ────────────────────────────────────────────
  footer: { marginTop: 48, paddingTop: 48, paddingBottom: 28, paddingHorizontal: 20, borderTopWidth: 1, borderTopColor: C.border, overflow: 'hidden' },
  footerGrid: { width: '100%', maxWidth: 1200, alignSelf: 'center' },
  footerCol: { gap: 8 },
  footerLinkText: { fontFamily: F.body, fontSize: 14, color: C.muted },
  footerTitle: { fontFamily: F.headBold, fontSize: 14, letterSpacing: 0.5, textTransform: 'uppercase', color: C.fgDim, marginBottom: 12 },
  footerCopy: { fontFamily: F.body, fontSize: 13, color: C.muted, textAlign: 'center', marginTop: 32 },
  footerCopyText: { fontFamily: F.body, fontSize: 13, color: C.muted },
})
