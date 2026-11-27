"""Đánh giá ngưỡng thuần túy; bên gọi phải xác minh phạm vi và độ phủ.

Chưa lưu hoặc phát cảnh báo. Không dùng kết quả khi chưa kiểm tra dữ liệu,
phân loại và tính duy nhất của nội dung theo SRS.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class AlertDecision:
    status: Literal["triggered", "not_triggered", "insufficient_data"]
    reason: str


@dataclass(frozen=True)
class WindowEvidence:
    """Bằng chứng do bên gọi thu thập cho một cửa sổ [start, end)."""
    start: datetime
    end: datetime
    scope: tuple[str, ...]
    expected_runs: int
    successful_runs: int
    content_count: int
    classified_count: int
    missing_source_ids: int


def comparable_windows(previous: WindowEvidence, current: WindowEvidence) -> bool:
    """Không kết luận đủ dữ liệu nếu bất kỳ bằng chứng cần thiết nào bị thiếu.

    Bên gọi phải xác minh lịch, phạm vi, ID và phân loại từ nguồn dữ liệu tin cậy;
    hàm này không tự chứng minh việc thu thập thực tế có độ bao phủ đầy đủ.
    """
    windows = (previous, current)
    for window in windows:
        if (window.start.tzinfo is None or window.start.utcoffset() is None or
                window.end.tzinfo is None or window.end.utcoffset() is None or
                window.start.astimezone(timezone.utc) >= window.end.astimezone(timezone.utc) or not window.scope or
                any(not isinstance(value, str) or not value for value in window.scope) or
                len(set(window.scope)) != len(window.scope)):
            return False
        counts = (window.expected_runs, window.successful_runs, window.content_count,
                  window.classified_count, window.missing_source_ids)
        if any(type(value) is not int or value < 0 for value in counts):
            return False
        if (window.expected_runs == 0 or window.successful_runs != window.expected_runs or
                window.classified_count != window.content_count or window.missing_source_ids != 0):
            return False
    previous_start, previous_end = previous.start.astimezone(timezone.utc), previous.end.astimezone(timezone.utc)
    current_start, current_end = current.start.astimezone(timezone.utc), current.end.astimezone(timezone.utc)
    return (previous_end == current_start and previous_end - previous_start == current_end - current_start
            and set(previous.scope) == set(current.scope))


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
