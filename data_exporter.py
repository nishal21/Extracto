"""
data_exporter.py — turns AI output into actual files.

Supports JSON, CSV, XML, SQLite, Excel, and Markdown.
Attaches source_url and crawl_depth to every row so you
know where each piece of data came from.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from typing import Any, Sequence

import pandas as pd

logger = logging.getLogger(__name__)


class DataExporter:
    """Normalizes AI output and writes it to whatever format the user wants."""

    @staticmethod
    def _flatten(page_results: list[dict[str, Any]]) -> list[dict]:
        """
        Take the per-page results (each with data + metadata) and
        flatten into a single list of rows with source info attached.
        """
        rows: list[dict] = []

        for page in page_results:
            data = page["data"]
            source_url = page.get("source_url", "")
            depth = page.get("depth", 0)

            # ScrapeGraphAI often wraps results in a dict with one key
            if isinstance(data, dict):
                lists = [v for v in data.values() if isinstance(v, list)]
                if len(lists) == 1:
                    data = lists[0]
                else:
                    data = [data]

            if not isinstance(data, list):
                data = [{"value": data}]

            for item in data:
                if not isinstance(item, dict):
                    item = {"value": item}
                item["_source_url"] = source_url
                item["_crawl_depth"] = depth
                rows.append(item)

        return rows

    @classmethod
    def export(
        cls,
        data: Sequence[dict[str, Any]],
        fmt: str,
        output_dir: str = "output",
        filename: str = "scraped_data",
    ) -> str:
        """Flatten all results, write to disk, return the output path."""

        rows = cls._flatten(list(data))
        if not rows:
            logger.warning("Nothing to export, creating empty file")
            rows = [{"_empty": True}]

        df = pd.json_normalize(rows)
        os.makedirs(output_dir, exist_ok=True)
        fmt = fmt.strip().lower()

        writers = {
            "json": cls._write_json,
            "csv": cls._write_csv,
            "xml": cls._write_xml,
            "sql": cls._write_sql,
            "excel": cls._write_excel,
            "markdown": cls._write_markdown,
        }

        writer = writers.get(fmt)
        if not writer:
            raise ValueError(f"Unknown format '{fmt}'. Options: {', '.join(writers)}")

        path = writer(df, output_dir, filename)
        logger.info("Wrote %d rows → %s", len(df), path)
        return path

    @classmethod
    def write_summary(
        cls,
        output_dir: str,
        pages_crawled: int,
        pages_failed: int,
        elapsed: float,
        output_path: str,
    ) -> str:
        """Drop a summary txt next to the data file."""
        summary_path = os.path.join(output_dir, "run_summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"Pages crawled:  {pages_crawled}\n")
            f.write(f"Pages failed:   {pages_failed}\n")
            f.write(f"Time:           {elapsed:.1f}s\n")
            f.write(f"Output:         {output_path}\n")
            f.write(f"Timestamp:      {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        return summary_path

    # ---- format writers ----

    @staticmethod
    def _write_json(df: pd.DataFrame, out_dir: str, name: str) -> str:
        p = os.path.join(out_dir, f"{name}.json")
        df.to_json(p, orient="records", indent=2, force_ascii=False)
        return os.path.abspath(p)

    @staticmethod
    def _write_csv(df: pd.DataFrame, out_dir: str, name: str) -> str:
        p = os.path.join(out_dir, f"{name}.csv")
        df.to_csv(p, index=False, encoding="utf-8-sig")
        return os.path.abspath(p)

    @staticmethod
    def _write_xml(df: pd.DataFrame, out_dir: str, name: str) -> str:
        p = os.path.join(out_dir, f"{name}.xml")
        df.to_xml(p, index=False, root_name="data", row_name="record")
        return os.path.abspath(p)

    @staticmethod
    def _write_sql(df: pd.DataFrame, out_dir: str, name: str) -> str:
        p = os.path.join(out_dir, f"{name}.db")
        conn = sqlite3.connect(p)
        try:
            df.to_sql("scraped_data", conn, if_exists="replace", index=False)
        finally:
            conn.close()
        return os.path.abspath(p)

    @staticmethod
    def _write_excel(df: pd.DataFrame, out_dir: str, name: str) -> str:
        p = os.path.join(out_dir, f"{name}.xlsx")
        df.to_excel(p, index=False, engine="openpyxl")
        return os.path.abspath(p)

    @staticmethod
    def _write_markdown(df: pd.DataFrame, out_dir: str, name: str) -> str:
        p = os.path.join(out_dir, f"{name}.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(df.to_markdown(index=False))
        return os.path.abspath(p)
