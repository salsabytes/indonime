# Indonime — React Native (Expo) + web

App TypeScript (Expo SDK 57): dipakai buat mobile (Android/iOS) DAN desktop GUI
(pywebview via `react-native-web` build). React web Vite lama (`../ui/`) sudah
dihapus — UI cuma satu sumber sekarang: `App.tsx` + `src/`. Backend tetap Python
(`../indonime/`).

## Run mobile

1. Start backend (dari root repo):

       python -m indonime.app --headless   # server API aja, port 8756 (tanpa window GUI)

2. Start app:

       npx expo start          # lalu tekan a (emulator) / scan QR (HP)

### API URL mobile

- Emulator Android → otomatis `http://10.0.2.2:8756` (loopback host).
- Device fisik / Expo Go di HP → server harus bind `0.0.0.0` dulu, lalu:

      EXPO_PUBLIC_API_URL=http://<IP-LAN-host>:8756 npx expo start

  (IP host no hp: `ipconfig` → IPv4). Hp & PC harus satu jaringan.
- Web (`react-native-web`) → pakai URL relative, page dimuat dari server yang sama
  (desktop GUI / ekspor). PENTING: jangan buka web lewat `npx expo start --web` polos —
  dev server (localhost:8081) gak nge-proxy `/api`, jadi relative nyasar ke 8081 & anime
  gak ke-load. Kalau memang mau pakai dev-server Expo, set env backend eksplisit:

      EXPO_PUBLIC_API_URL=http://127.0.0.1:8756 npx expo start --web

  Untuk desktop GUI cukup `python app.py --dev` (atau `python main.py --dev`), page
  sama-origin dengan backend → relative jalan, tanpa env.

## Build web (buat desktop GUI / exe)

    npx expo export --platform web   # → app/dist (diserve indonime/server.py, dibundle build_exe.py)

Layout responsive: ≥900px = layout desktop penuh (topbar 1 baris, hero arrows,
rail arrows, grid auto-fill, footer 3 kolom); <900px = mobile.

## Struktur

- `App.tsx` — komponen utama (semua view: home/anime/player)
- `src/styles.ts` — StyleSheet (design system, cermin token)
- `src/api.ts` — client API + tipe data (Item/Ep/Job/DownloadOpt)
- `src/icons.tsx` — ikon SVG 1:1 dari map `Ic` web (react-native-svg)
- `src/theme.ts` — design token

## Typecheck

    npm run typecheck   # tsc --noEmit

## Build APK

    npx expo run:android        # dev build (butuh Android SDK + emulator/device)
    # atau EAS Build utk release

Perbedaan sengaja vs desktop web (ponytail): gradient text pakai SVG (RN tak punya
background-clip:text), shimmer skeleton = pulse opacity (bukan sweep),
ResSelect = bottom-sheet modal (dropdown absolut tersembunyi di bawah sheet),
hero arrow & ghost btn >900px disembunyikan (layout mobile).
