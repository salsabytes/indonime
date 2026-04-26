import re
import html
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
      if ".mp4" in request.url or ":8080" in request.url:
        if request.method == "GET":
          final_video_url = request.url

    page.on("request", handle_request)
    try:
      page.goto(url, timeout=60000)
      html_content = page.content()
      pattern = r"padding-left:(\d+)px[^>]*>(.*?)</span>"
      matches = re.findall(pattern, html_content)
      if matches:
        extracted = []
        for pos, val in matches:
          digit = re.sub(r'\D', '', html.unescape(val).strip())
          if digit: extracted.append((int(pos), digit))
        extracted.sort(key=lambda x: x[0])
        captcha_code = "".join([i[1] for i in extracted])
        page.fill("input[name='code']", captcha_code)
      page.click("#downloadbtn", force=True)
      for _ in range(20):
        if final_video_url:
          break
        time.sleep(0.5)
      return final_video_url
    except Exception:
      return None
    finally:
      browser.close()