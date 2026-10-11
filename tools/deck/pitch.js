// One-slide client pitch from a project's docs/pitch_spec.js:
//   cd tools/deck && node pitch.js ../../07-healthcare-condition-briefing
// Layout (16:9): header band | problem + users | how it works (pipeline) | proof + trust | value / next-steps bar.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");

const projectDir = path.resolve(process.argv[2] || ".");
const spec = require(path.join(projectDir, "docs", "pitch_spec.js"));
const out = process.env.DECK_OUT || path.join(projectDir, "docs", spec.fileName);

const THEME = {
  name: "Portfolio Pitch",
  colors: {
    dk1: "1B2430", lt1: "FFFFFF", dk2: "24303D", lt2: "EEF1F4",
    accent1: spec.accent, accent2: "D64933", accent3: "2D7DD2", accent4: "2E9E6B", accent5: "6B7785", accent6: "7A5CC4",
    hlink: "2D7DD2", folHlink: "7A5CC4",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 in
pres.title = spec.title;
pres.theme = { headFontFace: "Arial", bodyFontFace: "Calibri" };
const C = pres.SchemeColor;
const s = pres.addSlide();
s.background = { color: C.background1 };

const text = (t, o) => s.addText(t, { isTextBox: true, margin: 0, valign: "top", fontSize: 12, color: C.text1, ...o });
const card = (x, y, w, h, fill) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: fill }, line: { color: fill } });
const label = (t, x, y, w) => text(t.toUpperCase(), { x, y, w, h: 0.28, fontSize: 10.5, bold: true, color: C.accent1, charSpacing: 1 });
const bullets = (items, o) => text(items.map((t, i) => ({ text: t, options: { bullet: { indent: 12 }, breakLine: i < items.length - 1, paraSpaceAfter: 4 } })), o);

// ---------------------------------------------------------------- header band
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 13.33, h: 1.25, fill: { color: C.text2 }, line: { color: C.text2 } });
text(spec.title, { x: 0.45, y: 0.17, w: 9.6, h: 0.55, fontSize: 26, bold: true, color: C.background1, fontFace: "Arial" });
text(spec.tagline, { x: 0.45, y: 0.72, w: 10.2, h: 0.4, fontSize: 14, color: C.accent1 });
text(spec.client, { x: 10.2, y: 0.25, w: 2.7, h: 0.75, fontSize: 10.5, color: C.background1, align: "right", valign: "middle" });

// ---------------------------------------------------------------- column 1: problem + users
const top = 1.45;
card(0.4, top, 3.85, 2.75, C.background2);
label("The problem", 0.6, top + 0.15, 3.5);
bullets(spec.problem, { x: 0.6, y: top + 0.48, w: 3.5, h: 2.2, fontSize: 11.5 });
card(0.4, top + 2.9, 3.85, 1.85, C.background2);
label("Who uses it", 0.6, top + 3.05, 3.5);
bullets(spec.users, { x: 0.6, y: top + 3.38, w: 3.5, h: 1.35, fontSize: 11 });

// ---------------------------------------------------------------- column 2: how it works
label("How it works", 4.5, top + 0.0, 4.4);
const steps = spec.steps;
const stepH = 0.52, gap = 0.14;
steps.forEach(([title, caption], i) => {
  const y = top + 0.35 + i * (stepH + gap);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.5, y, w: 4.45, h: stepH, rectRadius: 0.06,
    fill: { color: i === spec.highlightStep ? C.accent1 : C.background2 }, line: { color: i === spec.highlightStep ? C.accent1 : C.background2 } });
  s.addShape(pres.shapes.OVAL, { x: 4.6, y: y + 0.1, w: 0.32, h: 0.32, fill: { color: C.text2 }, line: { color: C.text2 } });
  text(String(i + 1), { x: 4.6, y: y + 0.1, w: 0.32, h: 0.32, fontSize: 10.5, bold: true, color: C.background1, align: "center", valign: "middle" });
  const hi = i === spec.highlightStep;
  text([{ text: title, options: { bold: true, fontSize: 11.5, breakLine: true, color: hi ? C.background1 : C.text1 } },
        { text: caption, options: { fontSize: 9.5, color: hi ? C.background1 : C.accent5 } }],
    { x: 5.05, y: y + 0.03, w: 3.85, h: stepH - 0.04, valign: "middle" });
});
const visY = top + 0.35 + steps.length * (stepH + gap) + 0.05;
if (spec.image && fs.existsSync(spec.image.path)) {
  const h = Math.min(spec.image.h, 6.25 - visY);
  s.addImage({ path: spec.image.path, x: 4.5, y: visY, w: h * spec.image.ratio, h });
  text(spec.image.caption, { x: 4.5 + h * spec.image.ratio + 0.12, y: visY, w: 4.45 - h * spec.image.ratio - 0.12, h, fontSize: 9.5, color: C.accent5, valign: "middle" });
} else if (spec.chart) {
  s.addChart(pres.charts.LINE, [{ name: spec.chart.name, labels: spec.chart.labels, values: spec.chart.values }], {
    x: 4.4, y: visY - 0.05, w: 4.65, h: 6.3 - visY, chartColors: [spec.accent], lineSize: 2, lineDataSymbol: "none",
    catAxisHidden: true, valAxisLabelFontSize: 8, valAxisMinVal: spec.chart.min, valAxisMaxVal: spec.chart.max, valAxisLabelColor: "6B7785", valGridLine: { color: "E3E7EB", size: 0.5 },
    showLegend: false, showTitle: true, title: spec.chart.title, titleFontSize: 9.5, titleColor: "6B7785",
  });
}

// ---------------------------------------------------------------- column 3: proof + trust
label("Proof from the prototype", 9.2, top, 3.8);
spec.proof.forEach(([value, caption], i) => {
  const y = top + 0.35 + i * 0.66;
  text(value, { x: 9.2, y, w: 1.45, h: 0.55, fontSize: 21, bold: true, color: C.text2, valign: "middle", fontFace: "Arial" });
  text(caption, { x: 10.7, y, w: 2.3, h: 0.55, fontSize: 10, color: C.accent5, valign: "middle" });
});
const trustY = top + 0.35 + spec.proof.length * 0.66 + 0.1;
card(9.2, trustY, 3.75, 6.3 - trustY, C.background2);
label("Built to be trusted", 9.4, trustY + 0.12, 3.4);
bullets(spec.trust, { x: 9.4, y: trustY + 0.45, w: 3.45, h: 6.2 - trustY - 0.5, fontSize: 10.5 });

// ---------------------------------------------------------------- bottom bar: value + next steps
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 6.45, w: 13.33, h: 1.05, fill: { color: C.text2 }, line: { color: C.text2 } });
text("VALUE", { x: 0.45, y: 6.58, w: 1.2, h: 0.3, fontSize: 10.5, bold: true, color: C.accent1 });
text(spec.value, { x: 0.45, y: 6.86, w: 7.4, h: 0.55, fontSize: 12, color: C.background1 });
text("NEXT STEP", { x: 8.2, y: 6.58, w: 2, h: 0.3, fontSize: 10.5, bold: true, color: C.accent1 });
text(spec.next, { x: 8.2, y: 6.86, w: 4.75, h: 0.55, fontSize: 12, color: C.background1 });

if (spec.notes) s.addNotes(spec.notes);

pres.writeFile({ fileName: out }).then(() => applyTheme(out, THEME)).then(() => console.log(`Wrote ${out}`))
  .catch((e) => { console.error(e); process.exit(1); });
