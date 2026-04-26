import time
from playwright.sync_api import sync_playwright
from rich.console import Console

console = Console()

def scrape(url):
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    final_video_url = None

    def handle_request(request):
      nonlocal final_video_url
      if "/api/file/" in request.url and "download" in request.url:
        if not any(ext in request.url.lower() for ext in [".jpg", ".png", ".webp"]):
          final_video_url = request.url

    page.on("request", handle_request)
    try:
      file_id = url.split('/')[-1]
      backup_url = f"https://pixeldrain.com/api/file/{file_id}?download"
      page.goto(url, wait_until="domcontentloaded", timeout=30000)
      download_btn = page.locator("a.button:has-text('Download'), button:has-text('Download')").first
      if download_btn.is_visible():
        download_btn.click()
        for _ in range(10):
          if final_video_url:
            break
          time.sleep(0.5)
      return final_video_url if final_video_url else backup_url
    except Exception:
      file_id = url.split('/')[-1]
      return f"https://pixeldrain.com/api/file/{file_id}?download"
    finally:
      browser.close()