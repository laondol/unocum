import sys, os, time, requests, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

INTERVAL = 60
SERVICES = {
    'yp_app':  ('http://127.0.0.1:5000', 5000),
    'yp_dev':  ('http://127.0.0.1:5001', 5001),
}
WORKER_NAME = 'yp_ai_worker'
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'watchdog.log')

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def check():
    for name, (url, port) in SERVICES.items():
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                log(f"✓ {name} (:{port}) OK ({r.status_code})")
            else:
                log(f"✗ {name} (:{port}) ERROR ({r.status_code})")
        except Exception as e:
            log(f"✗ {name} (:{port}) FAILED ({e})")

    try:
        result = subprocess.run(
            ['sudo', 'supervisorctl', 'status', WORKER_NAME],
            capture_output=True, text=True, timeout=5
        )
        if 'RUNNING' in result.stdout:
            log(f"✓ {WORKER_NAME} RUNNING")
        else:
            log(f"✗ {WORKER_NAME} {result.stdout.strip()}")
    except Exception as e:
        log(f"✗ {WORKER_NAME} check failed: {e}")

if __name__ == '__main__':
    log("Watchdog started")
    while True:
        try:
            check()
        except Exception as e:
            log(f"Watchdog error: {e}")
        time.sleep(INTERVAL)
