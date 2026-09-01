import pytest

from management.agent.provider import FakeAgentModelProvider
from management.evaluation.cases import CASES, EvalCase
from management.evaluation.metrics import grade_case, run_eval


@pytest.mark.parametrize("case", CASES, ids=[case.case_id for case in CASES])
def test_fake_provider_passes_each_eval_case(case: EvalCase) -> None:
    result = grade_case(case, FakeAgentModelProvider())

    assert result.action_type_correct, (
        f"expected {case.expected_action_types}, missed {result.missed_action_types}, "
        f"unnecessary {result.unnecessary_action_types}"
    )
    assert result.param_valid
    assert result.investigation_correct


def test_scorecard_is_all_green_for_the_fake_provider() -> None:
    scorecard = run_eval(FakeAgentModelProvider())

    assert scorecard.total == len(CASES)
    assert scorecard.overall_pass_rate == 1.0
