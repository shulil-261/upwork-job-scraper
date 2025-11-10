import csv
import json
from typing import Any, Dict, List

class DataExporter:
    def to_json(self, rows: List[Dict[str, Any]], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    def to_csv(self, rows: List[Dict[str, Any]], path: str) -> None:
        if not rows:
            # create an empty CSV with no rows but still valid
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write("")
            return

        # Union of all keys across rows
        fieldnames = set()
        for r in rows:
            fieldnames.update(r.keys())
        ordered = [
            "Date Scraped",
            "Job ID",
            "Time Posted",
            "Project Payment Type",
            "Budget",
            "Skill Level",
            "Title",
            "URL",
            "Description",
            "Location",
            "Total Spent",
            "Feedback",
            "Proposals",
            "Project Length",
            "Weekly Hours",
            "Skills",
            "Query",
            "Source",
        ]
        # Preserve preferred order then add the rest
        for k in sorted(fieldnames):
            if k not in ordered:
                ordered.append(k)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ordered)
            writer.writeheader()
            for r in rows:
                r_copy = dict(r)
                # Serialize lists as comma-joined strings for CSV
                if isinstance(r_copy.get("Skills"), list):
                    r_copy["Skills"] = ", ".join(r_copy["Skills"])
                writer.writerow(r_copy)