from pathlib import Path

import pytest

from ingestion.cli import main
from ingestion.manifests import ArtifactKind
from ingestion.profiles import PROFILES, Profile


def test_tiny_and_dev_profiles_can_never_download_image_archives() -> None:
    for profile in (Profile.TINY, Profile.DEV):
        rules = PROFILES[profile]
        assert ArtifactKind.LONGITUDINAL_RGBD not in rules.artifact_kinds
        assert ArtifactKind.LABELLED_IMAGES not in rules.artifact_kinds
        assert rules.max_download_bytes is not None
        assert rules.max_download_bytes <= 1024**3
    assert PROFILES[Profile.FULL].artifact_kinds == frozenset(ArtifactKind)


def test_load_without_prepared_data_explains_what_to_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            "load",
            "wur",
            "agc4-2024",
            "--compartment",
            "3.06",
            "--data-dir",
            str(tmp_path),
            "--database-url",
            f"sqlite:///{tmp_path / 'app.db'}",
        ]
    )

    assert code == 1
    assert "greenhouse-data prepare wur agc4-2024 --profile tiny" in capsys.readouterr().out


def test_only_the_2024_dataset_has_an_adapter_so_far(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="agc4-2023"):
        main(["prepare", "wur", "agc4-2023", "--profile", "tiny", "--data-dir", str(tmp_path)])
