"""The built-in demo suite: real ``gauntlet`` tasks with *staged* pitfalls.

Each :class:`Scenario` pairs a genuine ``gauntlet`` :class:`~gauntlet.Task` with a
list of ``cues`` (the mistakes to fix, in the order they surface) and a
``playbook`` for each stage — the trajectory the offline model follows when it
has learned that many cues so far.

The important idea, and what makes the curve organic rather than a tidy staircase:
**tasks have different numbers of pitfalls, and each pitfall only becomes visible
once the previous one is fixed.** A naive attempt trips pitfall #1; once that
lesson is learned the next attempt gets further and trips pitfall #2; and so on.
So an easy task is solved in one iteration and a three-pitfall task takes three —
the score climbs unevenly because the *tasks* genuinely differ.

Every cue is a token that (a) unlocks the next stage when present in the system
prompt and (b) really appears in that stage's failure evidence (a tool-error
string or the grader reason for the *first* unmet requirement). Cues are unique
across scenarios so a lesson for one task never accidentally unlocks another.

============  ==========  ==================================================
scenario      difficulty  pitfalls (cues), in the order they surface
============  ==========  ==================================================
delete_confirm   1        destructive call needs confirm=true
config_deploy    1        wrong config key (deploy_enabled)
ask_ambiguous    1        guessing instead of asking (ask_user)
discover_read    2        list_files first → then read the right path
replica_bump     2        get_config first → then set the right value
ticket_search    3        search → fetch to confirm → update the right ticket
============  ==========  ==================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gauntlet.types import GraderKind, GraderSpec, Task

Step = dict[str, Any]
Playbook = list[Step]


@dataclass(frozen=True)
class Scenario:
    """A gauntlet task plus one offline playbook per learning stage.

    ``cues[i]`` is the mistake fixed at stage ``i``. ``playbooks[level]`` is the
    trajectory the model follows when ``level`` of those cues are present in its
    system prompt; ``playbooks`` therefore has ``len(cues) + 1`` entries, and the
    last one is the fully-correct solution.
    """

    task: Task
    cues: tuple[str, ...]
    playbooks: tuple[Playbook, ...]

    @property
    def difficulty(self) -> int:
        return len(self.cues)


def build_scenarios() -> list[Scenario]:
    """Construct the six built-in scenarios (fresh objects each call)."""
    return [
        _delete_confirm(),
        _config_deploy(),
        _ask_ambiguous(),
        _discover_read(),
        _replica_bump(),
        _ticket_search(),
    ]


# --------------------------------------------------------------------------- #
# Difficulty 1
# --------------------------------------------------------------------------- #


def _delete_confirm() -> Scenario:
    task = Task(
        id="delete_confirm",
        capability="destructive-gating",
        prompt="Delete the stale file logs/old.log.",
        tools=["list_files", "delete_file"],
        initial_state={"files": {"logs/old.log": "stale", "logs/keep.log": "keep"}},
        graders=[
            GraderSpec(
                kind=GraderKind.TRAJECTORY,
                required_tools=["delete_file"],
                required_args={"delete_file": {"path": "logs/old.log", "confirm": True}},
            )
        ],
    )
    naive = [
        {"text": "I'll delete it.", "tool_calls": [
            {"id": "d1", "name": "delete_file", "arguments": {"path": "logs/old.log"}}]},
        {"text": "Done."},
    ]
    solved = [
        {"text": "Deleting with confirmation.", "tool_calls": [
            {"id": "d1", "name": "delete_file",
             "arguments": {"path": "logs/old.log", "confirm": True}}]},
        {"text": "Deleted logs/old.log."},
    ]
    return Scenario(task=task, cues=("confirm=true",), playbooks=(naive, solved))


def _config_deploy() -> Scenario:
    task = Task(
        id="config_deploy",
        capability="exact-parameter",
        prompt="Turn on deployments by enabling the deploy flag in the config.",
        tools=["get_config", "set_config"],
        initial_state={"config": {"deploy_enabled": False}},
        graders=[GraderSpec(kind=GraderKind.STATE, expected_state={"config.deploy_enabled": True})],
    )
    naive = [
        {"text": "Enabling deploy.", "tool_calls": [
            {"id": "c1", "name": "set_config", "arguments": {"key": "deploy", "value": True}}]},
        {"text": "Deployments enabled."},
    ]
    solved = [
        {"text": "Setting the deploy_enabled flag.", "tool_calls": [
            {"id": "c1", "name": "set_config",
             "arguments": {"key": "deploy_enabled", "value": True}}]},
        {"text": "deploy_enabled is now true."},
    ]
    return Scenario(task=task, cues=("deploy_enabled",), playbooks=(naive, solved))


def _ask_ambiguous() -> Scenario:
    task = Task(
        id="ask_ambiguous",
        capability="clarify-ambiguity",
        prompt="Close the billing ticket.",
        tools=["search_tickets", "get_ticket", "update_ticket", "ask_user"],
        initial_state={"tickets": {
            "T1": {"title": "Billing overcharge", "body": "charged twice", "status": "open"},
            "T2": {"title": "Billing address change", "body": "update address", "status": "open"},
        }},
        graders=[GraderSpec(kind=GraderKind.TRAJECTORY, required_tools=["ask_user"])],
    )
    naive = [
        {"text": "Closing the billing ticket.", "tool_calls": [
            {"id": "u1", "name": "update_ticket",
             "arguments": {"ticket_id": "T1", "status": "closed"}}]},
        {"text": "Closed."},
    ]
    solved = [
        {"text": "Multiple billing tickets exist; asking which one.", "tool_calls": [
            {"id": "a1", "name": "ask_user",
             "arguments": {"question": "Two billing tickets exist (T1 overcharge, T2 address). Which should I close?"}}]},
        {"text": "Waiting for clarification before closing."},
    ]
    return Scenario(task=task, cues=("ask_user",), playbooks=(naive, solved))


# --------------------------------------------------------------------------- #
# Difficulty 2
# --------------------------------------------------------------------------- #


def _discover_read() -> Scenario:
    task = Task(
        id="discover_read",
        capability="discover-before-act",
        prompt="Read the file that stores the database password and report it.",
        tools=["list_files", "read_file"],
        initial_state={"files": {
            "secrets/db.env": "password=hunter2",
            "README.md": "project readme",
        }},
        graders=[
            # Order matters: the first unmet requirement is what reflection sees.
            GraderSpec(kind=GraderKind.TRAJECTORY, required_tools=["list_files"]),
            GraderSpec(
                kind=GraderKind.TRAJECTORY,
                required_tools=["read_file"],
                required_args={"read_file": {"path": "secrets/db.env"}},
            ),
        ],
    )
    # Stage 0: guess a path without listing -> "list_files" not called.
    naive = [
        {"text": "Reading the env file.", "tool_calls": [
            {"id": "r1", "name": "read_file", "arguments": {"path": ".env"}}]},
        {"text": "Could not find it."},
    ]
    # Stage 1: list first, but still read the wrong path -> path requirement fails.
    listed = [
        {"text": "Listing files first.", "tool_calls": [
            {"id": "l1", "name": "list_files", "arguments": {}}]},
        {"text": "Trying the env file.", "tool_calls": [
            {"id": "r1", "name": "read_file", "arguments": {"path": ".env"}}]},
        {"text": "Still not found."},
    ]
    # Stage 2: list, then read the right path.
    solved = [
        {"text": "Listing files first.", "tool_calls": [
            {"id": "l1", "name": "list_files", "arguments": {}}]},
        {"text": "Found secrets/db.env; reading.", "tool_calls": [
            {"id": "r1", "name": "read_file", "arguments": {"path": "secrets/db.env"}}]},
        {"text": "The password is hunter2."},
    ]
    return Scenario(
        task=task,
        cues=("list_files", "secrets/db.env"),
        playbooks=(naive, listed, solved),
    )


def _replica_bump() -> Scenario:
    task = Task(
        id="replica_bump",
        capability="read-before-write",
        prompt="Increase the replica count in the config by one.",
        tools=["get_config", "set_config"],
        initial_state={"config": {"replicas": 3}},
        graders=[
            GraderSpec(kind=GraderKind.TRAJECTORY, required_tools=["get_config"]),
            GraderSpec(kind=GraderKind.STATE, expected_state={"config.replicas": 4}),
        ],
    )
    # Stage 0: write a guessed value without reading -> "get_config" not called.
    naive = [
        {"text": "Setting replicas.", "tool_calls": [
            {"id": "c1", "name": "set_config", "arguments": {"key": "replicas", "value": 2}}]},
        {"text": "Done."},
    ]
    # Stage 1: read first, but still set the wrong value -> state check fails ("expected 4").
    read = [
        {"text": "Reading current replicas.", "tool_calls": [
            {"id": "g1", "name": "get_config", "arguments": {"key": "replicas"}}]},
        {"text": "Setting a new value.", "tool_calls": [
            {"id": "c1", "name": "set_config", "arguments": {"key": "replicas", "value": 2}}]},
        {"text": "Done."},
    ]
    # Stage 2: read, then set current + 1.
    solved = [
        {"text": "Reading current replicas.", "tool_calls": [
            {"id": "g1", "name": "get_config", "arguments": {"key": "replicas"}}]},
        {"text": "Current is 3; setting to 4.", "tool_calls": [
            {"id": "c1", "name": "set_config", "arguments": {"key": "replicas", "value": 4}}]},
        {"text": "replicas is now 4."},
    ]
    return Scenario(
        task=task,
        cues=("get_config", "expected 4"),
        playbooks=(naive, read, solved),
    )


# --------------------------------------------------------------------------- #
# Difficulty 3
# --------------------------------------------------------------------------- #


def _ticket_search() -> Scenario:
    task = Task(
        id="ticket_search",
        capability="disambiguation-search",
        prompt="Mark the ticket about the login outage as resolved.",
        tools=["search_tickets", "get_ticket", "update_ticket"],
        initial_state={"tickets": {
            "T1": {"title": "Login outage", "body": "users cannot log in", "status": "open"},
            "T2": {"title": "Billing question", "body": "invoice looks wrong", "status": "open"},
        }},
        graders=[
            GraderSpec(kind=GraderKind.TRAJECTORY, required_tools=["search_tickets"]),
            GraderSpec(kind=GraderKind.TRAJECTORY, required_tools=["get_ticket"]),
            GraderSpec(kind=GraderKind.STATE, expected_state={"tickets.T1.status": "resolved"}),
        ],
    )
    # Stage 0: guess and update without searching -> "search_tickets" not called.
    naive = [
        {"text": "Resolving the likely ticket.", "tool_calls": [
            {"id": "u1", "name": "update_ticket",
             "arguments": {"ticket_id": "T2", "status": "resolved"}}]},
        {"text": "Resolved."},
    ]
    # Stage 1: search, but act without confirming which ticket -> "get_ticket" not called.
    searched = [
        {"text": "Searching for the outage ticket.", "tool_calls": [
            {"id": "s1", "name": "search_tickets", "arguments": {"query": "login outage"}}]},
        {"text": "Resolving one of the hits.", "tool_calls": [
            {"id": "u1", "name": "update_ticket",
             "arguments": {"ticket_id": "T2", "status": "resolved"}}]},
        {"text": "Resolved."},
    ]
    # Stage 2: search and fetch, but still update the wrong ticket -> state check names T1.
    fetched = [
        {"text": "Searching for the outage ticket.", "tool_calls": [
            {"id": "s1", "name": "search_tickets", "arguments": {"query": "login outage"}}]},
        {"text": "Fetching a candidate.", "tool_calls": [
            {"id": "g1", "name": "get_ticket", "arguments": {"ticket_id": "T1"}}]},
        {"text": "Resolving one of them.", "tool_calls": [
            {"id": "u1", "name": "update_ticket",
             "arguments": {"ticket_id": "T2", "status": "resolved"}}]},
        {"text": "Resolved."},
    ]
    # Stage 3: search, fetch T1, resolve T1.
    solved = [
        {"text": "Searching for the outage ticket.", "tool_calls": [
            {"id": "s1", "name": "search_tickets", "arguments": {"query": "login outage"}}]},
        {"text": "Confirming T1 is the outage.", "tool_calls": [
            {"id": "g1", "name": "get_ticket", "arguments": {"ticket_id": "T1"}}]},
        {"text": "Resolving T1.", "tool_calls": [
            {"id": "u1", "name": "update_ticket",
             "arguments": {"ticket_id": "T1", "status": "resolved"}}]},
        {"text": "T1 resolved."},
    ]
    return Scenario(
        task=task,
        cues=("search_tickets", "get_ticket", "tickets.T1"),
        playbooks=(naive, searched, fetched, solved),
    )
