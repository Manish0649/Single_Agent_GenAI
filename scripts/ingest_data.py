"""
Standalone data ingestion script.

Usage:
    python scripts/ingest_data.py [--dataset PATH] [--batch-size N] [--force-recreate]

This script:
1. Loads the CSV dataset.
2. Runs the data quality report.
3. Builds searchable customer summary documents.
4. Indexes them in Milvus.

Run this before starting the application for the first time or when
the dataset is updated.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.loader import load_dataset
from app.data.quality_checks import produce_report
from app.rag.document_builder import build_documents_from_df
from app.rag.milvus_store import ingest_documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest customer data into Milvus.")
    parser.add_argument("--dataset", type=Path, default=None, help="Path to CSV file.")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Drop and recreate the Milvus collection.",
    )
    parser.add_argument(
        "--quality-report-out",
        type=Path,
        default=Path("data/quality_report.json"),
        help="Where to write the data quality report.",
    )
    args = parser.parse_args()

    # ── Load ──────────────────────────────────────────────────────────────────
    logger.info("Loading dataset …")
    df = load_dataset(args.dataset)
    logger.info("Loaded %d rows, %d columns.", len(df), len(df.columns))

    # ── Quality report ────────────────────────────────────────────────────────
    logger.info("Running data quality checks …")
    report = produce_report()
    args.quality_report_out.parent.mkdir(parents=True, exist_ok=True)
    args.quality_report_out.write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    logger.info("Quality report written to %s", args.quality_report_out)

    # ── Build documents ───────────────────────────────────────────────────────
    logger.info("Building searchable documents …")
    docs = build_documents_from_df(df)
    logger.info("Built %d documents.", len(docs))

    # ── Ingest ────────────────────────────────────────────────────────────────
    logger.info("Indexing into Milvus (force_recreate=%s) …", args.force_recreate)
    n = ingest_documents(docs, batch_size=args.batch_size, drop_old=args.force_recreate)
    logger.info("Done. %d documents indexed.", n)


if __name__ == "__main__":
    main()
