# Indonime — React Native (Expo)

App mobile port pixel-faithful dari `../ui/` (React web). Backend tetap Python
(`../indonime/`), jalan di port 8756.

## Run

1. Start backend dulu (dari root repo):

       python -m indonime.app --headless   # server API aja, port 8756 (tanpa window GUI)
       # atau: python main.py --dev        # sekalian buka GUI desktop

2. Start app:

       npx expo start          # lalu tekan a (emulator) / scan QR (HP)
       npx expo start --web    # testing desktop di browser (localhost:8081)

   Web: backend harus nyala, CORS sudah allow. Layout responsive:
   ≥900px = layout desktop penuh (topbar 1 baris, hero arrows, rail arrows,
   grid auto-fill, footer 3 kolom); <900px = layout mobile (breakpoint
   sama dengan @media ui/ CSS).

### API URL

- Emulator Android → otomatis `http://10.0.2.2:8756` (loopback host).
- Device fisik / Expo Go di HP → server harus bind `0.0.0.0` dulu, lalu:

      EXPO_PUBLIC_API_URL=http://<IP-LAN-host>:8756 npx expo start

  (IP host no hp: `ipconfig` → IPv4). Hp & PC harus satu jaringan.

## Struktur

- `App.js` — komponen utama (port `../ui/src/App.jsx`, layout mobile)
- `src/styles.js` — StyleSheet (port `../ui/src/style.css`)
- `src/api.js` — client API (port `../ui/src/api.js`)
- `src/icons.jsx` — ikon SVG 1:1 dari map `Ic` web (react-native-svg)
- `src/theme.js` — design token (cermin `:root` CSS)

## Build APK

    npx expo run:android        # dev build (butuh Android SDK + emulator/device)
    # atau EAS Build utk release:

Perbedaan sengaja vs web (ponytail): gradient text pakai SVG (RN tak punya
background-clip:text), shimmer skeleton = pulse opacity (bukan sweep),
ResSelect = bottom-sheet modal (dropdown absolut tersembunyi di bawah sheet),
hero arrow & ghost btn >900px disembunyikan (layout mobile).
