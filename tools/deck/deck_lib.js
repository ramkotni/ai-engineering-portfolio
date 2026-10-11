// Shared slide-deck builder for the portfolio projects (pptxgenjs + theme post-processing).
// Each project has docs/deck_spec.js that calls these helpers; build with:
//   cd tools/deck && npm install && node build.js <project-folder>
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");

function makeTheme(accent) {
  return {
    name: "Portfolio",
    headFontFace: "Arial",
    bodyFontFace: "Calibri",
    colors: {
      dk1: "1B2430", lt1: "FFFFFF", dk2: "24303D", lt2: "EEF1F4",
      accent1: accent || "F2A900",   // project accent
      accent2: "D64933", accent3: "2D7DD2", accent4: "2E9E6B", accent5: "6B7785", accent6: "7A5CC4",
      hlink: "2D7DD2", folHlink: "7A5CC4",
    },
  };
}

class Deck {
  constructor({ title, subtitle, footer, accent }) {
    this.THEME = makeTheme(accent);
    this.HEX = this.THEME.colors;
    this.pres = new pptxgen();
    this.pres.layout = "LAYOUT_WIDE";
    this.pres.title = title;
    this.pres.theme = { headFontFace: this.THEME.headFontFace, bodyFontFace: this.THEME.bodyFontFace };
    this.C = this.pres.SchemeColor;
    this.MONO = "Courier New";
    const C = this.C;
    this.pres.defineSlideMaster({
      title: "TITLE_DARK", background: { color: C.text2 },
      objects: [
        { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 11.7, h: 1.5, fontSize: 48, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
        { placeholder: { options: { name: "subtitle", type: "body", x: 0.8, y: 3.7, w: 11.7, h: 1.0, fontSize: 22, color: C.accent1, align: "left", valign: "top", margin: 0 }, text: "" } },
      ],
    });
    this.pres.defineSlideMaster({
      title: "CONTENT", background: { color: C.background1 },
      objects: [
        { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 34, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
        { text: { text: footer || title, options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
      ],
      slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
    });
    this.section = null;
    const s = this.pres.addSlide({ masterName: "TITLE_DARK" });
    s.addText(title, { placeholder: "title" });
    s.addText(subtitle || "", { placeholder: "subtitle" });
    this.titleSlide = s;
  }

  // ---------------------------------------------------------------- primitives
  text(slide, t, o) {
    return slide.addText(t, { isTextBox: true, margin: 0, valign: "top", fontSize: 14, color: this.C.text1, ...o });
  }
  card(slide, x, y, w, h, fill) {
    slide.addShape(this.pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || this.C.background2 }, line: { color: fill || this.C.background2 } });
  }
  badge(slide, x, y, d, label, fill, fontSize = 14) {
    slide.addShape(this.pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
    this.text(slide, label, { x, y, w: d, h: d, align: "center", valign: "middle", bold: true, fontSize, color: this.C.background1 });
  }
  arrow(slide, x1, y1, x2, y2, { color, dash = "solid", width = 1.75, head = true } = {}) {
    slide.addShape(this.pres.shapes.LINE, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.001), h: Math.max(Math.abs(y2 - y1), 0.001),
      flipH: x2 < x1, flipV: y2 < y1, line: { color: color || this.C.accent5, width, dashType: dash, endArrowType: head ? "triangle" : undefined },
    });
  }
  node(slide, x, y, w, h, title, caption, { fill, color, titleColor, outline } = {}) {
    const f = fill || this.C.background2;
    slide.addShape(this.pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: f }, line: { color: outline || f, width: outline ? 1.5 : 0.75 } });
    const runs = [{ text: title, options: { bold: true, fontSize: 13, color: titleColor || (fill && fill !== this.C.background2 && fill !== this.C.background1 ? this.C.background1 : this.C.text1), breakLine: !!caption } }];
    if (caption) runs.push({ text: caption, options: { fontSize: 10.5, color: color || (fill && fill !== this.C.background2 && fill !== this.C.background1 ? this.C.background1 : this.C.accent5) } });
    this.text(slide, runs, { x: x + 0.06, y, w: w - 0.12, h, align: "center", valign: "middle" });
  }
  code(slide, x, y, w, h, code, fontSize = 12) {
    if (!h) h = 0.45 + code.split(String.fromCharCode(10)).length * fontSize * 0.0205;
    slide.addShape(this.pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: this.C.text2 }, line: { color: this.C.text2 } });
    this.text(slide, code, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: h - 0.36, fontFace: this.MONO, fontSize, color: this.C.background1 });
  }

  // ---------------------------------------------------------------- slide templates
  slide(section, title) {
    if (section !== this.section) {
      this.pres.addSection({ title: section });
      this.section = section;
    }
    const s = this.pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
    s.addText(title, { placeholder: "title" });
    return s;
  }

  // Numbered cards in a grid. items: [[title, desc], ...]
  cards(section, title, items, { cols = 3, intro, notes, color } = {}) {
    const s = this.slide(section, title);
    let top = 1.45;
    if (intro) { this.text(s, intro, { x: 0.6, y: 1.4, w: 12.1, h: 0.5, fontSize: 15, color: this.C.accent5 }); top = 2.0; }
    const rows = Math.ceil(items.length / cols), gap = 0.25;
    const w = (12.1 - gap * (cols - 1)) / cols, h = Math.min(rows > 1 ? 1.75 : 2.2, (6.75 - top - gap * (rows - 1)) / rows);
    items.forEach(([t, d], i) => {
      const x = 0.6 + (i % cols) * (w + gap), y = top + Math.floor(i / cols) * (h + gap);
      this.card(s, x, y, w, h);
      this.badge(s, x + 0.2, y + 0.2, 0.5, String(i + 1), color || this.C.accent1, 14);
      this.text(s, [{ text: t, options: { bold: true, fontSize: 16, breakLine: true } }, { text: d, options: { fontSize: 13 } }],
        { x: x + 0.85, y: y + 0.15, w: w - 1.0, h: h - 0.25 });
    });
    if (notes) s.addNotes(notes);
    return s;
  }

  // Table slide. rows[0] = header.
  table(section, title, rows, { colW, notes, caption, fontSize = 13 } = {}) {
    const s = this.slide(section, title);
    const head = rows[0].map((t) => ({ text: t, options: { bold: true, color: this.HEX.lt1, fill: { color: this.HEX.dk2 }, fontSize: 14 } }));
    const body = rows.slice(1).map((r) => r.map((t, j) => ({ text: String(t), options: { fontSize, color: this.HEX.dk1, bold: j === 0 } })));
    const rowH = Math.min(0.55, 5.2 / rows.length);
    s.addTable([head, ...body], { x: 0.6, y: 1.45, w: 12.1, colW, border: { type: "solid", pt: 0.75, color: "D9DEE4" }, rowH, valign: "middle", fill: { color: this.HEX.lt1 } });
    if (caption) this.text(s, caption, { x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontSize: 12, color: this.C.accent5 });
    if (notes) s.addNotes(notes);
    return s;
  }

  // Horizontal pipeline of steps with arrows; optional caption under it.
  pipeline(section, title, steps, { notes, below } = {}) {
    const s = this.slide(section, title);
    const n = steps.length, gap = 0.3, w = (12.1 - gap * (n - 1)) / n;
    steps.forEach(([t, d], i) => {
      const x = 0.6 + i * (w + gap);
      this.node(s, x, 1.6, w, 1.5, t, d, i % 2 ? {} : {});
      if (i < n - 1) this.arrow(s, x + w + 0.02, 2.35, x + w + gap - 0.02, 2.35, { color: this.C.accent1, width: 2 });
    });
    if (below) below(s);
    if (notes) s.addNotes(notes);
    return s;
  }

  // Big numbers. stats: [[value, label], ...]
  stats(section, title, stats, { notes, caption } = {}) {
    const s = this.slide(section, title);
    const cols = Math.min(stats.length, 4), w = 12.1 / cols;
    stats.forEach(([v, l], i) => {
      const x = 0.6 + (i % cols) * w, y = 1.7 + Math.floor(i / cols) * 2.3;
      this.text(s, v, { x, y, w: w - 0.3, h: 1.0, fontSize: 48, bold: true, color: this.C.accent1, fontFace: this.THEME.headFontFace });
      this.text(s, l, { x, y: y + 1.05, w: w - 0.4, h: 0.9, fontSize: 14 });
    });
    if (caption) this.text(s, caption, { x: 0.6, y: 6.3, w: 12.1, h: 0.5, fontSize: 12, color: this.C.accent5 });
    if (notes) s.addNotes(notes);
    return s;
  }

  // Code on the left, numbered explanation on the right.
  codeSlide(section, title, codeText, points, { notes, fontSize = 12 } = {}) {
    const s = this.slide(section, title);
    const lines = codeText.split("\n").length;
    this.code(s, 0.6, 1.45, 6.9, Math.min(5.3, 0.45 + lines * fontSize * 0.0205), codeText, fontSize);
    points.forEach(([t, d], i) => {
      const y = 1.5 + i * (5.2 / points.length);
      this.badge(s, 7.85, y, 0.45, String(i + 1), this.C.accent1, 13);
      this.text(s, [{ text: t, options: { bold: true, fontSize: 15, breakLine: true } }, { text: d, options: { fontSize: 13 } }], { x: 8.45, y: y - 0.05, w: 4.25, h: 5.2 / points.length - 0.1 });
    });
    if (notes) s.addNotes(notes);
    return s;
  }

  // Free-form slide: callback receives (slide, deck).
  custom(section, title, draw, { notes } = {}) {
    const s = this.slide(section, title);
    draw(s, this);
    if (notes) s.addNotes(notes);
    return s;
  }

  closing(title, items) {
    this.pres.defineSlideMaster({
      title: "CLOSING", background: { color: this.C.text2 },
      objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.8, y: 0.7, w: 11.7, h: 1.1, fontSize: 44, bold: true, color: this.C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } }],
    });
    const s = this.pres.addSlide({ masterName: "CLOSING", sectionTitle: this.section });
    s.addText(title, { placeholder: "title" });
    items.forEach((t, i) => {
      const y = 2.3 + i * 0.8;
      this.badge(s, 0.8, y, 0.5, String(i + 1), this.C.accent1, 15);
      this.text(s, t, { x: 1.55, y, w: 11.0, h: 0.5, fontSize: 17, color: this.C.background1, valign: "middle" });
    });
    return s;
  }

  async save(file) {
    await this.pres.writeFile({ fileName: file });
    await applyTheme(file, this.THEME);
    console.log(`Wrote ${file}`);
  }
}

module.exports = { Deck };
