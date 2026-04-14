"""Simulation subpackage."""

from eostudio.core.simulation.engine import (
    Signal, Block, SourceBlock, GainBlock, SumBlock, PIDBlock, ScopeBlock, SimulationModel,
)

SimBlock = Block
SimConnection = None
SimEngine = SimulationModel

__all__ = [
    "Signal", "Block", "SimBlock", "SourceBlock", "GainBlock", "SumBlock",
    "PIDBlock", "ScopeBlock", "SimulationModel", "SimConnection", "SimEngine",
]
