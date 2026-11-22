"""Physics and trial model for the Atwood machine virtual laboratory.

All lengths are in metres, masses in kilograms, times in seconds, and
accelerations in m/s**2.  This module deliberately has no Qt dependency so
its calculation and randomisation rules can be tested on any Python install.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable

STANDARD_GRAVITY = 9.81


def atwood_acceleration(mass_each_kg: float, overload_kg: float,
                        gravity: float = STANDARD_GRAVITY) -> float:
    """Return the ideal Atwood acceleration a = g*m/(2M + m)."""
    if mass_each_kg <= 0:
        raise ValueError("Mass M must be positive")
    if overload_kg <= 0:
        raise ValueError("Overload mass m must be positive")
    if gravity <= 0:
        raise ValueError("Gravity must be positive")
    return gravity * overload_kg / (2.0 * mass_each_kg + overload_kg)


def fall_time(distance_m: float, acceleration: float) -> float:
    """Time from rest to travel distance H with constant acceleration."""
    if distance_m <= 0:
        raise ValueError("Distance H must be positive")
    if acceleration <= 0:
        raise ValueError("Acceleration must be positive")
    return (2.0 * distance_m / acceleration) ** 0.5


def estimate_gravity(distance_m: float, time_s: float,
                     mass_each_kg: float, overload_kg: float) -> float:
    """Calculate g from one run using the ideal Atwood model."""
    if time_s <= 0:
        raise ValueError("Time must be positive")
    if distance_m <= 0:
        raise ValueError("Distance H must be positive")
    if overload_kg <= 0 or mass_each_kg <= 0:
        raise ValueError("Masses must be positive")
    return (2.0 * distance_m / (time_s * time_s)
            * (2.0 * mass_each_kg + overload_kg) / overload_kg)


def fit_acceleration_from_heights(distances_m: Iterable[float],
                                  times_s: Iterable[float]) -> float:
    """Fit 2H = a*t^2 through the origin and return its slope a."""
    distances = list(distances_m)
    times = list(times_s)
    xs = [t * t for t in times]
    ys = [2.0 * h for h in distances]
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("At least two paired measurements are required")
    if any(h <= 0 for h in distances) or any(t <= 0 for t in times):
        raise ValueError("Distances and times must be positive")
    denominator = sum(x * x for x in xs)
    if denominator == 0:
        raise ValueError("Cannot fit a zero-time data set")
    return sum(x * y for x, y in zip(xs, ys)) / denominator


def student_random_gravity(rng: random.Random | None = None) -> float:
    """Pick a reproducible-to-test pseudo-random g, quantized to 0.001.

    The range is deliberately narrow (9.805..9.815 m/s²).  Passing a seeded
    ``random.Random`` instance makes automated tests deterministic.
    """
    source = rng if rng is not None else random.SystemRandom()
    milli_steps = source.randint(-5, 5)
    return round(STANDARD_GRAVITY + milli_steps / 1000.0, 3)


@dataclass(frozen=True)
class Trial:
    mass_each_kg: float
    overload_kg: float
    distance_m: float
    gravity_m_s2: float

    @property
    def acceleration_m_s2(self) -> float:
        return atwood_acceleration(self.mass_each_kg, self.overload_kg,
                                   self.gravity_m_s2)

    @property
    def ideal_time_s(self) -> float:
        return fall_time(self.distance_m, self.acceleration_m_s2)
