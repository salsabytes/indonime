# Kontribusi ke Indonime

Hai, makasih udah mau berkontribusi ke **Indonime**! 🎉

Kami sangat menghargai bantuan kamu, baik itu lapor bug, saran fitur, atau langsung bantu ngoding. Dokumen ini bakal ngebantu kamu tahu gimana caranya berkontribusi dengan lancar.

---

## Daftar Isi

- [Kode Etik](#kode-etik)
- [Cara Laporkan Bug](#cara-laporkan-bug)
- [Cara Ajukan Fitur](#cara-ajukan-fitur)
- [Setup Development](#setup-development)
- [Struktur Project](#struktur-project)
- [Coding Standards](#coding-standards)
- [Git Workflow & Commit](#git-workflow--commit)
- [Prosedur Pull Request](#prosedur-pull-request)
- [Testing](#testing)
- [Tips & Pitfalls](#tips--pitfalls)

---

## Kode Etik

Project ini mengikuti [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). Dengan berpartisipasi, kamu diharapkan untuk menjunjung kode etik ini. Laporkan perilaku yang tidak pantas ke maintainer.

---

## Cara Laporkan Bug

Nemuin bug? Bikin issue di [GitHub Issues](https://github.com/salsabytes/indonime/issues).

**Informasi yang perlu disertakan:**

1. **Judul** yang jelas dan deskriptif
2. **Langkah reproduksi** — langkah demi langkah untuk memunculkan bug
3. **Expected behavior** — apa yang seharusnya terjadi
4. **Actual behavior** — apa yang benar-benar terjadi
5. **Screenshot / log error** — kalau ada, tempelin aja
6. **Environment:**
   - OS dan versi (contoh: Windows 10/11)
   - Python versi berapa (`python --version`)
   - Versi Indonime (`pip show indonime` atau `git log --oneline -1`)
   - Player yang dipakai (mpv versi?)

**Contoh template issue:**

```markdown
### Deskripsi
[ceritakan bugnya]

### Langkah Reproduksi
1. Jalankan `indonime search ...`
2. Pilih episode ...
3. ...

### Expected
[seharusnya apa]

### Actual
[yang terjadi]

### Log
[paste log errornya]

### Environment
- OS: Windows 11
- Python: 3.11.5
- Indonime: v1.2.0
```

---

## Cara Ajukan Fitur

Punya ide keren? Buka [Discussions](https://github.com/salsabytes/indonime/discussions) dulu — diskusikan sebelum bikin PR biar nggak sia-sia.

**Fitur yang bakal dipertimbangkan:**
- Provider baru (scraper untuk situs streaming lain)
- Fitur yang bikin UX makin enak
- Optimasi performa
- Dukungan platform lain (Linux/macOS)

**Sebaiknya diskusikan dulu kalau:**
- Mau nambah provider — takut structuranya perlu penyesuaian
- Mau refactor besar-besaran
- Fitur yang butuh dependency berat

---

## Setup Development

### Prasyarat

- **Python 3.10+**
- **Git**
- **mpv** (akan diinstall otomatis kalau belum ada)
- Sekitar 50MB ruang kosong

### Langkah

```bash
# 1. Clone repository
git clone https://github.com/salsabytes/indonime
cd indonime

# 2. (Rekomendasi) Buat virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# 3. Install dependencies
pip install -e .

# 5. Jalankan
python main.py
# atau
indonime
```

### Verifikasi

```bash
# Cek apakah semua modul bisa di-import
python -c "import indonime; import ext; import plugins; print('OK')"

# Cek CLI works
python main.py search one piece
```

---

## Struktur Project

```
indonime/
├── indonime/              # Package utama
│   ├── __init__.py        # Entry point, main() function
│   ├── __main__.py        # `python -m indonime`
│   ├── ui.py              # TUI — tuiko (menu, prompt)
│   ├── player.py          # Player — streaming via mpv
│   ├── _mpv_install.py    # Auto-install mpv
│   └── ext/               # Utility / extension modules
│       ├── megaNZ.py      # Mega downloader + AES-128 CTR decrypt
│       └── pdrain.py      # PixelDrain downloader
├── plugins/               # Plugin system — provider scrapers
│   └── __init__.py
├── main.py                # CLI entry point (developer shortcut)
├── pyproject.toml         # Build system config
├── build_exe.py           # Build Indonime.exe (PyInstaller)
├── README.md              # Dokumentasi utama (Indonesia)
├── README.en.md           # Dokumentasi (English)
└── SECURITY.md            # Security policy
```

### Penjelasan Modul

| Modul | Fungsi |
|---|---|
| `indonime/__init__.py` | Entry point `main()`, routing argumen CLI |
| `indonime/ui.py` | TUI interaktif: search, pilih episode, pilih provider |
| `indonime/player.py` | Handle streaming ke mpv, cleanup temp file |
| `indonime/_mpv_install.py` | Auto-install mpv lintas platform |
| `indonime/ext/megaNZ.py` | Download + decrypt link Mega (AES-128 CTR murni Python) |
| `indonime/ext/pdrain.py` | Download dari PixelDrain |
| `indonime/plugins/` | Scraper tiap provider (Otakudesu, Anoboy, dll) |

---

## Coding Standards

### Python

- **Python 3.10+** — manfaatkan type hints, match-case, union types (`X | Y`)
- **Ikuti [PEP 8](https://peps.python.org/pep-0008/)** — kecuali yang nggak praktis
- **Type hints** — wajib untuk fungsi public, dianjurkan untuk internal
- **Docstrings** — pake Google style atau sekedar komentar jelas
- **Line length** — maksimal ~100 karakter (nggak kaku)

### Contoh

```python
from typing import Optional


def search_anime(query: str, provider: str = "otakudesu") -> list[dict]:
    """Cari anime berdasarkan query.

    Args:
        query: Judul anime yang dicari.
        provider: Nama provider (otakudesu, anoboy, dll).

    Returns:
        List of dict dengan keys: title, url, episode, dll.
    """
    ...
```

### Hal Lain

- **Error handling** — jangan `except: pass`, minimal log atau raise specific exception
- **Logging** — ganti `print()` dengan `logging` atau `rich.print()` untuk yang kritis
- **Import order**: stdlib → third-party → local
- **Jangan** commit file temp (`__pycache__/`, `.venv/`, dll)

---

## Git Workflow & Commit

### Branching

- `main` — branch stabil, siap rilis
- `dev` / `<fitur>` — branch pengembangan, nanti PR ke `main`
- Jangan commit langsung ke `main` kecuali hotfix kecil

### Commit Message

Pake **conventional commits** biar rapi:

```
<type>: <deskripsi singkat>

<opsional: body lebih detail>
```

**Type yang dipake:**

| Type | Kapan |
|---|---|
| `feat` | Fitur baru (provider baru, command baru) |
| `fix` | Perbaikan bug |
| `refactor` | Refactor tanpa ubah behavior |
| `style` | Perbaikan coding style (formatting, spasi) |
| `docs` | Update dokumentasi |
| `perf` | Optimasi performa |
| `test` | Nambah / ubah test |
| `chore` | Housekeeping (dependencies, build, CI) |

**Contoh:**

```
feat(provider): tambah provider Anoboy

- Scraper halaman search Anoboy
- Extract link PixelDrain
- Register ke plugin system
```

```
fix(player): handle mpv path dengan spasi

mpv_path yang mengandung spasi sekarang di-quote.
```

---

## Prosedur Pull Request

### Checklist Sebelum PR

- [ ] Kode sudah di-test secara manual
- [ ] Tidak ada print/komentar debug yang ketinggalan
- [ ] Nggak ada error/warning baru
- [ ] Type hints udah ditambahin kalau perlu
- [ ] Udah `git pull --rebase` dari `main` terbaru
- [ ] Udah nambah / update dokumentasi kalau ada API baru

### Steps

1. **Fork** repository (kalau kontributor eksternal)
2. **Buat branch** baru dari `main`:
   ```bash
   git checkout -b feat/nama-fitur
   ```
3. **Commit** sesuai conventional commits
4. **Push** ke fork / branch kamu
5. **Buka Pull Request** ke `main`
6. **Deskripsi PR** jelas — apa yang diubah dan kenapa
7. **Tunggu review** — maintainer akan review, minta perubahan kalau perlu

### Saat Review

- Responsif terhadap feedback
- Kalau ada perubahan, push aja commit baru (jangan force push dulu)
- Setelah approve, maintainer yang handle merge

---

## Testing

Saat ini Indonime belum punya test suite otomatis. Tapi kamu tetap diminta untuk:

- **Test manual** — jalankan fitur yang kamu ubah
- **Coba edge cases** — search kosong, network error, link rusak
- **Test di Windows** — platform utama (kalau bisa di Linux juga bonus)

Kalau kamu mau nambahin test — itu sangat dihargai! 🎉

Untuk test nanti kita bisa pake `pytest`. Contoh struktur yang bakal dipake:

```python
# tests/test_player.py
def test_mpv_path_handling():
    ...
```

---

## Tips & Pitfalls

### Untuk Kontributor Baru

- **Mulai dari yang kecil** — cari issue label `good first issue` atau `help wanted`
- **Tanya dulu** di Discussions kalau bingung — nggak ada pertanyaan bodoh
- **Baca plugin yang udah ada** — contoh provider yang udah jalan

### Pitfalls yang Sering

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError` | Jalanin `pip install -e .` dulu |
| mpv gak kedetek | Jalankan app — mpv auto-install, atau install manual |
| Link Mega gagal decrypt | Pastikan link valid; cek log di `ext/megaNZ.py` |
| Provider berubah struktur HTML | Update scraper — tinggal follow pattern yang ada |

### Debugging

```bash
# Mode verbose
python main.py search one piece --verbose  # (kalau tersedia)

# Test component aja
python -c "from ext.megaNZ import mega_download; print(mega_download('https://mega.nz/...'))"

# Cek apakah provider scraping masih jalan
python -c "from plugins import otakudesu; print(otakudesu.search('one piece'))"
```

---

## Build & Rilis

### Build Portable (.exe)

```bash
python build.py
```

Hasilnya ada di `dist/Indonime.exe`. Proses build pake PyInstaller (lihat `build_exe.py`).

### Rilis

1. Update versi di `pyproject.toml`
2. Commit dengan `chore(release): vX.Y.Z`
3. Tag: `git tag vX.Y.Z`
4. Build & upload ke GitHub Releases

---

## Akhir Kata

Makasih udah baca sampai sini! Setiap kontribusi — dari lapor typo sampe nambah provider baru — sangat berarti buat Indonime. 🐍✨

Kalau ada pertanyaan, jangan ragu buat buka [Discussions](https://github.com/salsabytes/indonime/discussions) atau kontak langsung maintainer.

**Happy coding!** 🎉
