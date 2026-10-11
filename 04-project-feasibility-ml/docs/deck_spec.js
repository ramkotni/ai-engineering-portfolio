// Deck for Project Feasibility Prediction.  cd tools/deck && node build.js ../../04-project-feasibility-ml
const fs = require("fs");
const path = require("path");

const R = (f) => { try { return JSON.parse(fs.readFileSync(path.join(__dirname, "..", f), "utf8")); } catch { return null; } };

module.exports = {
  fileName: "Project_Feasibility_ML.pptx",
  build(Deck) {
    const d = new Deck({
      title: "Project Feasibility Prediction",
      subtitle: "scikit-learn pipeline, interpretable logistic regression, drift monitoring and a LangGraph advisor",
      footer: "Project Feasibility Prediction | portfolio prototype on synthetic data",
      accent: "7A5CC4",
    });
    const C = d.C, HEX = d.HEX;
    const card = R("models/model_card.json"), ev = R("eval/results/eval_report.json");

    d.cards("Context", "Why: consistent, explainable intake decisions", [
      ["Inconsistent reviews", "Similar projects get different verdicts depending on who reviews them."],
      ["Opaque reasoning", "Boards need to know which factors drive risk, not just a score."],
      ["Dirty data", "Missing fields, unit errors, invalid codes and duplicates in the intake history."],
      ["Goal", "Calibrated probability + drivers + mitigations, monitored for drift, behind an API."],
    ], { cols: 2 });

    d.pipeline("Pipeline", "End-to-end ML pipeline", [
      ["Validate", "duplicates, missing, ranges, categories"],
      ["Clean", "unit fix, normalise, null impossible"],
      ["Features", "budget/week, staffing pressure, ..."],
      ["Preprocess", "median impute, scale, one-hot"],
      ["Compare + tune", "5-fold CV, GridSearchCV"],
      ["Evaluate + card", "hold-out, calibration, model card"],
    ], {
      below: (s) => d.text(s, "One scikit-learn Pipeline object holds feature engineering, preprocessing and the model, so serving uses exactly the training code. The data-validation report found the planted problems: 12 duplicates, ~50 missing values per field, 7 budget unit errors, 6 invalid TRL codes, upper-case category drift.",
        { x: 0.6, y: 3.45, w: 12.1, h: 1.2, fontSize: 15 }),
    });

    if (card) {
      const comp = Object.entries(card.comparison).map(([k, v]) => [k.replace(/_/g, " "), v.cv_auc_mean]);
      d.custom("Model", "Model selection: interpretability within 0.02 AUC", (s) => {
        s.addChart(d.pres.charts.BAR, [{ name: "CV ROC-AUC", labels: comp.map((c) => c[0]), values: comp.map((c) => c[1]) }], {
          x: 0.6, y: 1.45, w: 7.2, h: 4.9, barDir: "bar", chartColors: [HEX.accent6], showValue: true, dataLabelFormatCode: "0.000",
          dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
          valAxisMinVal: 0.75, valAxisMaxVal: 0.86, valAxisLabelFontSize: 10, valAxisLabelColor: HEX.accent5, valAxisLabelFontFace: "+mn-lt",
          catAxisLabelFontSize: 11, catAxisLabelColor: HEX.dk1, catAxisLabelFontFace: "+mn-lt", showLegend: false,
          valGridLine: { color: "D9DEE4", size: 0.5 }, catGridLine: { style: "none" },
          showTitle: true, title: "5-fold cross-validated ROC-AUC", titleFontSize: 13, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
        });
        const m = card.test_metrics;
        [["ROC-AUC", m.roc_auc], ["PR-AUC", m.pr_auc], ["F1", m.f1], ["Brier", m.brier]].forEach(([k, v], i) => {
          d.text(s, String(v), { x: 8.3 + (i % 2) * 2.2, y: 1.6 + Math.floor(i / 2) * 1.5, w: 2.0, h: 0.8, fontSize: 36, bold: true, color: C.accent1 });
          d.text(s, `${k} (hold-out)`, { x: 8.3 + (i % 2) * 2.2, y: 2.4 + Math.floor(i / 2) * 1.5, w: 2.0, h: 0.4, fontSize: 13 });
        });
        d.text(s, `Chosen: ${card.model.replace(/_/g, " ")} - ${card.selection_reason}. Tuned over C and l1_ratio (L2 / elastic net / L1).`,
          { x: 8.3, y: 4.8, w: 4.4, h: 1.4, fontSize: 13 });
      });
      d.table("Model", "What drives feasibility (standardised coefficients)", [["Feature", "Coefficient", "Odds ratio per SD"],
        ...card.coefficients.slice(0, 8).map((c) => [c.feature.replace(/_/g, " "), c.coefficient, c.odds_ratio])],
      { colW: [5.5, 3.2, 3.4], caption: "readiness_gap (= 9 - TRL) was removed: perfectly collinear with TRL, it split one effect into two opposite coefficients." });
    }
    if (ev) {
      d.table("Model", "Decision threshold is a business choice", [["Threshold", "Precision", "Recall", "F1", "Share approved"],
        ...ev.threshold_sweep.map((t) => [t.threshold, t.precision, t.recall, t.f1, t.approved_share])],
      { colW: [2.4, 2.4, 2.4, 2.4, 2.5], fontSize: 12, caption: "Default 0.5; 0.45 maximises F1; 0.65 gives precision ~0.85 for a conservative board." });
    }
    d.custom("Serving", "Serving: explanation, OOD and drift", (s) => {
      [["Explanation", "contribution = coefficient x standardised value -> top positive / negative drivers in business language"],
        ["Input guardrails", "pydantic types, categories and ranges (422); out-of-distribution warnings vs training range"],
        ["Drift (PSI)", "rolling window vs training histogram in the model card: stable < 0.1 < moderate < 0.25 < significant"],
        ["Verified", "random training sample PSI ~0.02; complexity +3 -> 2.39 (significant)"]].forEach(([t, dsc], i) => {
        d.badge(s, 0.6, 1.55 + i * 1.2, 0.5, String(i + 1), C.accent1, 14);
        d.text(s, [{ text: t, options: { bold: true, fontSize: 16, breakLine: true } }, { text: dsc, options: { fontSize: 14 } }], { x: 1.3, y: 1.5 + i * 1.2, w: 11.4, h: 1.1 });
      });
    });
    d.pipeline("Advisor", "LangGraph advisor: LLM only where it adds value", [
      ["guard_notes", "prompt-injection check"], ["predict", "sklearn model as a tool"], ["retrieve_playbook", "BM25 by negative drivers"],
      ["advise", "LLM: why + 2-4 mitigations"], ["guard_output", "numeric grounding"],
    ], { below: (s) => d.text(s, "The probability comes from the model, never from the LLM. The playbook has 7 sections, so keyword retrieval is enough - no vector store. Without Ollama the advisor falls back to drivers + playbook text. RAGAS is not used here: there is no retrieval-augmented generation in the decision path.", { x: 0.6, y: 3.45, w: 12.1, h: 1.2, fontSize: 15 }) });
    d.table("Security", "Sample roles", [["Role", "Capabilities"], ["project_manager", "predict, advise"], ["portfolio_director", "predict, advise, batch"],
      ["data_scientist", "predict, batch, model card, drift, retrain"], ["stakeholder_viewer", "predict (score only, no drivers)"]], { colW: [3.6, 8.5] });
    d.custom("Run", "Run, test and monitor", (s) => d.code(s, 0.6, 1.45, 12.1, null, [
      "cd 04-project-feasibility-ml",
      "python -m feasibility.train                       # compare, tune, evaluate, save model + card",
      "python -m feasibility.cli score data/raw/new_projects.csv",
      "uvicorn feasibility.api:app --port 8004           # http://localhost:8004/docs",
      "streamlit run ui/streamlit_app.py --server.port 8504",
      "curl localhost:8004/drift -H \"X-API-Key: ds-demo-key\"",
      "curl localhost:8004/metrics",
      "pytest -q                                         # 11 tests",
      "python -m eval.run_eval                           # metrics + threshold sweep",
    ].join("\n"), 13));
    d.closing("Next steps", ["Calibrate with real intake outcomes; add isotonic calibration if needed", "Scheduled retraining with champion / challenger comparison",
      "Alert on PSI > 0.25 and on OOD rate", "Advisor feedback loop into the playbook"]);
    return d;
  },
};
