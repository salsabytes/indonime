# Backend launcher for Android: runs the indonime API server inside the app
# (Chaquopy). Native RN UI talks to http://127.0.0.1:8756 (same process).
import os


def start(home):
    # make tempfile/expanduser land in app-private storage
    os.environ.setdefault('HOME', home)
    os.environ.setdefault('TMPDIR', home)

    from indonime.server import start_server
    start_server(port=8756, static_dir=None)  # daemon thread, returns immediately