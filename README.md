# 📺 Indonime
#### A minimalist Indonesian-subtitled anime streamer for Windows.
Indonime is a lightweight tool designed to search and stream anime with Indonesian subtitles directly from local providers without the need for a web browser. It handles scraping, link decryption (such as Mega, PDrain, and more to come), and uses MPV as the primary media player.

## 💻 Compatibility Notice
> [!IMPORTANT]  
> **Windows Only:** Currently, Indonime is developed and optimized exclusively for Windows environments. Cross-platform support (Linux/macOS) is not yet guaranteed due to specific binary dependencies.

## 📡 Provider & Link Support

| Provider  | Extraction |
|-----------|------------|
| Otakudesu |   PDrain   |
|           |    Mega    |

## 🚀 Getting Started

### Using Portable Version
If you downloaded the bundle from the [Releases](https://github.com/salsabytes/indonime/releases) page:
1. Extract the archive.
2. Run `Indonime.exe`.

### Prerequisites
- Python 3.10+
- Git
- Visual Studio Build Tools: Required for compiling C++ extensions. Select "Desktop development with C++" during installation

### Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/salsabytes/indonime
   cd indonime
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
3. **Initialize MPV Binary**
   Run the included batch script to fetch the required player binaries:
   ```bash
   install_mpv.bat
   ```
4. **Build extensions**
   ```bash
   python setup.py build_ext --inplace
   ```

### ⚡ Quick Start
#### How to Run
After completing the installation, you can launch the application using:
```bash
python main.py
```
