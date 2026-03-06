/**
 * Generate a native .pptx presentation from results.json using pptxgenjs.
 * Output: reports/presentation.pptx
 *
 * Usage:
 *   npm install pptxgenjs
 *   node src/report_ppt.js --results results/results.json
 */

const PptxGenJS = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const resultsPath = args[args.indexOf("--results") + 1] || "results/results.json";
const outPath = args[args.indexOf("--out") + 1] || "reports/presentation.pptx";

const results = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
const pptx = new PptxGenJS();

pptx.layout = "LAYOUT_WIDE";
pptx.title = "3GPP RCA Benchmark Results";

const BLUE = "0066CC";
const WHITE = "FFFFFF";
const LIGHT = "F5F8FF";

// ── Slide 1: Title ──────────────────────────────────────────────────────────
const s1 = pptx.addSlide();
s1.background = { color: BLUE };
s1.addText("3GPP RCA Benchmark", {
  x: 1, y: 1.5, w: 11, h: 1.2,
  fontSize: 36, bold: true, color: WHITE, align: "center",
});
s1.addText("Fine-tuned SLMs vs Frontier Models\nF1 · Precision · Recall · Exact Match", {
  x: 1, y: 3, w: 11, h: 1.2,
  fontSize: 18, color: WHITE, align: "center",
});
s1.addText(new Date().toISOString().slice(0, 10), {
  x: 1, y: 4.5, w: 11, h: 0.5,
  fontSize: 12, color: WHITE, align: "center",
});

// ── Slide 2: Overall Metrics Table ──────────────────────────────────────────
const s2 = pptx.addSlide();
s2.addText("Overall Metrics", {
  x: 0.5, y: 0.3, w: 12, h: 0.6,
  fontSize: 24, bold: true, color: BLUE,
});

const sorted = [...results].sort((a, b) => b.metrics.f1 - a.metrics.f1);
const tableRows = [
  [
    { text: "Model",        options: { bold: true, fill: BLUE, color: WHITE } },
    { text: "Strategy",     options: { bold: true, fill: BLUE, color: WHITE } },
    { text: "F1",           options: { bold: true, fill: BLUE, color: WHITE } },
    { text: "Precision",    options: { bold: true, fill: BLUE, color: WHITE } },
    { text: "Recall",       options: { bold: true, fill: BLUE, color: WHITE } },
    { text: "Exact Match",  options: { bold: true, fill: BLUE, color: WHITE } },
  ],
  ...sorted.map((r, i) => [
    { text: r.model,                              options: { fill: i % 2 === 0 ? WHITE : LIGHT } },
    { text: r.strategy,                           options: { fill: i % 2 === 0 ? WHITE : LIGHT } },
    { text: r.metrics.f1.toFixed(4),              options: { fill: i % 2 === 0 ? WHITE : LIGHT } },
    { text: r.metrics.precision.toFixed(4),       options: { fill: i % 2 === 0 ? WHITE : LIGHT } },
    { text: r.metrics.recall.toFixed(4),          options: { fill: i % 2 === 0 ? WHITE : LIGHT } },
    { text: r.metrics.exact_match.toFixed(4),     options: { fill: i % 2 === 0 ? WHITE : LIGHT } },
  ]),
];

s2.addTable(tableRows, { x: 0.5, y: 1.1, w: 12, colW: [2.5, 2, 1.8, 1.8, 1.8, 2.1], fontSize: 12 });

// ── Slides 3+: Per-model per-class breakdown ─────────────────────────────────
const FAILURE_TYPES = [
  "core_network_failure", "authentication_failure", "normal",
  "handover_failure", "congestion", "qos_violation",
  "transport_jitter", "radio_failure",
];

for (const r of results) {
  const s = pptx.addSlide();
  s.addText(`${r.model} / ${r.strategy} — Per-Class`, {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontSize: 20, bold: true, color: BLUE,
  });

  const pcRows = [
    [
      { text: "Failure Type", options: { bold: true, fill: BLUE, color: WHITE } },
      { text: "F1",           options: { bold: true, fill: BLUE, color: WHITE } },
      { text: "Precision",    options: { bold: true, fill: BLUE, color: WHITE } },
      { text: "Recall",       options: { bold: true, fill: BLUE, color: WHITE } },
      { text: "N",            options: { bold: true, fill: BLUE, color: WHITE } },
    ],
    ...FAILURE_TYPES.map((ft, i) => {
      const pc = r.per_class?.[ft];
      const fill = i % 2 === 0 ? WHITE : LIGHT;
      return pc
        ? [
            { text: ft,                       options: { fill } },
            { text: pc.f1.toFixed(4),         options: { fill } },
            { text: pc.precision.toFixed(4),  options: { fill } },
            { text: pc.recall.toFixed(4),     options: { fill } },
            { text: String(pc.n),             options: { fill } },
          ]
        : [
            { text: ft,   options: { fill } },
            { text: "—",  options: { fill } },
            { text: "—",  options: { fill } },
            { text: "—",  options: { fill } },
            { text: "0",  options: { fill } },
          ];
    }),
  ];

  s.addTable(pcRows, { x: 0.5, y: 1.1, w: 12, colW: [3.5, 2, 2, 2, 2.5], fontSize: 12 });
}

// ── Write file ───────────────────────────────────────────────────────────────
fs.mkdirSync(path.dirname(outPath), { recursive: true });
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log(`Presentation saved to ${outPath}`);
});
