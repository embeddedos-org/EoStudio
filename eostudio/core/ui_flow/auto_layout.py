"""Auto-layout engine — flexbox/grid-like layout system for UI components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LayoutDirection(Enum):
    ROW = "row"
    COLUMN = "column"
    ROW_REVERSE = "row-reverse"
    COLUMN_REVERSE = "column-reverse"


class LayoutAlignment(Enum):
    START = "flex-start"
    CENTER = "center"
    END = "flex-end"
    STRETCH = "stretch"
    BASELINE = "baseline"


class LayoutDistribution(Enum):
    START = "flex-start"
    CENTER = "center"
    END = "flex-end"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"


class LayoutWrap(Enum):
    NOWRAP = "nowrap"
    WRAP = "wrap"
    WRAP_REVERSE = "wrap-reverse"


@dataclass
class LayoutConstraints:
    """Constraints applied to a child within an auto-layout."""
    fill_width: bool = False
    fill_height: bool = False
    fixed_width: Optional[float] = None
    fixed_height: Optional[float] = None
    min_width: Optional[float] = None
    min_height: Optional[float] = None
    max_width: Optional[float] = None
    max_height: Optional[float] = None
    flex_grow: float = 0
    flex_shrink: float = 1
    align_self: Optional[LayoutAlignment] = None

    def to_css(self) -> Dict[str, str]:
        styles: Dict[str, str] = {}
        if self.fill_width:
            styles["width"] = "100%"
        elif self.fixed_width is not None:
            styles["width"] = f"{self.fixed_width}px"
        if self.fill_height:
            styles["height"] = "100%"
        elif self.fixed_height is not None:
            styles["height"] = f"{self.fixed_height}px"
        if self.min_width is not None:
            styles["min-width"] = f"{self.min_width}px"
        if self.min_height is not None:
            styles["min-height"] = f"{self.min_height}px"
        if self.max_width is not None:
            styles["max-width"] = f"{self.max_width}px"
        if self.max_height is not None:
            styles["max-height"] = f"{self.max_height}px"
        if self.flex_grow:
            styles["flex-grow"] = str(self.flex_grow)
        if self.flex_shrink != 1:
            styles["flex-shrink"] = str(self.flex_shrink)
        if self.align_self:
            styles["align-self"] = self.align_self.value
        return styles


@dataclass
class AutoLayout:
    """Flexbox-like auto-layout system for EoStudio components."""
    direction: LayoutDirection = LayoutDirection.COLUMN
    alignment: LayoutAlignment = LayoutAlignment.START
    distribution: LayoutDistribution = LayoutDistribution.START
    wrap: LayoutWrap = LayoutWrap.NOWRAP
    gap: float = 8.0
    padding_top: float = 0.0
    padding_right: float = 0.0
    padding_bottom: float = 0.0
    padding_left: float = 0.0
    children_constraints: List[LayoutConstraints] = field(default_factory=list)

    @property
    def padding(self) -> Tuple[float, float, float, float]:
        return (self.padding_top, self.padding_right, self.padding_bottom, self.padding_left)

    @padding.setter
    def padding(self, value: float | Tuple[float, ...]) -> None:
        if isinstance(value, (int, float)):
            self.padding_top = self.padding_right = self.padding_bottom = self.padding_left = value
        elif len(value) == 2:
            self.padding_top = self.padding_bottom = value[0]
            self.padding_left = self.padding_right = value[1]
        elif len(value) == 4:
            self.padding_top, self.padding_right, self.padding_bottom, self.padding_left = value

    def compute_layout(self, container_width: float, container_height: float,
                       child_sizes: List[Tuple[float, float]]) -> List[Tuple[float, float, float, float]]:
        """Compute child positions and sizes. Returns list of (x, y, width, height)."""
        results: List[Tuple[float, float, float, float]] = []
        if not child_sizes:
            return results

        avail_w = container_width - self.padding_left - self.padding_right
        avail_h = container_height - self.padding_top - self.padding_bottom
        is_horizontal = self.direction in (LayoutDirection.ROW, LayoutDirection.ROW_REVERSE)
        is_reverse = self.direction in (LayoutDirection.ROW_REVERSE, LayoutDirection.COLUMN_REVERSE)

        # Total content size
        main_sizes = [s[0] if is_horizontal else s[1] for s in child_sizes]
        cross_sizes = [s[1] if is_horizontal else s[0] for s in child_sizes]
        total_main = sum(main_sizes) + self.gap * max(0, len(child_sizes) - 1)
        main_avail = avail_w if is_horizontal else avail_h
        cross_avail = avail_h if is_horizontal else avail_w

        # Distribute along main axis
        positions = self._distribute(main_sizes, main_avail, self.gap, self.distribution)

        if is_reverse:
            positions = [main_avail - p - s for p, s in zip(positions, main_sizes)]
            positions.reverse()
            main_sizes = list(reversed(main_sizes))
            cross_sizes = list(reversed(cross_sizes))

        for i, (pos, m_size, c_size) in enumerate(zip(positions, main_sizes, cross_sizes)):
            constraint = self.children_constraints[i] if i < len(self.children_constraints) else LayoutConstraints()

            # Apply constraints
            w = m_size if is_horizontal else c_size
            h = c_size if is_horizontal else m_size
            if constraint.fill_width:
                w = avail_w if not is_horizontal else m_size
            if constraint.fill_height:
                h = avail_h if is_horizontal else m_size
            if constraint.fixed_width is not None:
                w = constraint.fixed_width
            if constraint.fixed_height is not None:
                h = constraint.fixed_height

            # Cross-axis alignment
            align = constraint.align_self or self.alignment
            cross_pos = self._align_cross(c_size, cross_avail, align)

            if is_horizontal:
                x = self.padding_left + pos
                y = self.padding_top + cross_pos
            else:
                x = self.padding_left + cross_pos
                y = self.padding_top + pos

            results.append((x, y, w, h))

        return results

    def _distribute(self, sizes: List[float], available: float, gap: float,
                    distribution: LayoutDistribution) -> List[float]:
        n = len(sizes)
        total = sum(sizes) + gap * max(0, n - 1)
        remaining = available - total

        if distribution == LayoutDistribution.START:
            pos, positions = 0.0, []
            for s in sizes:
                positions.append(pos)
                pos += s + gap
            return positions

        if distribution == LayoutDistribution.END:
            pos = remaining
            positions = []
            for s in sizes:
                positions.append(pos)
                pos += s + gap
            return positions

        if distribution == LayoutDistribution.CENTER:
            pos = remaining / 2
            positions = []
            for s in sizes:
                positions.append(pos)
                pos += s + gap
            return positions

        if distribution == LayoutDistribution.SPACE_BETWEEN:
            if n <= 1:
                return [0.0]
            space = (available - sum(sizes)) / (n - 1)
            pos, positions = 0.0, []
            for s in sizes:
                positions.append(pos)
                pos += s + space
            return positions

        if distribution == LayoutDistribution.SPACE_AROUND:
            space = (available - sum(sizes)) / n
            pos, positions = space / 2, []
            for s in sizes:
                positions.append(pos)
                pos += s + space
            return positions

        if distribution == LayoutDistribution.SPACE_EVENLY:
            space = (available - sum(sizes)) / (n + 1)
            pos, positions = space, []
            for s in sizes:
                positions.append(pos)
                pos += s + space
            return positions

        return [0.0] * n

    def _align_cross(self, size: float, available: float,
                     alignment: LayoutAlignment) -> float:
        if alignment == LayoutAlignment.START:
            return 0.0
        if alignment == LayoutAlignment.CENTER:
            return (available - size) / 2
        if alignment == LayoutAlignment.END:
            return available - size
        return 0.0  # STRETCH / BASELINE default

    def to_css(self) -> Dict[str, str]:
        return {
            "display": "flex",
            "flex-direction": self.direction.value,
            "align-items": self.alignment.value,
            "justify-content": self.distribution.value,
            "flex-wrap": self.wrap.value,
            "gap": f"{self.gap}px",
            "padding": f"{self.padding_top}px {self.padding_right}px {self.padding_bottom}px {self.padding_left}px",
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction.value,
            "alignment": self.alignment.value,
            "distribution": self.distribution.value,
            "wrap": self.wrap.value,
            "gap": self.gap,
            "padding": list(self.padding),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutoLayout":
        layout = cls()
        if "direction" in data:
            layout.direction = LayoutDirection(data["direction"])
        if "alignment" in data:
            layout.alignment = LayoutAlignment(data["alignment"])
        if "distribution" in data:
            layout.distribution = LayoutDistribution(data["distribution"])
        if "wrap" in data:
            layout.wrap = LayoutWrap(data["wrap"])
        if "gap" in data:
            layout.gap = data["gap"]
        if "padding" in data:
            p = data["padding"]
            if isinstance(p, list) and len(p) == 4:
                layout.padding_top, layout.padding_right, layout.padding_bottom, layout.padding_left = p
            elif isinstance(p, (int, float)):
                layout.padding = p
        return layout
