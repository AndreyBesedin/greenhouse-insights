"""Prints the eval scorecard for the current default agent provider.

Run from backend/: python -m management.evaluation
"""

from management.agent.provider import build_default_provider
from management.evaluation.metrics import format_report, run_eval


def main() -> None:
    scorecard = run_eval(build_default_provider())
    print(format_report(scorecard))


if __name__ == "__main__":
    main()
