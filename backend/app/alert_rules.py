"""Đánh giá ngưỡng thuần túy; bên gọi phải xác minh phạm vi và độ phủ.

Chưa lưu hoặc phát cảnh báo. Không dùng kết quả khi chưa kiểm tra dữ liệu,
phân loại và tính duy nhất của nội dung theo SRS.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class AlertDecision:
    status: Literal["triggered", "not_triggered", "insufficient_data"]
    reason: str


def evaluate_increase(
    previous: int | None,
    current: int | None,
    *,
    growth_percent: Decimal,
    minimum_current: int,
    absolute_threshold: int | None = None,
    comparable: bool = False,
    fully_classified: bool = False,
) -> AlertDecision:
    """Chỉ so sánh khi bên gọi xác nhận đủ độ phủ và phân loại."""
    if (not isinstance(growth_percent, Decimal) or not growth_percent.is_finite() or growth_percent < 0
            or isinstance(minimum_current, bool) or not isinstance(minimum_current, int) or minimum_current < 0):
        raise ValueError("Ngưỡng không hợp lệ")
    if absolute_threshold is not None and (isinstance(absolute_threshold, bool)
                                           or not isinstance(absolute_threshold, int) or absolute_threshold < 1):
        raise ValueError("Ngưỡng tuyệt đối phải dương")
    if any(value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0)
           for value in (previous, current)):
        raise ValueError("Số lượng không hợp lệ")
    if not comparable or not fully_classified or previous is None or current is None:
        return AlertDecision("insufficient_data", "coverage_or_classification")
    if previous == 0:
        if absolute_threshold is None:
            return AlertDecision("insufficient_data", "zero_baseline")
        triggered = current >= max(absolute_threshold, minimum_current)
        return AlertDecision("triggered" if triggered else "not_triggered", "absolute_threshold")
    triggered = current >= minimum_current and Decimal(current - previous) * 100 >= growth_percent * previous
    return AlertDecision("triggered" if triggered else "not_triggered", "growth_threshold")
