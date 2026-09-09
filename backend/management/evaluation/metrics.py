"""Grades an AgentModelProvider against the eval cases in cases.py.

Metrics follow docs/archive/design-history/greenhouse_agentic_management_design.md §37,
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
from management.evaluation.cases import CASES, EvalCase, build_history, build_plant_state


class CaseResult(BaseModel):
    case_id: str
    description: str
    action_type_correct: bool
    missed_action_types: frozenset[str]
    unnecessary_action_types: frozenset[str]
    param_valid: bool
    investigation_correct: bool
    condition_correct: bool = True
    """Whether reconstruct_plant_state's health matched the case's
    expected_condition - always True for cases that don't assert one."""

    @property
    def passed(self) -> bool:
        return (
            self.action_type_correct
            and self.param_valid
            and self.investigation_correct
            and self.condition_correct
        )


class Scorecard(BaseModel):
    provider: str
    model: str
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

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

    @property
    def condition_correct_rate(self) -> float:
        return self._rate(lambda r: r.condition_correct)

    def _rate(self, predicate: Callable[["CaseResult"], bool]) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if predicate(r)) / len(self.results)


def grade_case(case: EvalCase, provider: AgentModelProvider) -> tuple[CaseResult, str, str]:
    plant_state = build_plant_state(case)
    history = build_history(case)
    context = GreenhouseManagementContext(
        greenhouse_id=case.greenhouse_id,
        day=case.day,
        plant_states=[plant_state],
    )
    toolkit = AgentToolkit(
        context,
        history_reader=lambda plant_id, days: history[-days:],
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
    condition_correct = (
        case.expected_condition is None or plant_state.health == case.expected_condition
    )

    result = CaseResult(
        case_id=case.case_id,
        description=case.description,
        action_type_correct=actual_types == case.expected_action_types,
        missed_action_types=missed,
        unnecessary_action_types=unnecessary,
        param_valid=param_valid,
        investigation_correct=investigated == case.requires_investigation,
        condition_correct=condition_correct,
    )
    return result, decision.provider, decision.model


def run_eval(provider: AgentModelProvider, cases: list[EvalCase] = CASES) -> Scorecard:
    graded = [grade_case(case, provider) for case in cases]
    provider_name, model_name = (graded[0][1], graded[0][2]) if graded else ("", "")
    return Scorecard(
        provider=provider_name, model=model_name, results=[result for result, _, _ in graded]
    )


def format_report(scorecard: Scorecard) -> str:
    lines = [
        f"Agent decision-quality evaluation - {scorecard.provider}/{scorecard.model}",
        f"{scorecard.passed_count}/{scorecard.total} cases passed "
        f"({scorecard.overall_pass_rate:.0%})",
        "",
    ]
    id_width = max((len(r.case_id) for r in scorecard.results), default=0)
    for result in scorecard.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.case_id:<{id_width}}  {result.description}")
        if result.missed_action_types:
            lines.append(f"       missed: {sorted(result.missed_action_types)}")
        if result.unnecessary_action_types:
            lines.append(f"       unnecessary: {sorted(result.unnecessary_action_types)}")
        if not result.param_valid:
            lines.append("       parameter out of acceptable range")
        if not result.investigation_correct:
            lines.append("       investigation (tool-call) behavior incorrect")
        if not result.condition_correct:
            lines.append("       reconstructed plant condition did not match expected")
    lines.append("")
    lines.append(f"action type accuracy:       {scorecard.action_type_accuracy:.0%}")
    lines.append(f"parameter validity rate:    {scorecard.parameter_validity_rate:.0%}")
    lines.append(f"unnecessary-action rate:    {scorecard.unnecessary_action_rate:.0%}")
    lines.append(f"missed-action rate:         {scorecard.missed_action_rate:.0%}")
    lines.append(f"investigation-correct rate: {scorecard.investigation_correct_rate:.0%}")
    lines.append(f"condition-correct rate:     {scorecard.condition_correct_rate:.0%}")
    return "\n".join(lines)
