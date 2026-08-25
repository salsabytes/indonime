<div align="center">
  <h1>📺 Indonime</h1>
  <p><em>Nonton anime sub Indo dari terminal — cepat, ringan, tanpa browser.</em></p>

  <p>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/platform-windows-lightgrey?style=flat-square&logo=windows&logoColor=white" alt="Platform Windows">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License MIT">
    <a href="https://www.codefactor.io/repository/github/salsabytes/indonime/issues/main"><img src="https://www.codefactor.io/repository/github/salsabytes/indonime/badge?style=flat-square" alt="CodeFactor"></a>
    <img src="https://img.shields.io/github/v/release/salsabytes/indonime?style=flat-square&logo=github" alt="Latest Release">
    <img src="https://img.shields.io/github/downloads/salsabytes/indonime/total?style=flat-square&logo=github" alt="Downloads">
  </p>

  <p>
    <a href="#-kenapa-indonime">Kenapa?</a> •
    <a href="#-cara-pakai">Cara Pakai</a> •
    <a href="#-dari-source-contributor">Instalasi</a> •
    <a href="#-fitur">Fitur</a> •
    <a href="#-provider">Provider</a> •
    <a href="#-struktur-project">Struktur</a>
  </p>

  <br>

  <img src="https://github.com/user-attachments/assets/e86c9815-cc39-47a4-b796-b9ab048c7410" alt="Indonime TUI Demo" width="75%" style="border-radius: 10px;"/>

  <br><br>

  <a href="https://github.com/salsabytes/indonime/releases/latest">
    <img src="https://img.shields.io/badge/Download%20.exe-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Download">
  </a>
  &nbsp;
  <a href="#-cara-pakai">
    <img src="https://img.shields.io/badge/Pip%20Install-black?style=for-the-badge&logo=python&logoColor=white" alt="Pip Install">
  </a>
</div>

<br>

---

## ✨ Kenapa Indonime?

| 😫 Ribet di Browser | ✅ Indonime |
|---|---|
| Buka browser, cari situs, hadapi iklan, ganti episode manual | **`indonime search one piece`** — langsung search + putar |
| Download, buka player, hapus file sampah | Stream langsung lewat **mpv**, auto-cleanup ✅ |
| Link Mega/PixelDrain pusing sendiri | Decrypt **otomatis** — tinggal tonton 🎬 |
| Butuh Visual C++ 5GB buat compile | **Pure Python** — nggak perlu build tools sama sekali 🐍 |

> **Intinya:** Dari `pip install` sampe nonton episode pertama — **kurang dari 2 menit**.

<br>

## 🚀 Cara Pakai

Ada **3 cara** pake Indonime — pilih yang paling cocok buat kamu:

### 🟢 Paling Gampang — Portable

| Step | Aksi |
|---|---|
| 1️⃣ | Download [`Indonime.exe`](https://github.com/salsabytes/indonime/releases/latest) |
| 2️⃣ | Buka exe — backend + UI + player langsung jalan, gak perlu install apa-apa |
| 3️⃣ | Tinggal pilih anime & nonton! 🎉 |

> ⚠️ **Windows bilang "virus"/"protected your PC"?** Bukan virus — exe gak di-sign
> (pakai sertifikat berbayar) jadi SmartScreen/Defender nge-flag heuristic.
> Cara lewatin:
> - SmartScreen *"Windows protected your PC"* → klik **More info** → **Run anyway**,
>   atau klik kanan exe → **Properties** → centang **Unblock** (sekali doang).
> - Defender deteksi beneran → **Windows Security → Protection history** →
>   **Restore** file-nya, terus **Allow on device**.
> - Kode sumber terbuka, build dari repo: `python build_exe.py`.

### 🔵 Via Pip (Developer)

```bash
pip install indonime
```

| Command | Fungsi |
|---|---|
| `indonime` | TUI mode — pake keyboard navigasi |
| `indonime search <judul>` | Search + play langsung dari CLI |
| `indonime search <judul> -p anoboy` | Ganti provider |

### 🟡 Dari Source (Contributor)

```bash
git clone https://github.com/salsabytes/indonime
cd indonime

# Pakai uv (punya uv.lock → versi ke-kunci persis):
uv sync

# atau pakai pip biasa:
pip install -e .
python main.py
```

> **Tips:** `uv sync` / `pip install -e .` bikin kamu bisa panggil `indonime` dari mana aja. Ubah kode → langsung jalan, nggak perlu install ulang.

<br>

---

## 🧩 Fitur

<div>
  <table>
    <tr>
      <td align="center" width="33%">🔍</td>
      <td align="center" width="33%">📡</td>
      <td align="center" width="33%">🔐</td>
    </tr>
    <tr>
      <td align="center"><strong>Search & Stream</strong></td>
      <td align="center"><strong>Multi-Provider</strong></td>
      <td align="center"><strong>Auto Decrypt</strong></td>
    </tr>
    <tr>
      <td align="center">Cari anime, pilih episode, langsung putar. Selesai.</td>
      <td align="center">Otakudesu + provider lain via plugin system 🔌</td>
      <td align="center">PixelDrain & Mega — decrypt otomatis, <strong>pure Python AES</strong></td>
    </tr>
    <tr>
      <td align="center">🎬</td>
      <td align="center">⚡</td>
      <td align="center">🧹</td>
    </tr>
    <tr>
      <td align="center"><strong>Auto mpv Setup</strong></td>
      <td align="center"><strong>Zero Build Tools</strong></td>
      <td align="center"><strong>Auto Cleanup</strong></td>
    </tr>
    <tr>
      <td align="center">mpv diinstall otomatis kalo belum ada</td>
      <td align="center">Nggak perlu Visual C++ — <strong>beneran pure Python</strong></td>
      <td align="center">File sementara dihapus otomatis pas keluar 🧽</td>
    </tr>
  </table>
</div>

<br>

---

## 📡 Provider

| Provider | Link Support | Status |
|---|---|---|
| **Otakudesu** | PixelDrain, Mega | ✅ Aktif |
| **Anoboy** | PixelDrain | 🔜 Coming soon |

> Dekripsi Mega pake **AES-128 CTR pure Python** — nggak perlu C++ extension. 🐍

<br>

---

## 🗂️ Struktur Project

```
indonime/
├── 📁 indonime/              # Package utama
│   ├── __init__.py          # Entry point & CLI routing
│   ├── __main__.py          # python -m indonime
│   ├── ui.py                # TUI — InquirerPy + Rich
│   ├── player.py            # Streaming via mpv
│   ├── 📁 ext/               # Utility modules
│   │   ├── megaNZ.py        # Mega download + AES decrypt
│   │   ├── pdrain.py        # PixelDrain downloader
│   └── 📁 plugins/           # Provider scrapers
│       ├── anoboy.py        # Anoboy provider
│       ├── otakudesu.py     # Otakudesu provider
│       └── _base.py         # Shared helpers
├── 📄 main.py                # Dev entry point (python main.py)
├── 📄 build_exe.py           # PyInstaller build script
├── 📄 pyproject.toml         # Package config
└── 📄 README.md              # Ini dia 😄
```

<br>

---

## 💬 Tentang Project

Dibuat dengan ❤️ buat **penikmat anime sub Indo** yang capek ribet buka browser, hadepin iklan, download file gede, dan compile C++ cuma buat nonton.

| Tautan | URL |
|---|---|
| 🐛 Lapor Bug | [github.com/salsabytes/indonime/issues](https://github.com/salsabytes/indonime/issues) |
| 💬 Diskusi | [github.com/salsabytes/indonime/discussions](https://github.com/salsabytes/indonime/discussions) |
| ⭐ Kontribusi | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 📜 Lisensi | [MIT License](LICENSE) |

<br>

---

<div align="center">
  <sub>
    Dibaca pake <a href="README.en.md">English version 🇬🇧</a>
  </sub>
  <br><br>
  <img src="https://img.shields.io/badge/made%20with%20❤️%20and%20🐍-indonime-blue?style=flat-square" alt="Made with love and Python">
</div>
