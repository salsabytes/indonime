<div align="center">
  <h1>📺 Indonime</h1>
  <p><em>A minimalist terminal-based anime streamer with Indonesian subtitles.</em></p>
  
  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/platform-windows-lightgrey?logo=windows" alt="Platform Windows">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT">
    <img src="https://img.shields.io/github/v/release/salsabytes/indonime?logo=github" alt="Latest Release">
  </p>

  <p>
    <a href="#🚀-getting-started">Getting Started</a> •
    <a href="#📡-providers">Providers</a> •
    <a href="#🛠️-installation-from-source">Installation</a> •
    <a href="#📖-indonesia">Indonesia</a>
  </p>
</div>

---

## ✨ Why Indonime?

| The browser hassle | ✅ Indonime way |
|---|---|
| Open browser, search sites, dodge ads, find episodes | `indonime search one piece` — plays immediately |
| Download video, open player, delete files | Stream directly via **mpv**, auto-cleanup |
| Mega/PixelDrain decryption headache | Handled automatically — just watch |
| Need 5GB Visual C++ build tools | **Pure Python** — no compilation needed |

## 🎬 Preview

<div align="center">
  <video src="https://github.com/user-attachments/assets/7057b06a-859e-47cc-a555-50d1cfd3996f" controls autoplay loop muted style="max-width: 100%; border-radius: 10px;"></video>
</div>

## 🚀 Getting Started

### 🔹 Portable (easiest)
1. Download `Indonime.exe` from [Releases](https://github.com/salsabytes/indonime/releases)
2. Extract and run — **mpv installs automatically** if missing

### 🔹 Via pip
```bash
pip install indonime
indonime                          # TUI mode
indonime search one piece         # direct search
indonime search one piece -p anoboy
```

---

## 🛠️ Installation from Source

### 📋 Prerequisites
- **Python 3.10+**
- **Git**
- **~50MB disk space** (no Visual Studio Build Tools needed)

### 🔧 Steps

```bash
# 1. Clone
git clone https://github.com/salsabytes/indonime
cd indonime

# 2. Install dependencies
pip install -r requirements.txt
pip install -e .

# 3. Run — mpv auto-installs if missing
python main.py
```

That's it. No C++ compilation. No Visual Studio. No headaches.

### ⚡ All Commands

```bash
python main.py                           # Interactive TUI
python main.py search one piece          # Direct search + play
python main.py search one piece -p anoboy  # Switch provider
python -m indonime                       # Same, via module
```

> **Tip:** `pip install -e .` registers the `indonime` command globally.

## 📡 Providers

| Provider | Link Support |
|---|---|
| **Otakudesu** | PixelDrain, Mega |
| **Anoboy** | _(coming soon)_ |

Mega decryption uses **pure Python** AES-128 CTR — no C++ extensions required. 🐍

## 🧩 Features

- ✅ **Search & stream** — find anime, pick episodes, play instantly
- ✅ **Multi-provider** — Otakudesu + plugins for more
- ✅ **PixelDrain & Mega** — automatic link decryption
- ✅ **Auto mpv setup** — downloads mpv automatically if missing
- ✅ **Pure Python AES** — no Visual C++ build tools needed
- ✅ **Temp file cleanup** — temporary files deleted on exit
- ✅ **CLI mode** — search + play without the TUI

---

## 📖 Indonesia

> [Dokumentasi Bahasa Indonesia tersedia di sini.](README.md)

Indonime adalah tools ringan buat nonton anime sub Indo dari terminal. Scraping provider lokal, decrypt link (Mega, PixelDrain), putar lewat **mpv**, dan **nggak perlu compile C++** sama sekali.

---

<div align="center">
  <p>Made with ❤️ for Indonesian anime fans.</p>
  <p>
    <a href="https://github.com/salsabytes/indonime/issues">Report an issue</a> •
    <a href="https://github.com/salsabytes/indonime/discussions">Discussions</a>
  </p>
</div>
