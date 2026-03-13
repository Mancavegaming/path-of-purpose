"""
Attack / cast speed calculation.
"""

from __future__ import annotations


def calc_hits_per_second(
    base_speed: float,
    increased_speed: float,
    more_speed: list[float],
    less_speed: list[float] | None = None,
) -> float:
    """Calculate hits per second.

    Args:
        base_speed: Base attacks/casts per second from weapon or gem.
        increased_speed: Total increased attack/cast speed in %.
        more_speed: List of more attack/cast speed values in %.
        less_speed: List of less attack/cast speed values in %.

    Returns:
        Hits per second (floored at 0.01).
    """
    speed = base_speed * (1.0 + increased_speed / 100.0)

    for ms in more_speed:
        speed *= 1.0 + ms / 100.0

    if less_speed:
        for ls in less_speed:
            speed *= 1.0 - ls / 100.0

    return max(speed, 0.01)
