"""
Generate a self-contained HTML report from results.json.
Output: reports/report.html

Usage:
  python src/report_html.py --results results/results.json
"""

import argparse
import json
import os
from datetime import datetime

FAILURE_TYPES = [
    "core_network_failure", "authentication_failure", "normal",
    "handover_failure", "congestion", "qos_violation",
    "transport_jitter", "radio_failure",
]


def render_html(results: list) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Summary table rows
    summary_rows = ""
    for r in sorted(results, key=lambda x: -x["metrics"]["f1"]):
        m = r["metrics"]
        summary_rows += (
            f"<tr><td>{r['model']}</td><td>{r['strategy']}</td>"
            f"<td>{m['f1']:.4f}</td><td>{m['precision']:.4f}</td>"
            f"<td>{m['recall']:.4f}</td><td>{m['exact_match']:.4f}</td>"
            f"<td>{m['n']}</td></tr>\n"
        )

    # Per-class tables
    per_class_html = ""
    for r in results:
        per_class_html += f"<h3>{r['model']} / {r['strategy']}</h3>\n"
        per_class_html += (
            "<table><thead><tr><th>Failure Type</th>"
            "<th>F1</th><th>Precision</th><th>Recall</th><th>N</th></tr></thead><tbody>\n"
        )
        for ft in FAILURE_TYPES:
            pc = r.get("per_class", {}).get(ft)
            if pc:
                per_class_html += (
                    f"<tr><td>{ft}</td><td>{pc['f1']:.4f}</td>"
                    f"<td>{pc['precision']:.4f}</td><td>{pc['recall']:.4f}</td>"
                    f"<td>{pc['n']}</td></tr>\n"
                )
        per_class_html += "</tbody></table>\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>3GPP RCA Benchmark Results</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
  h1 {{ border-bottom: 2px solid #0066cc; padding-bottom: .5rem; }}
  h2 {{ margin-top: 2rem; color: #0066cc; }}
  h3 {{ margin-top: 1.5rem; color: #444; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }}
  th, td {{ border: 1px solid #ddd; padding: .5rem .75rem; text-align: left; }}
  th {{ background: #0066cc; color: #fff; }}
  tr:nth-child(even) {{ background: #f5f8ff; }}
  .meta {{ color: #666; font-size: .9rem; }}
</style>
</head>
<body>
<h1>3GPP RCA Benchmark — Results</h1>
<p class="meta">Generated: {ts}</p>

<h2>Overall Metrics</h2>
<table>
<thead><tr>
  <th>Model</th><th>Strategy</th><th>F1</th>
  <th>Precision</th><th>Recall</th><th>Exact Match</th><th>N</th>
</tr></thead>
<tbody>
{summary_rows}
</tbody>
</table>

<h2>Per-Class Breakdown</h2>
{per_class_html}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/results.json")
    parser.add_argument("--out", default="reports/report.html")
    args = parser.parse_args()

    with open(args.results) as f:
        results = json.load(f)

    html = render_html(results)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(html)
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
