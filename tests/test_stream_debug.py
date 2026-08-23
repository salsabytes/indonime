"""Debug: test _http_range and streaming flow against real MEGA CDN."""
import sys, os, time, threading, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from indonime.ext.megaNZ import (
    _http_range, _parse_mega_url, _fetch_file_info, _mega_fid,
    resolve_mega_file_stream, _decrypt_range, HEADERS
)
from indonime.plugins._base import resolve_url

# --- Test 1: _http_range basic connectivity ---
def test_http_range_basic():
    print("\n=== Test 1: _http_range connectivity ===")
    # Use a known public Range-supporting URL
    test_url = "https://httpbin.org/range/1024"
    result = _http_range(test_url, 0, 512)
    if result:
        print(f"  OK: got {len(result)} bytes")
    else:
        print("  FAIL: _http_range returned None")

# --- Test 2: _fetch_file_info ---
def test_fetch_file_info():
    print("\n=== Test 2: _fetch_file_info ===")
    # Need a real mega file_id to test. Skip if not available.
    print("  SKIP: need real mega file_id")

# --- Test 3: _http_range retry behavior ---
def test_retry_behavior():
    print("\n=== Test 3: _http_range retry on bad URL ===")
    bad_url = "https://httpbin.org/status/500"
    t0 = time.time()
    result = _http_range(bad_url, 0, 100, retries=3)
    elapsed = time.time() - t0
    print(f"  Result: {result} (expected None)")
    print(f"  Elapsed: {elapsed:.1f}s (should be ~3s with backoff)")

# --- Test 4: Connection reset simulation ---
def test_connection_reset():
    print("\n=== Test 4: Connection reset handling ===")
    # httpbin sometimes resets connections
    for i in range(5):
        try:
            result = _http_range("https://httpbin.org/delay/10", 0, 100, timeout=3, retries=2)
            print(f"  Attempt {i+1}: {'OK' if result else 'None (expected for timeout)'}")
        except Exception as e:
            print(f"  Attempt {i+1}: Exception: {e}")

# --- Test 5: Full stream flow with a real mega URL ---
def test_full_stream():
    print("\n=== Test 5: Full stream flow ===")
    # We need a real mega URL. Check if there's one in history or env.
    mega_url = os.environ.get("TEST_MEGA_URL")
    if not mega_url:
        print("  SKIP: set TEST_MEGA_URL env var with a real mega.nz/file/...#key URL")
        return

    print(f"  URL: {mega_url[:50]}...")
    try:
        curr = resolve_url(mega_url, timeout=15)
        print(f"  Resolved: {curr[:50]}...")
        if not (('mega.nz' in curr or 'mega.co.nz' in curr) and '#' in curr):
            print("  FAIL: not a mega URL after resolve")
            return
        mega_url, f_id = _mega_fid(curr)
        print(f"  File ID: {f_id}")

        # Test _fetch_file_info
        print("  Fetching file info...")
        info = _fetch_file_info(f_id)
        if info is None:
            print("  FAIL: _fetch_file_info returned None")
            return
        dl_link, file_size = info
        print(f"  File size: {file_size} bytes ({file_size/1024/1024:.1f} MB)")
        print(f"  DL link: {dl_link[:80]}...")

        # Test _http_range on the actual MEGA CDN
        print("  Testing Range request (head 64KB)...")
        head = _http_range(dl_link, 0, 64 * 1024)
        if head:
            print(f"  OK: got {len(head)} bytes from head")
        else:
            print("  FAIL: head Range request returned None")

        print("  Testing Range request (tail 4MB)...")
        tail_off = max(0, file_size - 4 * 1024 * 1024) & ~15
        tail = _http_range(dl_link, tail_off, file_size)
        if tail:
            print(f"  OK: got {len(tail)} bytes from tail")
        else:
            print("  FAIL: tail Range request returned None")

        # Test full stream
        print("  Starting full resolve_mega_file_stream...")
        stream = resolve_mega_file_stream(mega_url, f_id)
        if stream is None:
            print("  FAIL: resolve_mega_file_stream returned None")
            return
        path, ready, stop, dl_thread, bytes_counter, file_size = stream
        print(f"  Stream created: {path}")
        print(f"  Waiting for ready (max 30s)...")

        t0 = time.time()
        while not ready.is_set() and time.time() - t0 < 30:
            print(f"    bytes: {bytes_counter[0]}/{file_size} ({bytes_counter[0]*100//file_size if file_size else 0}%)")
            time.sleep(2)

        if ready.is_set():
            print(f"  OK: ready in {time.time()-t0:.1f}s, {bytes_counter[0]} bytes buffered")
        else:
            print(f"  TIMEOUT: not ready after 30s, {bytes_counter[0]} bytes buffered")

        stop.set()
        dl_thread.join(timeout=5)
        if os.path.exists(path):
            os.remove(path)
            print("  Cleaned up temp file")

    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_http_range_basic()
    test_retry_behavior()
    test_connection_reset()
    test_full_stream()
    print("\n=== Done ===")
