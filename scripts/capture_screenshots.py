import os
import subprocess
import time
import urllib.request
from pathlib import Path

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCREENSHOTS_DIR = Path("docs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

VIEWS = [
    ("dashboard", "01_dashboard.png"),
    ("projects", "02_workloads.png"),
    ("agent_studio", "03_agent_studio.png"),
    ("evaluations", "04_evaluation_gates.png"),
    ("deployments", "05_deployments_rollout.png"),
    ("ml_studio", "06_ml_studio.png"),
    ("rag_hub", "07_rag_knowledge.png"),
    ("gateway", "08_llm_gateway.png"),
    ("incidents", "09_incidents_rca.png"),
    ("audit", "10_audit_trail.png"),
]


def wait_for_url(url: str, timeout: int = 15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    print("1. Starting FastAPI control plane server...")
    api_proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "uvicorn", "apps.api.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("2. Starting Vite web console server...")
    web_proc = subprocess.Popen(
        ["npx", "vite", "preview", "--host", "127.0.0.1", "--port", "5173"],
        cwd="apps/web",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        print("Waiting for API server (127.0.0.1:8000)...")
        if not wait_for_url("http://127.0.0.1:8000/health", timeout=15):
            print("API server failed to start in time.")
            return

        print("Waiting for Vite console (127.0.0.1:5173)...")
        if not wait_for_url("http://127.0.0.1:5173", timeout=15):
            print("Vite console failed to start in time.")
            return

        time.sleep(2)
        print("3. Capturing high-resolution screenshots with headless Chrome...")
        for view, filename in VIEWS:
            target_url = f"http://127.0.0.1:5173/#{view}"
            output_file = SCREENSHOTS_DIR / filename
            print(f"   Capturing {view} -> {filename}...")

            cmd = [
                CHROME_BIN,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--window-size=1440,900",
                "--virtual-time-budget=3000",
                f"--screenshot={output_file.resolve()}",
                target_url,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)

        print("\nAll screenshots captured successfully:")
        for _, filename in VIEWS:
            path = SCREENSHOTS_DIR / filename
            if path.exists():
                print(f"  ✓ {filename} ({path.stat().st_size // 1024} KB)")

    finally:
        print("\nCleaning up background processes...")
        api_proc.terminate()
        web_proc.terminate()
        api_proc.wait()
        web_proc.wait()


if __name__ == "__main__":
    main()
