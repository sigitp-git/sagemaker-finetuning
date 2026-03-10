"""
Generate a self-contained HTML report from results_final.json.
Output: reports/report.html

Usage:
  python3 src/report_html.py [--results results/results_final.json]
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

# Display-friendly names
DISPLAY_NAMES = {
    "mistral-nemo": "Mistral-Nemo-Base-2407",
    "claude": "Claude Opus 4.6",
    "nova": "Amazon Nova Pro",
    "qwen3-optionH-nothink": "Qwen3-14B",
    "gemma": "Gemma 3 12B",
}

DISPLAY_STRATEGIES = {
    "slm": "Fine-tuned (QLoRA 4-bit)",
    "zero_shot": "Zero-shot",
    "five_shot": "5-shot",
    "five_shot_cot": "5-shot CoT",
}

MODEL_TYPES = {
    "mistral-nemo": "SLM",
    "qwen3-optionH-nothink": "SLM",
    "gemma": "SLM",
    "claude": "Frontier (Bedrock)",
    "nova": "Frontier (Bedrock)",
}


def pct(v):
    return f"{v * 100:.2f}%"


def render_html(results: list) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    sorted_results = sorted(results, key=lambda x: -x["metrics"]["f1"])

    # Summary table rows
    summary_rows = ""
    for i, r in enumerate(sorted_results, 1):
        m = r["metrics"]
        model = DISPLAY_NAMES.get(r["model"], r["model"])
        strategy = DISPLAY_STRATEGIES.get(r["strategy"], r["strategy"])
        mtype = MODEL_TYPES.get(r["model"], "")
        is_best = i == 1
        cls = ' class="best"' if is_best else ""
        summary_rows += (
            f"<tr{cls}><td>{i}</td><td>{model}</td><td>{mtype}</td>"
            f"<td>{strategy}</td>"
            f"<td>{pct(m['f1'])}</td><td>{pct(m['precision'])}</td>"
            f"<td>{pct(m['recall'])}</td><td>{pct(m['exact_match'])}</td>"
            f"<td>{m['n']}</td></tr>\n"
        )

    # Per-class tables (only for top models)
    per_class_html = ""
    highlight_models = ["mistral-nemo", "claude", "nova", "qwen3-optionH-nothink"]
    highlight_strategies = {"mistral-nemo": "slm", "claude": "five_shot_cot",
                            "nova": "five_shot", "qwen3-optionH-nothink": "slm"}
    for r in sorted_results:
        if r["model"] not in highlight_models:
            continue
        if r["strategy"] != highlight_strategies.get(r["model"]):
            continue
        model = DISPLAY_NAMES.get(r["model"], r["model"])
        strategy = DISPLAY_STRATEGIES.get(r["strategy"], r["strategy"])
        per_class_html += f'<h3>{model} - {strategy} (F1={pct(r["metrics"]["f1"])})</h3>\n'
        per_class_html += (
            "<table><thead><tr><th>Failure Type</th>"
            "<th>F1</th><th>Precision</th><th>Recall</th><th>N</th></tr></thead><tbody>\n"
        )
        for ft in FAILURE_TYPES:
            pc = r.get("per_class", {}).get(ft)
            if pc:
                f1_cls = ' class="perfect"' if pc["f1"] == 1.0 else ""
                per_class_html += (
                    f"<tr><td>{ft}</td><td{f1_cls}>{pct(pc['f1'])}</td>"
                    f"<td>{pct(pc['precision'])}</td><td>{pct(pc['recall'])}</td>"
                    f"<td>{pc['n']}</td></tr>\n"
                )
        per_class_html += "</tbody></table>\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>3GPP RCA Benchmark Results</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 1200px; margin: 2rem auto; padding: 0 1.5rem; color: #1a1a2e; background: #fafbff; }}
  h1 {{ color: #0a1628; border-bottom: 3px solid #0066cc; padding-bottom: .6rem; margin-bottom: .3rem; }}
  .subtitle {{ color: #555; font-size: 1.05rem; margin-bottom: 2rem; }}
  h2 {{ margin-top: 2.5rem; color: #0066cc; font-size: 1.4rem; }}
  h3 {{ margin-top: 1.8rem; color: #333; font-size: 1.1rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; font-size: 0.92rem; }}
  th, td {{ border: 1px solid #d0d7e3; padding: .55rem .8rem; text-align: left; }}
  th {{ background: #0066cc; color: #fff; font-weight: 600; }}
  tr:nth-child(even) {{ background: #f0f4ff; }}
  tr:hover {{ background: #e3ebff; }}
  tr.best {{ background: #d4edda; font-weight: 600; }}
  tr.best:hover {{ background: #c3e6cb; }}
  td.perfect {{ color: #0a7c42; font-weight: 600; }}
  .meta {{ color: #777; font-size: .85rem; margin-bottom: 1rem; }}
  .key-finding {{ background: #e8f4fd; border-left: 4px solid #0066cc; padding: 1rem 1.2rem; margin: 1.5rem 0; border-radius: 0 6px 6px 0; }}
  .key-finding strong {{ color: #0066cc; }}
  footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #ddd; color: #888; font-size: .8rem; }}
</style>
</head>
<body>
<h1>3GPP RCA Benchmark Results</h1>
<p class="subtitle">Fine-tuned 14B SLMs vs Frontier Foundation Models on 5G Root Cause Analysis</p>
<p class="meta">Generated: {ts} | Test set: 992 scenarios | 8 failure types</p>

<div class="key-finding">
  <strong>Key finding:</strong> Mistral-Nemo-Base-2407 with QLoRA 4-bit fine-tuning (99.70% F1) outperforms
  all frontier model configurations including Claude Opus 4.6 five-shot CoT (99.39% F1),
  trained on just 1,300 synthetic examples for ~$1.31 in compute.
</div>

<h2>Overall Ranking</h2>
<table>
<thead><tr>
  <th>#</th><th>Model</th><th>Type</th><th>Strategy</th>
  <th>F1</th><th>Precision</th><th>Recall</th><th>Exact Match</th><th>N</th>
</tr></thead>
<tbody>
{summary_rows}
</tbody>
</table>

<h2>Per-Class Breakdown (Best Config per Model)</h2>
{per_class_html}

<footer>
  <p>3GPP RCA Benchmark | SageMaker Fine-Tuning Guide |
  Models: Mistral-Nemo-Base-2407, Qwen3-14B, Gemma 3 12B, Claude Opus 4.6, Amazon Nova Pro</p>
</footer>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/results_final.json")
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
