"""Small dependency-free classification metrics used by training and evaluation."""

from __future__ import annotations


def confusion_matrix_counts(
    labels: list[int],
    predictions: list[int],
    *,
    num_classes: int,
) -> list[list[int]]:
    """Return a row=true, col=predicted confusion matrix."""
    matrix = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    for label, prediction in zip(labels, predictions, strict=True):
        if 0 <= label < num_classes and 0 <= prediction < num_classes:
            matrix[label][prediction] += 1
    return matrix


def per_class_precision_recall_f1(
    matrix: list[list[int]],
) -> tuple[list[float], list[float], list[float]]:
    """Compute per-class precision, recall, and F1 from a confusion matrix."""
    num_classes = len(matrix)
    precision: list[float] = []
    recall: list[float] = []
    f1: list[float] = []

    for class_idx in range(num_classes):
        true_positive = matrix[class_idx][class_idx]
        false_positive = sum(matrix[row][class_idx] for row in range(num_classes)) - true_positive
        false_negative = sum(matrix[class_idx]) - true_positive

        class_precision = _safe_divide(true_positive, true_positive + false_positive)
        class_recall = _safe_divide(true_positive, true_positive + false_negative)
        class_f1 = _safe_divide(2 * class_precision * class_recall, class_precision + class_recall)

        precision.append(class_precision)
        recall.append(class_recall)
        f1.append(class_f1)

    return precision, recall, f1


def macro_scores(matrix: list[list[int]]) -> tuple[float, float, float]:
    """Return macro precision, macro recall, and macro F1."""
    precision, recall, f1 = per_class_precision_recall_f1(matrix)
    return _mean(precision), _mean(recall), _mean(f1)


def classification_report_text(
    matrix: list[list[int]],
    class_names: list[str],
) -> str:
    """Render a compact text report similar to sklearn's classification_report."""
    precision, recall, f1 = per_class_precision_recall_f1(matrix)
    rows = ["class              precision  recall  f1-score  support"]
    for index, class_name in enumerate(class_names):
        support = sum(matrix[index])
        rows.append(
            f"{class_name:<18}{precision[index]:>9.4f}"
            f"{recall[index]:>8.4f}{f1[index]:>10.4f}{support:>9}"
        )
    macro_precision, macro_recall, macro_f1 = macro_scores(matrix)
    total = sum(sum(row) for row in matrix)
    rows.append(
        f"{'macro avg':<18}{macro_precision:>9.4f}{macro_recall:>8.4f}{macro_f1:>10.4f}{total:>9}"
    )
    return "\n".join(rows)


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
