import time
"""
Runs the full benchmark suite in order:
    1. generate_testset.py  (skipped if benchmark/testset.jsonl already exists)
    2. bench_retrieval.py
    3. bench_latency.py
    4. bench_generation.py  (skipped with --skip-generation, or if GROQ_API_KEY unset)

Usage:
    export HF_TOKEN=...
    export GROQ_API_KEY=...
    python benchmark/run_all.py --n 40
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
load_dotenv(REPO_ROOT / ".env")

def run(cmd: list[str]):
    print(f"\n{'=' * 60}\n$ {' '.join(cmd)}\n{'=' * 60}")
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="test set size for generate_testset.py")
    ap.add_argument("--skip-generation", action="store_true")
    args = ap.parse_args()
    time.sleep(1)
    testset = BENCH_DIR / "testset.jsonl"
    if testset.exists():
        print(f"Reusing existing test set at {testset}")
    else:
        run([sys.executable, str(BENCH_DIR / "generate_testset.py"), "--n", str(args.n)])

    run([sys.executable, str(BENCH_DIR / "bench_retrieval.py")])
    run([sys.executable, str(BENCH_DIR / "bench_latency.py")] + (["--skip-generation"] if args.skip_generation else []))

    if not args.skip_generation and os.getenv("GROQ_API_KEY"):
        run([sys.executable, str(BENCH_DIR / "bench_generation.py")])
    else:
        print("\nSkipping bench_generation.py (--skip-generation or no GROQ_API_KEY).")

    print("\nAll done. Results:")
    for f in ["retrieval_results.json", "latency_results.json", "generation_results.jsonl"]:
        p = BENCH_DIR / f
        if p.exists():
            print(f"  - {p}")


if __name__ == "__main__":
    main()
