"""Run all 5 MCP mock servers concurrently."""

import subprocess
import sys
from pathlib import Path

SERVERS = [
    ("identity_kyc", 8010),
    ("product_catalog", 8011),
    ("credit_eligibility", 8012),
    ("offers_pricing", 8013),
    ("contract_disbursement", 8014),
]

def main():
    base = Path(__file__).parent
    procs = []
    for name, port in SERVERS:
        script = base / name / "server.py"
        print(f"Starting {name} on port {port}...")
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(base / name),
        )
        procs.append((name, proc))

    print(f"\n✅ All {len(SERVERS)} MCP servers running:")
    for name, port in SERVERS:
        print(f"   {name}: http://localhost:{port}/mcp")

    try:
        for _, proc in procs:
            proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        for _, proc in procs:
            proc.terminate()

if __name__ == "__main__":
    main()
