# 📺 Indonime
#### Nonton anime sub Indo dari terminal, nggak pake ribet.
Indonime itu tools ringan buat kamu yang males buka browser cuma buat nonton anime. Tinggal cari, klik, dan tonton.

[English version is available here](https://github.com/salsabytes/indonime/blob/main/README.en.md)

## 💻 Compatibility
> [!IMPORTANT]  
> Windows Only: Karena ada urusan sama C++ binary dependencies, saat ini cuma lancar di Windows.

## 📡 Provider & Extraction

| Provider  | Extraction |
|-----------|------------|
| Otakudesu |   PDrain   |
|           |    Mega    |

## 🚀 Cara Pake
### Portable
Buat yang mau langsung pakai tanpa ribet:
1. Download di [Releases](https://github.com/salsabytes/indonime/releases).
2. Ekstrak, tinggal pake `Indonime.exe`.

### Minimal Punya
- Python 3.10+
- Git
- Visual Studio Build Tools: Wajib instal yang "Desktop development with C++" buat compile ekstensinya

### Build dari source
Pastiin kamu punya Python 3.10+, Git, sama Visual Studio Build Tools (Desktop development with C++) biar nggak error pas build.
1. **Clone**
   ```bash
   git clone https://github.com/salsabytes/indonime
   cd indonime
   ```
2. **Install**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
3. **Setup**
   ```bash
   install_mpv.bat
   python setup.py build_ext --inplace
   ```

### ⚡ Quick Start
#### Run
```bash
python main.py
```
