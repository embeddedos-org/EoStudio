"""Spring physics simulation for natural-feeling animations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple, Union

NumericValue = Union[float, Tuple[float, ...], List[float]]


@dataclass
class SpringConfig:
    """Configuration for spring physics animation.

    Presets mirror Framer Motion naming:
      - default: stiffness=100, damping=10, mass=1
      - gentle:  stiffness=120, damping=14, mass=1
      - wobbly:  stiffness=180, damping=12, mass=1
      - stiff:   stiffness=300, damping=20, mass=1
      - slow:    stiffness=50,  damping=15, mass=1
      - molasses: stiffness=30, damping=20, mass=1
    """
    stiffness: float = 100.0
    damping: float = 10.0
    mass: float = 1.0
    velocity: float = 0.0
    rest_threshold: float = 0.001
    rest_velocity_threshold: float = 0.001
    clamp: bool = False

    @classmethod
    def default(cls) -> "SpringConfig":
        return cls(stiffness=100, damping=10, mass=1)

    @classmethod
    def gentle(cls) -> "SpringConfig":
        return cls(stiffness=120, damping=14, mass=1)

    @classmethod
    def wobbly(cls) -> "SpringConfig":
        return cls(stiffness=180, damping=12, mass=1)

    @classmethod
    def stiff(cls) -> "SpringConfig":
        return cls(stiffness=300, damping=20, mass=1)

    @classmethod
    def slow(cls) -> "SpringConfig":
        return cls(stiffness=50, damping=15, mass=1)

    @classmethod
    def molasses(cls) -> "SpringConfig":
        return cls(stiffness=30, damping=20, mass=1)

    @property
    def damping_ratio(self) -> float:
        return self.damping / (2 * math.sqrt(self.stiffness * self.mass))

    @property
    def is_underdamped(self) -> bool:
        return self.damping_ratio < 1.0

    @property
    def natural_frequency(self) -> float:
        return math.sqrt(self.stiffness / self.mass)


class SpringSimulator:
    """Simulate spring motion from an initial value to a target value."""

    def __init__(self, from_value: float, to_value: float,
                 config: SpringConfig | None = None) -> None:
        self.config = config or SpringConfig.default()
        self.from_value = from_value
        self.to_value = to_value
        self._position = from_value
        self._velocity = self.config.velocity
        self._at_rest = False
        self._time = 0.0

    @property
    def position(self) -> float:
        return self._position

    @property
    def velocity(self) -> float:
        return self._velocity

    @property
    def at_rest(self) -> bool:
        return self._at_rest

    def step(self, dt: float) -> float:
        """Advance the spring simulation by dt seconds. Returns current position."""
        if self._at_rest:
            return self._position

        cfg = self.config
        displacement = self._position - self.to_value
        spring_force = -cfg.stiffness * displacement
        damping_force = -cfg.damping * self._velocity
        acceleration = (spring_force + damping_force) / cfg.mass

        self._velocity += acceleration * dt
        self._position += self._velocity * dt
        self._time += dt

        if cfg.clamp:
            if self.from_value < self.to_value:
                self._position = min(self._position, self.to_value)
            else:
                self._position = max(self._position, self.to_value)

        if (abs(self._position - self.to_value) < cfg.rest_threshold and
                abs(self._velocity) < cfg.rest_velocity_threshold):
            self._position = self.to_value
            self._velocity = 0.0
            self._at_rest = True

        return self._position

    def evaluate(self, time: float, steps_per_second: int = 120) -> float:
        """Evaluate spring position at a specific time from start."""
        sim = SpringSimulator(self.from_value, self.to_value, self.config)
        dt = 1.0 / steps_per_second
        t = 0.0
        while t < time:
            sim.step(dt)
            t += dt
            if sim.at_rest:
                break
        return sim.position

    def sample(self, duration: float, fps: int = 60) -> List[Tuple[float, float]]:
        """Sample spring values over a duration. Returns list of (time, value)."""
        samples = []
        sim = SpringSimulator(self.from_value, self.to_value, self.config)
        dt = 1.0 / fps
        t = 0.0
        while t <= duration:
            samples.append((t, sim.position))
            sim.step(dt)
            t += dt
            if sim.at_rest:
                samples.append((t, sim.position))
                break
        return samples

    def estimated_duration(self, steps_per_second: int = 120, max_time: float = 10.0) -> float:
        """Estimate how long the spring takes to settle."""
        sim = SpringSimulator(self.from_value, self.to_value, self.config)
        dt = 1.0 / steps_per_second
        t = 0.0
        while t < max_time:
            sim.step(dt)
            t += dt
            if sim.at_rest:
                return t
        return max_time


class MultiSpringSimulator:
    """Simulate spring motion for multi-dimensional values (x,y,z etc.)."""

    def __init__(self, from_value: NumericValue, to_value: NumericValue,
                 config: SpringConfig | None = None) -> None:
        self.config = config or SpringConfig.default()
        from_seq = [from_value] if isinstance(from_value, (int, float)) else list(from_value)
        to_seq = [to_value] if isinstance(to_value, (int, float)) else list(to_value)
        length = max(len(from_seq), len(to_seq))
        self._springs = []
        for i in range(length):
            fv = from_seq[i] if i < len(from_seq) else 0.0
            tv = to_seq[i] if i < len(to_seq) else 0.0
            self._springs.append(SpringSimulator(fv, tv, SpringConfig(
                stiffness=self.config.stiffness,
                damping=self.config.damping,
                mass=self.config.mass,
                velocity=self.config.velocity,
                rest_threshold=self.config.rest_threshold,
                rest_velocity_threshold=self.config.rest_velocity_threshold,
                clamp=self.config.clamp,
            )))

    def step(self, dt: float) -> NumericValue:
        values = [s.step(dt) for s in self._springs]
        return values[0] if len(values) == 1 else tuple(values)

    @property
    def at_rest(self) -> bool:
        return all(s.at_rest for s in self._springs)

    @property
    def position(self) -> NumericValue:
        values = [s.position for s in self._springs]
        return values[0] if len(values) == 1 else tuple(values)
