"""Run the full pipeline end to end inside the retail_spark container.

    docker compose exec spark python src/run_pipeline.py

Each step runs as a separate process; output is streamed to the console
and to logs/pipeline_<timestamp>.log. The run stops at the first failure.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"

STEPS = [
    ("Create warehouse schema", ["src/apply_sql.py", "sql/schema.sql"]),
    ("Ingest and clean raw CSV", ["src/ingest_sales.py"]),
    ("Verify cleaned Parquet", ["src/verify.py"]),
    ("Load star schema into PostgreSQL", ["src/load_to_postgres.py"]),
    ("Build reporting views", ["src/apply_sql.py", "sql/views.sql"]),
    ("Validate warehouse", ["src/validate_warehouse.py"]),
    ("Generate insights report", ["src/generate_report.py"]),
]


def main():
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"

    with log_path.open("w", encoding="utf-8") as log:
        def emit(line):
            sys.stdout.write(line)
            sys.stdout.flush()
            log.write(line)
            log.flush()

        pipeline_start = time.monotonic()
        for number, (name, args) in enumerate(STEPS, start=1):
            emit(f"\n{'=' * 70}\n[{number}/{len(STEPS)}] {name}\n{'=' * 70}\n")
            step_start = time.monotonic()

            process = subprocess.Popen(
                [sys.executable, *args],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in process.stdout:
                emit(line)
            return_code = process.wait()

            elapsed = time.monotonic() - step_start
            if return_code != 0:
                emit(f"\nFAILED: {name} (exit code {return_code}, {elapsed:.1f}s)\n")
                emit(f"Log: {log_path}\n")
                raise SystemExit(return_code)
            emit(f"\nOK: {name} ({elapsed:.1f}s)\n")

        total = time.monotonic() - pipeline_start
        emit(f"\nPipeline completed successfully in {total:.1f}s.\nLog: {log_path}\n")


if __name__ == "__main__":
    main()
