# Server API smoke test (no provider network needed).
import json
import time
import urllib.request

from indonime.server import start_server


def test_api():
  port = start_server(port=0)
  base = f'http://127.0.0.1:{port}'

  with urllib.request.urlopen(base + '/api/providers') as r:
    data = json.load(r)
    assert r.status == 200 and 'otakudesu' in data['providers']

  with urllib.request.urlopen(base + '/api/jobs') as r:
    assert json.load(r) == {'jobs': []}

  req = urllib.request.Request(
    base + '/api/download',
    data=json.dumps({'server_url': 'https://pixeldrain.com/u/xxxx',
                     'title': 'Smoke Test'}).encode(),
    headers={'Content-Type': 'application/json'})
  with urllib.request.urlopen(req) as r:
    jid = json.load(r)['job_id']
  assert jid >= 1

  job = None
  for _ in range(100):
    with urllib.request.urlopen(base + '/api/jobs') as r:
      jobs = json.load(r)['jobs']
    job = next((j for j in jobs if j['id'] == jid), None)
    if job and job['status'] != 'running':
      break
    time.sleep(0.1)
  assert job and job['status'] == 'failed'  # bogus link → clean failure, no crash


if __name__ == '__main__':
  test_api()
  print('test_server OK')