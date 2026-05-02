"""Performance profiling tools for Python and Node.js."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ProfileType(Enum):
    """Types of profiling."""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    BUNDLE = "bundle"


@dataclass
class ProfileSample:
    """A single profile sample entry."""
    function: str
    file: str
    line: int
    time_ms: float
    calls: int
    cumulative_ms: float


@dataclass
class ProfileResult:
    """Complete profiling result."""
    type: ProfileType
    samples: List[ProfileSample] = field(default_factory=list)
    total_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    timestamp: str = ""


@dataclass
class FlameGraphNode:
    """A node in a flame graph tree."""
    name: str
    value: float
    children: List[FlameGraphNode] = field(default_factory=list)


@dataclass
class FlameGraph:
    """A flame graph representation of profiling data."""
    root: FlameGraphNode = field(default_factory=lambda: FlameGraphNode("root", 0))
    total_samples: int = 0


class Profiler:
    """Profiler for Python and Node.js applications."""

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = os.path.abspath(workspace_path)
        self._history: List[ProfileResult] = []

    def profile_python(
        self, script: str, args: Optional[List[str]] = None
    ) -> ProfileResult:
        """Profile a Python script using cProfile via subprocess."""
        stats_file = os.path.join(
            tempfile.gettempdir(),
            f"eostudio_profile_{os.getpid()}.prof",
        )
        cmd = [
            "python", "-m", "cProfile",
            "-o", stats_file,
            script,
        ]
        if args:
            cmd.extend(args)

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.workspace_path,
        )

        result = self.parse_cprofile_output(stats_file)

        # Clean up temp file
        try:
            os.unlink(stats_file)
        except OSError:
            pass

        self._history.append(result)
        return result

    def profile_memory_python(self, script: str) -> ProfileResult:
        """Profile memory usage of a Python script using tracemalloc."""
        wrapper = (
            "import tracemalloc, runpy, json, sys;"
            "tracemalloc.start();"
            f"runpy.run_path({script!r});"
            "snapshot = tracemalloc.take_snapshot();"
            "stats = snapshot.statistics('lineno');"
            "entries = [];"
            "for s in stats[:50]:"
            "  entries.append({"
            "    'file': str(s.traceback[0].filename) if s.traceback else '',"
            "    'line': s.traceback[0].lineno if s.traceback else 0,"
            "    'size': s.size,"
            "    'count': s.count"
            "  });"
            "peak = tracemalloc.get_traced_memory()[1];"
            "print(json.dumps({'entries': entries, 'peak': peak}))"
        )
        cmd = ["python", "-c", wrapper]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.workspace_path,
        )

        result = ProfileResult(
            type=ProfileType.MEMORY,
            timestamp=datetime.now().isoformat(),
        )

        if proc.returncode == 0 and proc.stdout.strip():
            try:
                data = json.loads(proc.stdout.strip().splitlines()[-1])
                result.peak_memory_mb = data.get("peak", 0) / (1024 * 1024)
                for entry in data.get("entries", []):
                    result.samples.append(ProfileSample(
                        function="<memory>",
                        file=entry.get("file", ""),
                        line=entry.get("line", 0),
                        time_ms=0.0,
                        calls=entry.get("count", 0),
                        cumulative_ms=entry.get("size", 0) / 1024,  # KB
                    ))
            except (json.JSONDecodeError, IndexError):
                pass

        self._history.append(result)
        return result

    def profile_node(self, script: str) -> ProfileResult:
        """Profile a Node.js script using --prof flag."""
        cmd = ["node", "--prof", script]
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.workspace_path,
        )

        result = ProfileResult(
            type=ProfileType.CPU,
            timestamp=datetime.now().isoformat(),
        )

        log_files = [
            f for f in os.listdir(self.workspace_path)
            if f.startswith("isolate-") and f.endswith(".log")
        ]
        if not log_files:
            self._history.append(result)
            return result

        log_file = os.path.join(self.workspace_path, sorted(log_files)[-1])

        # Process the V8 log
        proc_cmd = ["node", "--prof-process", "--preprocess", log_file]
        proc = subprocess.run(
            proc_cmd,
            capture_output=True,
            text=True,
            cwd=self.workspace_path,
        )

        if proc.returncode == 0 and proc.stdout.strip():
            try:
                v8_data = json.loads(proc.stdout)
                ticks = v8_data.get("ticks", [])
                result.total_time_ms = len(ticks) * 1.0  # approximate
            except json.JSONDecodeError:
                pass

        # Clean up log file
        try:
            os.unlink(log_file)
        except OSError:
            pass

        self._history.append(result)
        return result

    def parse_cprofile_output(self, stats_file: str) -> ProfileResult:
        """Parse a cProfile binary stats file into a ProfileResult."""
        result = ProfileResult(
            type=ProfileType.CPU,
            timestamp=datetime.now().isoformat(),
        )

        # Use pstats via subprocess to dump stats as text
        dump_script = (
            "import pstats, sys;"
            f"s = pstats.Stats({stats_file!r});"
            "s.sort_stats('cumulative');"
            "s.print_stats(50)"
        )
        proc = subprocess.run(
            ["python", "-c", dump_script],
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            return result

        output = proc.stdout
        # Parse the pstats text output
        # Format: ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        in_stats = False
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if "ncalls" in line and "tottime" in line and "cumtime" in line:
                in_stats = True
                continue
            if not in_stats or not line:
                continue

            # Match stat lines
            match = re.match(
                r"(\d+(?:/\d+)?)\s+"      # ncalls
                r"([\d.]+)\s+"             # tottime
                r"([\d.]+)\s+"             # percall
                r"([\d.]+)\s+"             # cumtime
                r"([\d.]+)\s+"             # percall
                r"(.+)",                   # filename:lineno(function)
                line,
            )
            if not match:
                continue

            ncalls_str = match.group(1)
            tottime = float(match.group(2))
            cumtime = float(match.group(4))
            location = match.group(6)

            # Parse ncalls (handles "3/1" recursive format)
            if "/" in ncalls_str:
                ncalls = int(ncalls_str.split("/")[0])
            else:
                ncalls = int(ncalls_str)

            # Parse location: filename:lineno(function)
            loc_match = re.match(r"(.+):(\d+)\((.+)\)", location)
            if loc_match:
                file_path = loc_match.group(1)
                line_no = int(loc_match.group(2))
                func_name = loc_match.group(3)
            else:
                file_path = ""
                line_no = 0
                func_name = location

            result.samples.append(ProfileSample(
                function=func_name,
                file=file_path,
                line=line_no,
                time_ms=tottime * 1000,
                calls=ncalls,
                cumulative_ms=cumtime * 1000,
            ))

        if result.samples:
            result.total_time_ms = sum(s.time_ms for s in result.samples)

        return result

    def generate_flame_graph(self, result: ProfileResult) -> FlameGraph:
        """Generate a flame graph from profiling results."""
        root = FlameGraphNode(name="root", value=result.total_time_ms)
        graph = FlameGraph(root=root, total_samples=len(result.samples))

        # Group samples by file to create hierarchy
        file_groups: Dict[str, List[ProfileSample]] = {}
        for sample in result.samples:
            key = sample.file or "<unknown>"
            if key not in file_groups:
                file_groups[key] = []
            file_groups[key].append(sample)

        for file_path, samples in file_groups.items():
            file_node = FlameGraphNode(
                name=os.path.basename(file_path) if file_path else "<unknown>",
                value=sum(s.time_ms for s in samples),
            )
            for sample in samples:
                func_node = FlameGraphNode(
                    name=f"{sample.function} (line {sample.line})",
                    value=sample.time_ms,
                )
                file_node.children.append(func_node)
            root.children.append(file_node)

        return graph

    def export_flame_graph_html(self, graph: FlameGraph, output: str) -> None:
        """Export a flame graph as an interactive HTML file."""

        def node_to_dict(node: FlameGraphNode) -> Dict:
            return {
                "name": node.name,
                "value": round(node.value, 2),
                "children": [node_to_dict(c) for c in node.children],
            }

        data_json = json.dumps(node_to_dict(graph.root), indent=2)

        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Flame Graph - EoStudio Profiler</title>
<style>
  body { margin: 0; font-family: monospace; background: #1e1e1e; color: #ccc; }
  h1 { padding: 10px 20px; margin: 0; font-size: 16px; background: #2d2d2d; }
  .info { padding: 5px 20px; font-size: 12px; background: #252525; }
  #chart { padding: 20px; }
  .bar {
    display: block; position: relative; height: 20px; margin: 1px 0;
    background: #e74c3c; border-radius: 2px; cursor: pointer;
    font-size: 11px; line-height: 20px; padding: 0 4px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    color: white; min-width: 2px;
  }
  .bar:hover { opacity: 0.85; }
  .children { padding-left: 0; }
  .level-0 .bar { background: #e74c3c; }
  .level-1 .bar { background: #e67e22; }
  .level-2 .bar { background: #f1c40f; color: #333; }
  .level-3 .bar { background: #2ecc71; }
  .tooltip {
    position: fixed; background: #333; color: #fff; padding: 8px 12px;
    border-radius: 4px; font-size: 12px; pointer-events: none;
    display: none; z-index: 999;
  }
</style>
</head>
<body>
<h1>EoStudio Flame Graph</h1>
<div class="info">Total samples: """ + str(graph.total_samples) + """</div>
<div id="chart"></div>
<div class="tooltip" id="tooltip"></div>
<script>
const data = """ + data_json + """;
const chart = document.getElementById('chart');
const tooltip = document.getElementById('tooltip');
const totalValue = data.value || 1;

function renderNode(node, level, parentWidth) {
  const pct = (node.value / totalValue) * 100;
  const wrapper = document.createElement('div');
  wrapper.className = 'level-' + (level % 4);

  const bar = document.createElement('div');
  bar.className = 'bar';
  bar.style.width = Math.max(pct, 0.5) + '%';
  bar.textContent = node.name + ' (' + node.value.toFixed(1) + 'ms)';
  bar.addEventListener('mousemove', function(e) {
    tooltip.style.display = 'block';
    tooltip.style.left = (e.clientX + 10) + 'px';
    tooltip.style.top = (e.clientY + 10) + 'px';
    tooltip.textContent = node.name + ': ' + node.value.toFixed(2) +
      'ms (' + pct.toFixed(1) + '%)';
  });
  bar.addEventListener('mouseout', function() {
    tooltip.style.display = 'none';
  });
  wrapper.appendChild(bar);

  if (node.children && node.children.length > 0) {
    const childDiv = document.createElement('div');
    childDiv.className = 'children';
    node.children
      .sort(function(a, b) { return b.value - a.value; })
      .forEach(function(child) {
        childDiv.appendChild(renderNode(child, level + 1, pct));
      });
    wrapper.appendChild(childDiv);
  }
  return wrapper;
}

data.children
  .sort(function(a, b) { return b.value - a.value; })
  .forEach(function(child) {
    chart.appendChild(renderNode(child, 0, 100));
  });
</script>
</body>
</html>"""

        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w") as f:
            f.write(html)

    def get_history(self) -> List[ProfileResult]:
        """Return the history of profiling results from this session."""
        return list(self._history)

    def compare(
        self, result1: ProfileResult, result2: ProfileResult
    ) -> Dict:
        """Compare two profiling results and return a diff summary."""
        comparison: Dict = {
            "total_time_diff_ms": result2.total_time_ms - result1.total_time_ms,
            "total_time_pct_change": (
                ((result2.total_time_ms - result1.total_time_ms) / result1.total_time_ms * 100)
                if result1.total_time_ms > 0 else 0.0
            ),
            "peak_memory_diff_mb": result2.peak_memory_mb - result1.peak_memory_mb,
            "sample_count_diff": len(result2.samples) - len(result1.samples),
            "faster": [],
            "slower": [],
            "new": [],
            "removed": [],
        }

        funcs1 = {s.function: s for s in result1.samples}
        funcs2 = {s.function: s for s in result2.samples}

        for name, s2 in funcs2.items():
            if name in funcs1:
                s1 = funcs1[name]
                diff = s2.time_ms - s1.time_ms
                if diff < -0.1:
                    comparison["faster"].append({
                        "function": name,
                        "before_ms": round(s1.time_ms, 2),
                        "after_ms": round(s2.time_ms, 2),
                        "diff_ms": round(diff, 2),
                    })
                elif diff > 0.1:
                    comparison["slower"].append({
                        "function": name,
                        "before_ms": round(s1.time_ms, 2),
                        "after_ms": round(s2.time_ms, 2),
                        "diff_ms": round(diff, 2),
                    })
            else:
                comparison["new"].append({
                    "function": name,
                    "time_ms": round(s2.time_ms, 2),
                })

        for name in funcs1:
            if name not in funcs2:
                comparison["removed"].append({
                    "function": name,
                    "time_ms": round(funcs1[name].time_ms, 2),
                })

        return comparison
