"""
Tabular augmentation for the tiny (33-document) real feature corpus.

- Classification target (risk_bucket): classic SMOTE via imbalanced-learn,
  generating synthetic feature vectors along the line between real
  minority-class neighbors in feature space.
- Regression target (risk_score, continuous): imbalanced-learn's SMOTE
  doesn't apply to continuous targets, so this implements a small
  SMOTER-style augmentor (Torgo et al.'s "SMOTE for Regression" idea,
  simplified): pick a real sample, find its nearest real neighbors in
  feature space, interpolate a synthetic point between them and linearly
  interpolate the target score to match, with a touch of Gaussian noise
  so synthetic points aren't exactly on the line segment.

Both operate purely on the numeric feature matrix built from real
documents — no synthetic text, no fabricated documents.
"""

from __future__ import annotations

import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import NearestNeighbors


def augment_classification(X: np.ndarray, y: np.ndarray, random_state: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """SMOTE-oversample the minority classes. k_neighbors is capped below
    the smallest class's sample count (SMOTE requires k_neighbors <
    n_samples in the smallest class it's oversampling)."""
    class_counts = np.bincount(y)
    min_class_count = class_counts[class_counts > 0].min()
    k_neighbors = max(1, min(5, min_class_count - 1))
    if min_class_count < 2:
        # Can't interpolate with fewer than 2 real neighbors — return as-is.
        return X, y
    smote = SMOTE(random_state=random_state, k_neighbors=k_neighbors)
    return smote.fit_resample(X, y)


def augment_regression(
    X: np.ndarray,
    y: np.ndarray,
    n_synthetic: int,
    k_neighbors: int = 4,
    noise_std: float = 0.02,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate n_synthetic additional (feature, score) rows by
    interpolating between real nearest-neighbor pairs in feature space."""
    rng = np.random.default_rng(random_state)
    n_samples = X.shape[0]
    k = min(k_neighbors, n_samples - 1)
    if k < 1:
        return X, y

    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    _, neighbor_idx = nn.kneighbors(X)

    synth_X = []
    synth_y = []
    for _ in range(n_synthetic):
        base_idx = rng.integers(0, n_samples)
        # neighbor_idx[base_idx][0] is the point itself; pick from the rest
        neighbor_choices = neighbor_idx[base_idx][1:]
        neighbor_idx_pick = rng.choice(neighbor_choices)

        lam = rng.uniform(0.15, 0.85)
        new_x = X[base_idx] * lam + X[neighbor_idx_pick] * (1 - lam)
        new_x = new_x + rng.normal(0, noise_std, size=new_x.shape) * (np.abs(new_x) + 1e-6)
        new_y = y[base_idx] * lam + y[neighbor_idx_pick] * (1 - lam)

        synth_X.append(new_x)
        synth_y.append(new_y)

    aug_X = np.vstack([X, np.array(synth_X)])
    aug_y = np.concatenate([y, np.array(synth_y)])
    return aug_X, aug_y
