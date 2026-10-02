"""
Trains the risk model on the augmented corpus feature matrix:
  - RandomForestClassifier -> risk bucket (low/medium/high)
  - RandomForestRegressor  -> continuous risk score (0-100)

Reports cross-validated performance BEFORE augmentation (on real data
only) so the numbers aren't inflated by synthetic points leaking across
folds, then fits the final deployed models on the augmented data for
better decision-boundary coverage at inference time.

With only 33 real documents, treat all metrics here as directional, not
production-grade validation — this is stated explicitly in the output.
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, mean_absolute_error, r2_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, KFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from risk_model.augmentation import augment_classification, augment_regression
from risk_model.feature_builder import FEATURE_NAMES

CORPUS_CSV = Path(__file__).resolve().parent / "corpus_features.csv"
MODEL_DIR = Path(__file__).resolve().parent / "trained"
MODEL_DIR.mkdir(exist_ok=True)

BUCKET_ORDER = ["low", "medium", "high"]
BUCKET_TO_IDX = {b: i for i, b in enumerate(BUCKET_ORDER)}


def load_corpus():
    df = pd.read_csv(CORPUS_CSV)
    X = df[FEATURE_NAMES].values.astype(float)
    y_bucket = df["risk_bucket"].map(BUCKET_TO_IDX).values
    y_score = df["risk_score"].values.astype(float)
    return df, X, y_bucket, y_score


def train():
    df, X, y_bucket, y_score = load_corpus()
    n = len(df)
    print(f"Loaded {n} real documents, {X.shape[1]} features.")
    print(f"Class distribution: {dict(zip(*np.unique(y_bucket, return_counts=True)))} "
          f"(0=low, 1=medium, 2=high)\n")

    # --- Cross-validated evaluation on REAL data only (no synthetic leakage) ---
    min_class_count = np.bincount(y_bucket).min()
    n_splits = max(2, min(3, min_class_count))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    clf_probe = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
    y_pred_cv = cross_val_predict(clf_probe, X, y_bucket, cv=skf)
    print(f"--- Classifier {n_splits}-fold CV on real data (n={n}, small-sample caveat applies) ---")
    print(classification_report(y_bucket, y_pred_cv, target_names=BUCKET_ORDER, zero_division=0))

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    reg_probe = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42)
    y_pred_reg_cv = cross_val_predict(reg_probe, X, y_score, cv=kf)
    mae = mean_absolute_error(y_score, y_pred_reg_cv)
    r2 = r2_score(y_score, y_pred_reg_cv)
    print(f"--- Regressor {n_splits}-fold CV on real data ---")
    print(f"MAE={mae:.2f}  R2={r2:.3f}\n")

    # --- Final models: fit on augmented data for smoother decision boundaries ---
    X_aug_clf, y_aug_clf = augment_classification(X, y_bucket)
    print(f"Classification training set after SMOTE: {len(y_bucket)} real -> {len(y_aug_clf)} rows")

    n_synth_reg = max(30, n * 3)
    X_aug_reg, y_aug_reg = augment_regression(X, y_score, n_synthetic=n_synth_reg)
    print(f"Regression training set after SMOTER-style augmentation: {len(y_score)} real -> {len(y_aug_reg)} rows\n")

    final_clf = RandomForestClassifier(n_estimators=300, max_depth=8, random_state=42, class_weight="balanced")
    final_clf.fit(X_aug_clf, y_aug_clf)

    final_reg = RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42)
    final_reg.fit(X_aug_reg, y_aug_reg)

    joblib.dump(final_clf, MODEL_DIR / "risk_classifier.joblib")
    joblib.dump(final_reg, MODEL_DIR / "risk_regressor.joblib")
    joblib.dump(FEATURE_NAMES, MODEL_DIR / "feature_names.joblib")

    print("--- Feature importances (final regressor, gain-based) ---")
    importances = sorted(zip(FEATURE_NAMES, final_reg.feature_importances_), key=lambda t: -t[1])
    for name, imp in importances[:10]:
        print(f"  {name:30s} {imp:.3f}")

    print(f"\nModels saved to {MODEL_DIR}")
    return final_clf, final_reg


if __name__ == "__main__":
    train()
