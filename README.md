<div align="center">
  <h1>📺 Indonime</h1>
  <p><em>Nonton anime sub Indo dari terminal — cepat, ringan, tanpa browser.</em></p>
  
  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/platform-windows-lightgrey?logo=windows" alt="Platform Windows">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT">
    <img src="https://img.shields.io/github/v/release/salsabytes/indonime?logo=github" alt="Latest Release">
  </p>

  <p>
    <a href="#🚀-cara-pakai">Cara Pakai</a> •
    <a href="#📡-provider">Provider</a> •
    <a href="#🛠️-instalasi-dari-source">Instalasi</a> •
    <a href="#📖-english">English</a>
  </p>
</div>

---

## ✨ Kenapa Indonime?

| Ribet di browser | ✅ Indonime |
|---|---|
| Buka browser, cari situs, hadapi iklan, cari episode | `indonime search one piece` — langsung main |
| Download, buka player, hapus file | Stream langsung lewat **mpv**, otomatis cleanup |
| Link Mega/PixelDrain ribet | Decrypt otomatis, tinggal tonton |
| Butuh Visual C++ setebal 5GB buat compile | **Sudah pure Python** — nggak perlu build tools lagi |

## 🎬 Preview

<div align="center">
  <video src="https://github.com/user-attachments/assets/7057b06a-859e-47cc-a555-50d1cfd3996f" controls autoplay loop muted style="max-width: 100%; border-radius: 10px;"></video>
</div>

## 🚀 Cara Pakai

### 🔹 Portable (langsung jalan)
1. Download `Indonime.exe` dari [Releases](https://github.com/salsabytes/indonime/releases)
2. Ekstrak, jalankan — **mpv otomatis terinstall** kalau belum ada

### 🔹 Via pip (dev)
```bash
pip install indonime
indonime                          # TUI mode
indonime search one piece         # langsung search
indonime search one piece -p anoboy
```

---

## 🛠️ Instalasi dari Source

### 📋 Minimal Punya
- **Python 3.10+**
- **Git**
- **Sekitar 50MB ruang kosong** (nggak perlu Visual Studio Build Tools)

### 🔧 Langkah-langkah

```bash
# 1. Clone
git clone https://github.com/salsabytes/indonime
cd indonime

# 2. Install dependencies
pip install -r requirements.txt
pip install -e .

# 3. Jalankan — mpv auto-install kalau belum ada
python main.py
```

Selesai. Nggak perlu compile C++, nggak perlu Visual Studio, nggak perlu ribet.

### ⚡ Command Lengkap

```bash
python main.py                           # TUI interaktif
python main.py search one piece          # Search langsung + putar
python main.py search one piece -p anoboy  # Ganti provider
python -m indonime                       # Sama, via module
```

> **Tips:** Install `pip install -e .` biar bisa panggil `indonime` dari mana aja.

## 📡 Provider

| Provider | Link Support |
|---|---|
| **Otakudesu** | PixelDrain, Mega |
| **Anoboy** | _(coming soon)_ |

Dekripsi Mega pake AES-128 CTR **pure Python** — nggak perlu C++ extension. 🐍

## 🧩 Fitur

- ✅ **Search & stream** — cari anime, pilih episode, langsung putar
- ✅ **Multi-provider** — Otakudesu + provider lain via plugin system
- ✅ **PixelDrain & Mega** — decrypt otomatis
- ✅ **Auto mpv setup** — kalau mpv belum terinstall, diinstall otomatis
- ✅ **Pure Python AES** — nggak perlu Visual C++ build tools
- ✅ **Temp file cleanup** — file sementara dihapus otomatis
- ✅ **CLI mode** — langsung search + play tanpa TUI

---

## 📖 English

> [Full English documentation is available here.](README.en.md)

Indonime is a lightweight terminal-based anime streamer with Indonesian subtitles. It scrapes local providers, handles link decryption (Mega, PixelDrain), plays via **mpv**, and requires **zero C++ compilation**.

---

<div align="center">
  <p>Dibuat dengan ❤️ buat penikmat anime sub Indo.</p>
  <p>
    <a href="https://github.com/salsabytes/indonime/issues">Laporkan masalah</a> •
    <a href="https://github.com/salsabytes/indonime/discussions">Diskusi</a>
  </p>
</div>
