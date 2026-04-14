"""Simulation engine — signal blocks and model runner."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Signal:
    name: str
    times: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)

    def num_samples(self) -> int:
        return len(self.values)

    def add_sample(self, time: float, value: float) -> None:
        self.times.append(time)
        self.values.append(value)

    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    def rms(self) -> float:
        if not self.values:
            return 0.0
        return math.sqrt(sum(v * v for v in self.values) / len(self.values))


class Block:
    def __init__(self, block_id: str = "", name: str = "") -> None:
        self.block_id = block_id
        self.name = name

    def compute(self, dt: float, t: float, inputs: List[float]) -> float:
        return 0.0


class SourceBlock(Block):
    def __init__(self, block_id: str = "", name: str = "",
                 signal_type: str = "step", amplitude: float = 1.0,
                 frequency: float = 1.0) -> None:
        super().__init__(block_id, name)
        self.signal_type = signal_type
        self.amplitude = amplitude
        self.frequency = frequency

    def compute(self, dt: float, t: float, inputs: List[float]) -> float:
        if self.signal_type == "step":
            return self.amplitude if t >= 1.0 else 0.0
        if self.signal_type == "sine":
            return self.amplitude * math.sin(2.0 * math.pi * self.frequency * t)
        if self.signal_type == "constant":
            return self.amplitude
        return 0.0


class GainBlock(Block):
    def __init__(self, block_id: str = "", name: str = "", gain: float = 1.0) -> None:
        super().__init__(block_id, name)
        self.gain = gain

    def compute(self, dt: float, t: float, inputs: List[float]) -> float:
        return self.gain * (inputs[0] if inputs else 0.0)


class SumBlock(Block):
    def __init__(self, block_id: str = "", name: str = "",
                 signs: Optional[List[str]] = None) -> None:
        super().__init__(block_id, name)
        self.signs = signs or ["+", "+"]

    def compute(self, dt: float, t: float, inputs: List[float]) -> float:
        total = 0.0
        for i, val in enumerate(inputs):
            sign = self.signs[i] if i < len(self.signs) else "+"
            total += val if sign == "+" else -val
        return total


class PIDBlock(Block):
    def __init__(self, block_id: str = "", name: str = "",
                 Kp: float = 1.0, Ki: float = 0.0, Kd: float = 0.0) -> None:
        super().__init__(block_id, name)
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, dt: float, t: float, inputs: List[float]) -> float:
        error = inputs[0] if inputs else 0.0
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error
        return self.Kp * error + self.Ki * self._integral + self.Kd * derivative

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0


class ScopeBlock(Block):
    def __init__(self, block_id: str = "", name: str = "") -> None:
        super().__init__(block_id, name)
        self.signal = Signal(name=name)

    def compute(self, dt: float, t: float, inputs: List[float]) -> float:
        val = inputs[0] if inputs else 0.0
        self.signal.add_sample(t, val)
        return val


class SimulationModel:
    def __init__(self, dt: float = 0.01, duration: float = 10.0) -> None:
        self.dt = dt
        self.duration = duration
        self._blocks: Dict[str, Block] = {}
        self._connections: List[tuple] = []

    def add_block(self, block: Block) -> None:
        self._blocks[block.block_id] = block

    def connect(self, source_id: str, target_id: str) -> None:
        self._connections.append((source_id, target_id))

    def _topo_sort(self) -> List[str]:
        in_edges: Dict[str, List[str]] = {bid: [] for bid in self._blocks}
        for src, tgt in self._connections:
            if tgt in in_edges:
                in_edges[tgt].append(src)
        visited: set = set()
        order: List[str] = []

        def visit(bid: str) -> None:
            if bid in visited:
                return
            visited.add(bid)
            for dep in in_edges.get(bid, []):
                visit(dep)
            order.append(bid)

        for bid in self._blocks:
            visit(bid)
        return order

    def run(self) -> Dict[str, Signal]:
        order = self._topo_sort()
        in_map: Dict[str, List[str]] = {bid: [] for bid in self._blocks}
        for src, tgt in self._connections:
            in_map[tgt].append(src)

        outputs: Dict[str, float] = {bid: 0.0 for bid in self._blocks}
        steps = int(self.duration / self.dt)
        for step in range(steps):
            t = step * self.dt
            for bid in order:
                block = self._blocks[bid]
                inputs = [outputs[s] for s in in_map[bid]]
                outputs[bid] = block.compute(self.dt, t, inputs)

        results: Dict[str, Signal] = {}
        for bid, block in self._blocks.items():
            if isinstance(block, ScopeBlock):
                results[block.name] = block.signal
        return results

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SimulationModel:
        model = cls(dt=data.get("dt", 0.01), duration=data.get("duration", 10.0))
        return model
