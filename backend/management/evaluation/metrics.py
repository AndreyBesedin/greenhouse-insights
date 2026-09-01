"""Grades an AgentModelProvider against the eval cases in cases.py.

Metrics follow docs/design/greenhouse_agentic_management_design.md §37,
kept to the small initial set the doc asks for: action type accuracy,
parameter validity, unnecessary-action rate, missed-action rate, and an
investigation-correctness rate (folding in both "invalid tool-call rate" -
investigating when it was not warranted - and "inspection appropriateness",
since inspection is just one of the compared action types).
"""

from collections.abc import Callable

from pydantic import BaseModel

from management.agent.provider import AgentModelProvider
from management.agent.tools import AgentToolkit
from management.context import GreenhouseManagementContext
from management.evaluation.cases import CASES, EvalCase


class CaseResult(BaseModel):
    case_id: str
    action_type_correct: bool
    missed_action_types: frozenset[str]
    unnecessary_action_types: frozenset[str]
    param_valid: bool
    investigation_correct: bool

    @property
    def passed(self) -> bool:
        return self.action_type_correct and self.param_valid and self.investigation_correct


class Scorecard(BaseModel):
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def overall_pass_rate(self) -> float:
        return self._rate(lambda r: r.passed)

    @property
    def action_type_accuracy(self) -> float:
        return self._rate(lambda r: r.action_type_correct)

    @property
    def parameter_validity_rate(self) -> float:
        return self._rate(lambda r: r.param_valid)

    @property
    def unnecessary_action_rate(self) -> float:
        return self._rate(lambda r: bool(r.unnecessary_action_types))

    @property
    def missed_action_rate(self) -> float:
        return self._rate(lambda r: bool(r.missed_action_types))

    @property
    def investigation_correct_rate(self) -> float:
        return self._rate(lambda r: r.investigation_correct)

    def _rate(self, predicate: Callable[["CaseResult"], bool]) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if predicate(r)) / len(self.results)


def grade_case(case: EvalCase, provider: AgentModelProvider) -> CaseResult:
    context = GreenhouseManagementContext(
        greenhouse_id=case.plant_state.greenhouse_id,
        day=case.plant_state.simulated_day,
        plant_states=[case.plant_state],
    )
    toolkit = AgentToolkit(
        context,
        history_reader=lambda plant_id, days: case.history,
        budget=case.config.agent_tool_call_budget,
    )
    decision = provider.decide(context, toolkit, case.config)

    actual_types = frozenset(a.action_type for a in decision.actions)
    missed = case.expected_action_types - actual_types
    unnecessary = actual_types - case.expected_action_types

    param_valid = True
    for action in decision.actions:
        param_range = case.param_ranges.get(action.action_type)
        if param_range is None:
            continue
        field_name, low, high = param_range
        value = getattr(action, field_name, None)
        if value is None or not (low <= value <= high):
            param_valid = False

    investigated = any(call.tool == "get_plant_history" for call in toolkit.calls)

    return CaseResult(
        case_id=case.case_id,
        action_type_correct=actual_types == case.expected_action_types,
        missed_action_types=missed,
        unnecessary_action_types=unnecessary,
        param_valid=param_valid,
        investigation_correct=investigated == case.requires_investigation,
    )


def run_eval(provider: AgentModelProvider, cases: list[EvalCase] = CASES) -> Scorecard:
    return Scorecard(results=[grade_case(case, provider) for case in cases])


def format_report(scorecard: Scorecard) -> str:
    lines = [f"Eval report - {scorecard.total} cases", ""]
    for result in scorecard.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.case_id}")
        if result.missed_action_types:
            lines.append(f"    missed: {sorted(result.missed_action_types)}")
        if result.unnecessary_action_types:
            lines.append(f"    unnecessary: {sorted(result.unnecessary_action_types)}")
        if not result.param_valid:
            lines.append("    parameter out of acceptable range")
        if not result.investigation_correct:
            lines.append("    investigation (tool-call) behavior incorrect")
    lines.append("")
    lines.append(f"overall pass rate:          {scorecard.overall_pass_rate:.0%}")
    lines.append(f"action type accuracy:       {scorecard.action_type_accuracy:.0%}")
    lines.append(f"parameter validity rate:    {scorecard.parameter_validity_rate:.0%}")
    lines.append(f"unnecessary-action rate:    {scorecard.unnecessary_action_rate:.0%}")
    lines.append(f"missed-action rate:         {scorecard.missed_action_rate:.0%}")
    lines.append(f"investigation-correct rate: {scorecard.investigation_correct_rate:.0%}")
    return "\n".join(lines)
