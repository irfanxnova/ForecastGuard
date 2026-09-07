"""Verification metrics and calibration evaluation for ForecastGuard bust models.

Metrics implemented:
- Brier score
- Brier skill score (vs climatology reference)
- PR-AUC (Precision-Recall Area Under Curve)
- ROC-AUC (safe with single-class edge cases)
- Expected Calibration Error (ECE)
- Reliability diagram points (calibration curve)
- Confusion matrix, precision, recall, and false alarm rate at threshold
- Recall at specified operational alert rates (top 5%, 10%, 20% alert rate)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


@dataclass(frozen=True)
class EvaluationMetrics:
    """Comprehensive evaluation record for a probabilistic bust model."""

    sample_count: int
    positive_count: int
    negative_count: int
    base_rate: float
    brier_score: float
    brier_skill_score: Optional[float]
    roc_auc: Optional[float]
    pr_auc: Optional[float]
    expected_calibration_error: float
    reliability_curve: Dict[str, List[float]]
    confusion_matrix: Dict[str, int]
    precision: Optional[float]
    recall: Optional[float]
    false_alarm_rate: Optional[float]
    recall_at_alert_rates: Dict[str, float]
    decision_threshold: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to serializable dictionary."""
        return asdict(self)


def compute_expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 5,
) -> Tuple[float, Dict[str, List[float]]]:
    """Calculate Expected Calibration Error (ECE) and reliability curve data.

    Bins predictions into n_bins uniform intervals in [0, 1].
    ECE is the weighted average absolute difference between predicted confidence
    and empirical accuracy across all non-empty bins.
    """
    if len(y_true) == 0:
        return 0.0, {"prob_pred": [], "prob_true": [], "bin_counts": []}

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    prob_pred_list: List[float] = []
    prob_true_list: List[float] = []
    bin_counts_list: List[float] = []

    ece = 0.0
    n_total = float(len(y_true))

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            in_bin = (y_prob >= low) & (y_prob <= high)
        else:
            in_bin = (y_prob >= low) & (y_prob < high)

        count = int(np.sum(in_bin))
        if count > 0:
            mean_pred = float(np.mean(y_prob[in_bin]))
            mean_true = float(np.mean(y_true[in_bin]))
            prob_pred_list.append(mean_pred)
            prob_true_list.append(mean_true)
            bin_counts_list.append(float(count))

            ece += (count / n_total) * abs(mean_true - mean_pred)

    curve = {
        "prob_pred": prob_pred_list,
        "prob_true": prob_true_list,
        "bin_counts": bin_counts_list,
    }
    return float(ece), curve


def compute_recall_at_alert_rates(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    alert_rates: Sequence[float] = (0.05, 0.10, 0.20),
) -> Dict[str, float]:
    """Calculate the fraction of true busts captured if top alpha% are alerted.

    Operational weather centers often have fixed capacity for special alerts.
    This metric answers: 'If the meteorologist alerts the top X% highest risk
    cases, what fraction of true busts are caught?'
    """
    total_busts = int(np.sum(y_true == 1))
    if total_busts == 0 or len(y_true) == 0:
        return {f"top_{int(rate*100)}%": 0.0 for rate in alert_rates}

    n_samples = len(y_true)
    sorted_indices = np.argsort(-y_prob)  # descending order
    results: Dict[str, float] = {}

    for rate in alert_rates:
        k = max(1, int(np.ceil(rate * n_samples)))
        top_k_indices = sorted_indices[:k]
        busts_in_top_k = int(np.sum(y_true[top_k_indices] == 1))
        recall = busts_in_top_k / float(total_busts)
        results[f"top_{int(rate*100)}%"] = float(recall)

    return results


def evaluate_probabilistic_bust_forecast(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    *,
    climatology_prob: Optional[float] = None,
    decision_threshold: float = 0.5,
    n_bins: int = 5,
) -> EvaluationMetrics:
    """Evaluate a probabilistic forecast against true binary bust outcomes.

    Handles edge cases (all 0s or all 1s, small sample sizes) gracefully.
    """
    y_t = np.asarray(y_true, dtype=np.int32)
    y_p = np.asarray(y_prob, dtype=np.float64)

    if len(y_t) != len(y_p):
        raise ValueError(
            f"y_true ({len(y_t)}) and y_prob ({len(y_p)}) must have identical lengths."
        )
    if len(y_t) == 0:
        raise ValueError("Cannot evaluate predictions on an empty dataset.")

    n_samples = len(y_t)
    pos_count = int(np.sum(y_t == 1))
    neg_count = int(np.sum(y_t == 0))
    base_rate = float(pos_count / n_samples)

    # Brier score
    brier = float(brier_score_loss(y_t, y_p))

    # Brier skill score relative to climatology reference
    if climatology_prob is not None and 0.0 <= climatology_prob <= 1.0:
        ref_brier = float(np.mean((y_t - climatology_prob) ** 2))
        bss: Optional[float] = (
            float(1.0 - (brier / ref_brier)) if ref_brier > 1e-12 else 0.0
        )
    else:
        # Default reference is empirical sample base rate
        ref_brier = float(np.mean((y_t - base_rate) ** 2))
        bss = float(1.0 - (brier / ref_brier)) if ref_brier > 1e-12 else None

    # ROC-AUC and PR-AUC (require at least one positive and one negative sample)
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    if pos_count > 0 and neg_count > 0:
        try:
            roc_auc = float(roc_auc_score(y_t, y_p))
        except ValueError:
            roc_auc = None

        try:
            pr_auc = float(average_precision_score(y_t, y_p))
        except ValueError:
            pr_auc = None

    # Expected calibration error and reliability curve
    ece, rel_curve = compute_expected_calibration_error(y_t, y_p, n_bins=n_bins)

    # Confusion matrix and threshold metrics
    y_pred_hard = (y_p >= decision_threshold).astype(np.int32)
    tp = int(np.sum((y_pred_hard == 1) & (y_t == 1)))
    fp = int(np.sum((y_pred_hard == 1) & (y_t == 0)))
    fn = int(np.sum((y_pred_hard == 0) & (y_t == 1)))
    tn = int(np.sum((y_pred_hard == 0) & (y_t == 0)))

    confusion = {"tp": tp, "fp": fp, "fn": fn, "tn": tn}
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    far = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    # Recall at alert rates
    recall_at_alert = compute_recall_at_alert_rates(y_t, y_p)

    return EvaluationMetrics(
        sample_count=n_samples,
        positive_count=pos_count,
        negative_count=neg_count,
        base_rate=base_rate,
        brier_score=brier,
        brier_skill_score=bss,
        roc_auc=roc_auc,
        pr_auc=pr_auc,
        expected_calibration_error=ece,
        reliability_curve=rel_curve,
        confusion_matrix=confusion,
        precision=precision,
        recall=recall,
        false_alarm_rate=far,
        recall_at_alert_rates=recall_at_alert,
        decision_threshold=decision_threshold,
    )
