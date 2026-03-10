/**
 * Generate a native .pptx presentation from results_final.json using pptxgenjs.
 * Output: reports/presentation.pptx
 *
 * Usage:
 *   npm install pptxgenjs
 *   node src/report_ppt.js [--results results/results_final.json]
 */

const PptxGenJS = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const resultsIdx = args.indexOf("--results");
const outIdx = args.indexOf("--out");
const resultsPath = resultsIdx >= 0 ? args[resultsIdx + 1] : "results/results_final.json";
const outPath = outIdx >= 0 ? args[outIdx + 1] : "reports/presentation.pptx";

const results = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
const pptx = new PptxGenJS();

pptx.layout = "LAYOUT_WIDE";
pptx.title = "3GPP RCA Benchmark Results";
pptx.author = "SageMaker Fine-Tuning Benchmark";

const BLUE = "0066CC";
const DARK = "0A1628";
const WHITE = "FFFFFF";
const LIGHT = "F0F4FF";
const GREEN = "D4EDDA";

const DISPLAY_NAMES = {
  "mistral-nemo": "Mistral-Nemo-Base-2407",
  "claude": "Claude Opus 4.6",
  "nova": "Amazon Nova Pro",
  "qwen3-optionH-nothink": "Qwen3-14B",
  "gemma": "Gemma 3 12B",
};

const DISPLAY_STRATEGIES = {
  "slm": "Fine-tuned (QLoRA 4-bit)",
  "zero_shot": "Zero-shot",
  "five_shot": "5-shot",
  "five_shot_cot": "5-shot CoT",
};

const MODEL_TYPES = {
  "mistral-nemo": "SLM",
  "qwen3-optionH-nothink": "SLM",
  "gemma": "SLM",
  "claude": "Frontier",
  "nova": "Frontier",
};

function pct(v) {
  return (v * 100).toFixed(2) + "%";
}

function displayName(model) {
  return DISPLAY_NAMES[model] || model;
}

function displayStrategy(strategy) {
  return DISPLAY_STRATEGIES[strategy] || strategy;
}

// ── Slide 1: Title ──────────────────────────────────────────────────────────
const s1 = pptx.addSlide();
s1.background = { color: DARK };
s1.addText("3GPP RCA Benchmark", {
  x: 0.8, y: 1.2, w: 11.5, h: 1.2,
  fontSize: 40, bold: true, color: WHITE, align: "center",
  fontFace: "Arial",
});
s1.addText("Fine-tuned 14B SLMs vs Frontier Foundation Models\non 5G Standalone Root Cause Analysis", {
  x: 0.8, y: 2.8, w: 11.5, h: 1.0,
  fontSize: 18, color: "AABBDD", align: "center",
  fontFace: "Arial",
});
s1.addText("992 test scenarios · 8 failure types · F1 / Precision / Recall / Exact Match", {
  x: 0.8, y: 4.2, w: 11.5, h: 0.5,
  fontSize: 13, color: "8899BB", align: "center",
  fontFace: "Arial",
});
s1.addText(new Date().toISOString().slice(0, 10), {
  x: 0.8, y: 5.0, w: 11.5, h: 0.4,
  fontSize: 11, color: "667799", align: "center",
  fontFace: "Arial",
});

// ── Slide 2: Key Finding ────────────────────────────────────────────────────
const s2 = pptx.addSlide();
s2.addText("Key Finding", {
  x: 0.5, y: 0.3, w: 12, h: 0.6,
  fontSize: 28, bold: true, color: DARK, fontFace: "Arial",
});
s2.addShape(pptx.ShapeType.rect, {
  x: 0.5, y: 1.2, w: 12, h: 2.5,
  fill: { color: "E8F4FD" },
  line: { color: BLUE, width: 2, dashType: "solid" },
  rectRadius: 0.1,
});
s2.addText(
  "Mistral-Nemo-Base-2407 with QLoRA 4-bit fine-tuning achieves 99.70% F1,\n" +
  "outperforming all frontier model configurations including\n" +
  "Claude Opus 4.6 five-shot CoT (99.39% F1).\n\n" +
  "Trained on 1,300 synthetic examples · ~$1.31 compute cost · ~41 min on 1× A10G",
  {
    x: 0.8, y: 1.4, w: 11.4, h: 2.1,
    fontSize: 17, color: DARK, align: "center",
    fontFace: "Arial", lineSpacingMultiple: 1.3,
  }
);

// ── Slide 3: Overall Ranking Table ──────────────────────────────────────────
const s3 = pptx.addSlide();
s3.addText("Overall Ranking", {
  x: 0.5, y: 0.3, w: 12, h: 0.6,
  fontSize: 24, bold: true, color: DARK, fontFace: "Arial",
});

const sorted = [...results].sort((a, b) => b.metrics.f1 - a.metrics.f1);
const headerOpts = { bold: true, fill: BLUE, color: WHITE, fontSize: 11, fontFace: "Arial" };
const tableRows = [
  [
    { text: "#", options: headerOpts },
    { text: "Model", options: headerOpts },
    { text: "Type", options: headerOpts },
    { text: "Strategy", options: headerOpts },
    { text: "F1", options: headerOpts },
    { text: "Precision", options: headerOpts },
    { text: "Recall", options: headerOpts },
    { text: "Exact Match", options: headerOpts },
  ],
  ...sorted.map((r, i) => {
    const isBest = i === 0;
    const fill = isBest ? GREEN : i % 2 === 0 ? WHITE : LIGHT;
    const bold = isBest;
    const opts = { fill, fontSize: 10, fontFace: "Arial", bold };
    return [
      { text: String(i + 1), options: opts },
      { text: displayName(r.model), options: opts },
      { text: MODEL_TYPES[r.model] || "", options: opts },
      { text: displayStrategy(r.strategy), options: opts },
      { text: pct(r.metrics.f1), options: opts },
      { text: pct(r.metrics.precision), options: opts },
      { text: pct(r.metrics.recall), options: opts },
      { text: pct(r.metrics.exact_match), options: opts },
    ];
  }),
];

s3.addTable(tableRows, {
  x: 0.3, y: 1.1, w: 12.5,
  colW: [0.5, 2.8, 1.2, 2.2, 1.3, 1.3, 1.3, 1.4],
  border: { type: "solid", pt: 0.5, color: "D0D7E3" },
});

// ── Slides 4+: Per-class breakdown for best config per model ────────────────
const FAILURE_TYPES = [
  "core_network_failure", "authentication_failure", "normal",
  "handover_failure", "congestion", "qos_violation",
  "transport_jitter", "radio_failure",
];

const bestConfigs = {
  "mistral-nemo": "slm",
  "claude": "five_shot_cot",
  "nova": "five_shot",
  "qwen3-optionH-nothink": "slm",
};

for (const r of sorted) {
  if (bestConfigs[r.model] !== r.strategy) continue;

  const s = pptx.addSlide();
  s.addText(`${displayName(r.model)} - ${displayStrategy(r.strategy)}`, {
    x: 0.5, y: 0.3, w: 10, h: 0.5,
    fontSize: 20, bold: true, color: DARK, fontFace: "Arial",
  });
  s.addText(`Overall F1: ${pct(r.metrics.f1)}`, {
    x: 0.5, y: 0.8, w: 5, h: 0.4,
    fontSize: 14, color: BLUE, fontFace: "Arial",
  });

  const pcHeader = { bold: true, fill: BLUE, color: WHITE, fontSize: 11, fontFace: "Arial" };
  const pcRows = [
    [
      { text: "Failure Type", options: pcHeader },
      { text: "F1", options: pcHeader },
      { text: "Precision", options: pcHeader },
      { text: "Recall", options: pcHeader },
      { text: "N", options: pcHeader },
    ],
    ...FAILURE_TYPES.map((ft, i) => {
      const pc = r.per_class?.[ft];
      const fill = i % 2 === 0 ? WHITE : LIGHT;
      const isPerfect = pc && pc.f1 === 1.0;
      const opts = { fill, fontSize: 10, fontFace: "Arial", bold: isPerfect };
      return pc
        ? [
            { text: ft, options: opts },
            { text: pct(pc.f1), options: { ...opts, color: isPerfect ? "0A7C42" : DARK } },
            { text: pct(pc.precision), options: opts },
            { text: pct(pc.recall), options: opts },
            { text: String(pc.n), options: opts },
          ]
        : [
            { text: ft, options: opts },
            { text: "—", options: opts },
            { text: "—", options: opts },
            { text: "—", options: opts },
            { text: "0", options: opts },
          ];
    }),
  ];

  s.addTable(pcRows, {
    x: 0.5, y: 1.4, w: 12,
    colW: [3.5, 2, 2, 2, 2.5],
    border: { type: "solid", pt: 0.5, color: "D0D7E3" },
  });
}

// ── Final Slide: Summary ────────────────────────────────────────────────────
const sLast = pptx.addSlide();
sLast.background = { color: DARK };
sLast.addText("Summary", {
  x: 0.8, y: 0.5, w: 11.5, h: 0.7,
  fontSize: 28, bold: true, color: WHITE, align: "center", fontFace: "Arial",
});

const bullets = [
  "Mistral-Nemo QLoRA 4-bit: 99.70% F1 — #1 overall, beats all frontier models",
  "Claude Opus 4.6 five-shot CoT: 99.39% F1 — best frontier configuration",
  "Qwen3-14B with chat template + /no_think: 77.42% F1 — competitive after optimization",
  "Gemma 3 12B: 11.90% F1 — requires more fundamental changes",
  "Domain-specific fine-tuning on 1,300 examples for ~$1.31 matches frontier models",
];

sLast.addText(
  bullets.map((b) => ({ text: "• " + b + "\n", options: { fontSize: 14, color: "CCDDEE", fontFace: "Arial", lineSpacingMultiple: 1.6 } })),
  { x: 1.0, y: 1.6, w: 11, h: 4.5 }
);

// ── Write file ───────────────────────────────────────────────────────────────
fs.mkdirSync(path.dirname(outPath), { recursive: true });
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log(`Presentation saved to ${outPath}`);
});
