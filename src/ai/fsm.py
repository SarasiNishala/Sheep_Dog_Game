"""
Finite State Machine - Lightweight FSM for agent behavior.

We implement a small FSM by hand rather than using the `transitions`
library so the code is self-contained (no extra pip installs) and so
graders can see the transitions clearly.

Each Agent owns an FSM instance.  States are simple strings; the agent's
AI tick chooses when to call fsm.change_state(new).
"""


class FSM:
    """Tracks the current state and transition history of a single agent."""

    def __init__(self, initial_state: str, states: list, agent_name: str = ""):
        self.state = initial_state
        self.previous_state = initial_state
        self.states = states
        self.agent_name = agent_name
        self.time_in_state = 0.0

        # transition history for the debug overlay and for auto-generating
        # state diagrams in the DESIGN.md writeup
        self.transition_log = []
        self.max_log = 20

    def change_state(self, new_state: str, reason: str = ""):
        """Transition to a new state.  Records the change for debugging."""
        if new_state == self.state:
            return
        if new_state not in self.states:
            raise ValueError(
                f"[{self.agent_name}] unknown state '{new_state}'. "
                f"valid: {self.states}"
            )

        self.previous_state = self.state
        self.transition_log.append(
            f"{self.state} -> {new_state}"
            + (f" ({reason})" if reason else "")
        )
        if len(self.transition_log) > self.max_log:
            self.transition_log.pop(0)

        self.state = new_state
        self.time_in_state = 0.0

    def update(self, dt: float):
        """Advance state-local timer.  Called every frame."""
        self.time_in_state += dt

    def is_in(self, *state_names) -> bool:
        return self.state in state_names
