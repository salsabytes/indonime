## 💻 Compatibility Notice
> [!IMPORTANT]  
> **Windows Only:** Currently, Indonime is developed and optimized exclusively for Windows environments. Cross-platform support (Linux/macOS) is not yet guaranteed due to specific binary dependencies.

## 📡 Provider & Link Support

| Provider  | Extraction |
|-----------|------------|
| Otakudesu |   PDrain   |
|           |    Mega    |

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Git
- Visual Studio Build Tools: Required for compiling C++ extensions. Select "Desktop development with C++" during installation

### Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/salsa-ram/indonime
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
