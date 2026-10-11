// Build a project's deck:  node build.js ../../01-payment-ops-intelligence
const path = require("path");
const fs = require("fs");

const projectDir = path.resolve(process.argv[2] || ".");
const spec = require(path.join(projectDir, "docs", "deck_spec.js"));
const out = process.env.DECK_OUT || path.join(projectDir, "docs", spec.fileName);
fs.mkdirSync(path.dirname(out), { recursive: true });
spec.build(require("./deck_lib.js").Deck).save(out).catch((e) => { console.error(e); process.exit(1); });
