from domain.enums import ActionExecutorType, ManagementPolicyType, SourceType


def test_source_type_has_expected_members() -> None:
    assert {member.value for member in SourceType} == {
        "SIMULATION",
        "REAL_SENSORS",
        "EXTERNAL_API",
        "IMPORTED_DATA",
    }


def test_management_policy_type_has_expected_members() -> None:
    assert {member.value for member in ManagementPolicyType} == {
        "NONE",
        "DETERMINISTIC",
        "AGENTIC",
    }


def test_action_executor_type_has_expected_members() -> None:
    assert {member.value for member in ActionExecutorType} == {"SIMULATED_OPERATOR"}
