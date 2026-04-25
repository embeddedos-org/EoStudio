"""Interactive prototyping engine — interactions, transitions, gestures, state machine."""

from eostudio.core.prototyping.interactions import (
    Interaction,
    InteractionTrigger,
    InteractionAction,
    InteractionManager,
)
from eostudio.core.prototyping.transitions import (
    ScreenTransition,
    TransitionType,
    TransitionDirection,
)
from eostudio.core.prototyping.gestures import (
    GestureRecognizer,
    GestureType,
    GestureEvent,
)
from eostudio.core.prototyping.state_machine import (
    PrototypeState,
    StateTransition,
    StateMachine,
    PrototypeVariable,
)
from eostudio.core.prototyping.player import PrototypePlayer

__all__ = [
    "Interaction", "InteractionTrigger", "InteractionAction", "InteractionManager",
    "ScreenTransition", "TransitionType", "TransitionDirection",
    "GestureRecognizer", "GestureType", "GestureEvent",
    "PrototypeState", "StateTransition", "StateMachine", "PrototypeVariable",
    "PrototypePlayer",
]
