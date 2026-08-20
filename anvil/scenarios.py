"""The built-in demo suite: real ``gauntlet`` tasks, each with a known pitfall.

Each :class:`Scenario` pairs a genuine ``gauntlet`` :class:`~gauntlet.Task` (a
goal, a seeded world, real graders) with two trajectories the offline model can
follow — a ``naive`` one that trips the task's pitfall and fails the grader, and
an ``improved`` one that succeeds. The ``cue`` is the token that flips the model
from naive to improved *and* — this is the important part — a token that really
appears in the failure evidence ``gauntlet`` emits (a tool-error string or a
grader reason). That is what lets reflection derive a working lesson from the
observed failure rather than from a hidden answer key.

The six scenarios each isolate a distinct, classic agent mistake:

===================  =========================================  ================
scenario             pitfall                                    cue
===================  =========================================  ================
delete_confirm       destructive call without ``confirm=true``  ``confirm=true``
config_deploy        wrong config key                           ``deploy_enabled``
ticket_search        acting before searching/disambiguating     ``search_tickets``
discover_read        guessing a path instead of listing         ``list_files``
ask_ambiguous        guessing instead of asking on ambiguity    ``ask_user``
replica_bump         writing without reading current state      ``get_config``
===================  =========================================  ================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gauntlet.types import GraderKind, GraderSpec, Task


@dataclass(frozen=True)
class Scenario:
    """A gauntlet task plus the offline model's naive/improved playbooks.

    ``cue`` is a substring that (a) unlocks ``improved_steps`` when present in
    the model's system prompt and (b) genuinely appears in the failure evidence
    of ``naive_steps`` — so a lesson distilled from the failure contains it.
    """

    task: Task
    cue: str
    naive_steps: list[dict[str, Any]]
    improved_steps: list[dict[str, Any]]


def build_scenarios() -> list[Scenario]:
    """Construct the six built-in scenarios (fresh objects each call)."""
    return [
        _delete_confirm(),
        _config_deploy(),
        _ticket_search(),
        _discover_read(),
        _ask_ambiguous(),
        _replica_bump(),
    ]


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
    improved = [
        {"text": "Deleting with confirmation.", "tool_calls": [
            {"id": "d1", "name": "delete_file",
             "arguments": {"path": "logs/old.log", "confirm": True}}]},
        {"text": "Deleted logs/old.log."},
    ]
    return Scenario(task=task, cue="confirm=true", naive_steps=naive, improved_steps=improved)


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
    improved = [
        {"text": "Setting the deploy_enabled flag.", "tool_calls": [
            {"id": "c1", "name": "set_config",
             "arguments": {"key": "deploy_enabled", "value": True}}]},
        {"text": "deploy_enabled is now true."},
    ]
    return Scenario(task=task, cue="deploy_enabled", naive_steps=naive, improved_steps=improved)


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
            GraderSpec(kind=GraderKind.STATE, expected_state={"tickets.T1.status": "resolved"}),
        ],
    )
    naive = [
        {"text": "I'll resolve the billing-looking ticket.", "tool_calls": [
            {"id": "u1", "name": "update_ticket",
             "arguments": {"ticket_id": "T2", "status": "resolved"}}]},
        {"text": "Resolved."},
    ]
    improved = [
        {"text": "Searching for the outage ticket first.", "tool_calls": [
            {"id": "s1", "name": "search_tickets", "arguments": {"query": "login outage"}}]},
        {"text": "Found T1; resolving it.", "tool_calls": [
            {"id": "u1", "name": "update_ticket",
             "arguments": {"ticket_id": "T1", "status": "resolved"}}]},
        {"text": "T1 resolved."},
    ]
    return Scenario(task=task, cue="search_tickets", naive_steps=naive, improved_steps=improved)


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
            GraderSpec(
                kind=GraderKind.TRAJECTORY,
                required_tools=["list_files", "read_file"],
                ordering=["list_files", "read_file"],
                required_args={"read_file": {"path": "secrets/db.env"}},
            )
        ],
    )
    naive = [
        {"text": "Reading the env file.", "tool_calls": [
            {"id": "r1", "name": "read_file", "arguments": {"path": ".env"}}]},
        {"text": "Could not find it."},
    ]
    improved = [
        {"text": "Listing files to find it.", "tool_calls": [
            {"id": "l1", "name": "list_files", "arguments": {}}]},
        {"text": "Found secrets/db.env; reading.", "tool_calls": [
            {"id": "r1", "name": "read_file", "arguments": {"path": "secrets/db.env"}}]},
        {"text": "The password is hunter2."},
    ]
    return Scenario(task=task, cue="list_files", naive_steps=naive, improved_steps=improved)


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
    improved = [
        {"text": "Multiple billing tickets exist; asking which one.", "tool_calls": [
            {"id": "a1", "name": "ask_user",
             "arguments": {"question": "Two billing tickets exist (T1 overcharge, T2 address). Which should I close?"}}]},
        {"text": "Waiting for clarification before closing."},
    ]
    return Scenario(task=task, cue="ask_user", naive_steps=naive, improved_steps=improved)


def _replica_bump() -> Scenario:
    task = Task(
        id="replica_bump",
        capability="read-before-write",
        prompt="Increase the replica count in the config by one.",
        tools=["get_config", "set_config"],
        initial_state={"config": {"replicas": 3}},
        graders=[
            GraderSpec(
                kind=GraderKind.TRAJECTORY,
                required_tools=["get_config"],
                ordering=["get_config", "set_config"],
            ),
            GraderSpec(kind=GraderKind.STATE, expected_state={"config.replicas": 4}),
        ],
    )
    naive = [
        {"text": "Setting replicas.", "tool_calls": [
            {"id": "c1", "name": "set_config", "arguments": {"key": "replicas", "value": 2}}]},
        {"text": "Done."},
    ]
    improved = [
        {"text": "Reading current replicas first.", "tool_calls": [
            {"id": "g1", "name": "get_config", "arguments": {"key": "replicas"}}]},
        {"text": "Current is 3; setting to 4.", "tool_calls": [
            {"id": "c1", "name": "set_config", "arguments": {"key": "replicas", "value": 4}}]},
        {"text": "replicas is now 4."},
    ]
    return Scenario(task=task, cue="get_config", naive_steps=naive, improved_steps=improved)
