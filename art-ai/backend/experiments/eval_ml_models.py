"""Honest evaluation of the shipped ML models.

The shipped pickles record NO accuracy -- the models were trained but never evaluated.
This measures them properly, which is what a reviewer will ask for:

  1. A majority-class baseline (the number any model must beat). The corpus is heavily
     imbalanced, so raw accuracy alone is misleading and macro-F1 is reported too.
  2. The SHIPPED model scored on the full corpus. Flagged as optimistic: the shipped
     model was almost certainly fitted on this same data, so this is a train-set score,
     not a generalisation estimate.
  3. A FRESH model retrained on a stratified 80/20 split and scored on the held-out 20%.
     This is the honest generalisation number.

    python -m experiments.eval_ml_models
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (accuracy_score, classification_report,  # noqa: E402
                             confusion_matrix, f1_score)
from sklearn.model_selection import train_test_split  # noqa: E402

from exploit_ml_models import ExploitabilityClassifier  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_cache" / "processed_exploits.csv"
OUT = HERE / "results" / "ml_eval.json"


def main():
    df = pd.read_csv(DATA)
    df = df.dropna(subset=["exploit_type"])
    y_all = df["exploit_type"].astype(str)
    report = {"n_records": int(len(df)),
              "class_counts": {k: int(v) for k, v in y_all.value_counts().items()}}

    # --- 1. majority baseline -------------------------------------------------
    majority = y_all.value_counts().idxmax()
    base_acc = float((y_all == majority).mean())
    base_f1 = float(f1_score(y_all, [majority] * len(y_all), average="macro"))
    report["baseline"] = {"strategy": f"always predict '{majority}'",
                          "accuracy": base_acc, "macro_f1": base_f1}
    print(f"records: {len(df)}   classes: {report['class_counts']}")
    print(f"\n[1] Majority baseline ('{majority}'): acc={base_acc:.4f}  macro-F1={base_f1:.4f}")

    # --- 2. shipped model on the full corpus (optimistic) ---------------------
    try:
        clf = ExploitabilityClassifier()
        clf.load_model()
        X = clf.prepare_features(df, fit=False)
        y_enc = clf.label_encoder.transform(y_all)
        pred = clf.model.predict(X)
        acc = float(accuracy_score(y_enc, pred))
        mf1 = float(f1_score(y_enc, pred, average="macro"))
        report["shipped_model_full_corpus"] = {
            "accuracy": acc, "macro_f1": mf1,
            "caveat": "optimistic: shipped model was likely fitted on this same data"}
        print(f"\n[2] SHIPPED model on FULL corpus: acc={acc:.4f}  macro-F1={mf1:.4f}")
        print("    (optimistic -- this is effectively a train-set score)")
    except Exception as e:
        report["shipped_model_full_corpus"] = {"error": repr(e)}
        print(f"\n[2] shipped model could not be scored: {e!r}")

    # --- 3. fresh model, held-out split (the honest number) -------------------
    tr, te = train_test_split(df, test_size=0.2, random_state=42, stratify=y_all)
    # The platform column is a free-text category; values present only in the test split
    # would crash the encoder. Map unseen platforms to the train-set mode. This touches
    # only the categorical vocabulary, never the target, so it is not label leakage.
    tr = tr.copy(); te = te.copy()
    seen = set(tr["platform"].astype(str))
    mode_platform = tr["platform"].astype(str).mode()[0]
    te["platform"] = te["platform"].astype(str).where(
        te["platform"].astype(str).isin(seen), mode_platform)
    fresh = ExploitabilityClassifier()
    Xtr = fresh.prepare_features(tr, fit=True)
    ytr = fresh.label_encoder.fit_transform(tr["exploit_type"].astype(str))
    from sklearn.ensemble import GradientBoostingClassifier
    fresh.model = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
    fresh.model.fit(Xtr, ytr)

    Xte = fresh.prepare_features(te, fit=False)
    yte = fresh.label_encoder.transform(te["exploit_type"].astype(str))
    pte = fresh.model.predict(Xte)
    acc_h = float(accuracy_score(yte, pte))
    f1_h = float(f1_score(yte, pte, average="macro"))
    names = list(fresh.label_encoder.classes_)
    report["heldout"] = {
        "n_train": int(len(tr)), "n_test": int(len(te)),
        "accuracy": acc_h, "macro_f1": f1_h,
        "lift_over_baseline_acc": acc_h - base_acc,
        "per_class": classification_report(yte, pte, target_names=names,
                                           output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(yte, pte).tolist(),
        "labels": names,
    }
    print(f"\n[3] FRESH model, held-out 20% (n={len(te)}): acc={acc_h:.4f}  macro-F1={f1_h:.4f}")
    print(f"    lift over majority baseline: {acc_h - base_acc:+.4f} accuracy")
    print("\n" + classification_report(yte, pte, target_names=names, zero_division=0))
    print("confusion matrix (rows=true, cols=pred):", names)
    for row in confusion_matrix(yte, pte):
        print("   ", row.tolist())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"\n[*] wrote {OUT}")


if __name__ == "__main__":
    main()
