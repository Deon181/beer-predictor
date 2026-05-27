"""Tests for the supplemental-beers layer in scripts/build_catalog.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_catalog as bc


def test_stratified_sample_does_not_emit_beer_id() -> None:
    """beer_id is assigned later in main() over the combined catalog,
    so the sampler must return only the seven non-id columns."""
    joined = bc.join_and_clean()
    normalized = bc.normalize_style(joined)
    sampled = bc.stratified_sample(normalized, target_size=100, seed=42)
    assert "beer_id" not in sampled.columns
    expected = {"name", "brewery", "style", "country", "abv", "ibu", "srm"}
    assert set(sampled.columns) == expected


def _make_valid_row() -> dict:
    return {
        "name": "Test Beer",
        "brewery": "Test Brewery",
        "style": "American Pale Ale",
        "country": "South Africa",
        "abv": 5.0,
        "ibu": 30.0,
        "srm": 5.0,
    }


def test_validate_supplement_accepts_well_formed_dataframe() -> None:
    df = pd.DataFrame([_make_valid_row()])
    bc._validate_supplement(df)


def test_validate_supplement_rejects_missing_column() -> None:
    df = pd.DataFrame([_make_valid_row()]).drop(columns=["ibu"])
    with pytest.raises(ValueError, match="missing columns"):
        bc._validate_supplement(df)


def test_validate_supplement_rejects_extra_column() -> None:
    row = _make_valid_row()
    row["srm_value"] = 5.0
    df = pd.DataFrame([row])
    with pytest.raises(ValueError, match="unexpected columns"):
        bc._validate_supplement(df)


def test_validate_supplement_rejects_unknown_style() -> None:
    row = _make_valid_row()
    row["style"] = "Definitely Not A Real Style"
    df = pd.DataFrame([row])
    with pytest.raises(ValueError, match="styles not in STYLE_ATTRS"):
        bc._validate_supplement(df)


def test_apply_supplements_no_file_is_silent_passthrough(tmp_path: Path) -> None:
    sampled = pd.DataFrame([_make_valid_row()])
    missing = tmp_path / "does_not_exist.csv"
    out = bc.apply_supplements(sampled, path=missing)
    pd.testing.assert_frame_equal(
        out.reset_index(drop=True), sampled.reset_index(drop=True)
    )


def test_apply_supplements_merges_supplement_rows(tmp_path: Path) -> None:
    sampled = pd.DataFrame([_make_valid_row()])
    supp_row = _make_valid_row()
    supp_row["name"] = "Different Beer"
    supp_path = tmp_path / "supp.csv"
    pd.DataFrame([supp_row]).to_csv(supp_path, index=False)

    out = bc.apply_supplements(sampled, path=supp_path)
    assert len(out) == 2
    assert "Test Beer" in out["name"].tolist()
    assert "Different Beer" in out["name"].tolist()


def test_apply_supplements_supplement_wins_on_duplicate(tmp_path: Path) -> None:
    sampled_row = _make_valid_row()
    sampled_row["abv"] = 4.0
    sampled = pd.DataFrame([sampled_row])

    supp_row = _make_valid_row()
    supp_row["abv"] = 9.9  # same (name, brewery), different value
    supp_path = tmp_path / "supp.csv"
    pd.DataFrame([supp_row]).to_csv(supp_path, index=False)

    out = bc.apply_supplements(sampled, path=supp_path)
    assert len(out) == 1
    assert out.iloc[0]["abv"] == 9.9, "supplement value should win on duplicate"


def test_apply_supplements_raises_on_malformed_file(tmp_path: Path) -> None:
    sampled = pd.DataFrame([_make_valid_row()])
    supp_path = tmp_path / "supp.csv"
    pd.DataFrame([{"name": "x", "brewery": "y"}]).to_csv(supp_path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        bc.apply_supplements(sampled, path=supp_path)


SUPP_FILE = ROOT / "data" / "raw" / "supplemental_beers.csv"


@pytest.mark.skipif(not SUPP_FILE.exists(), reason="supplement file not authored yet")
def test_supplement_file_passes_validation() -> None:
    df = pd.read_csv(SUPP_FILE)
    bc._validate_supplement(df)


@pytest.mark.skipif(not SUPP_FILE.exists(), reason="supplement file not authored yet")
def test_supplement_contains_south_african_beers() -> None:
    df = pd.read_csv(SUPP_FILE)
    sa = df[df["country"] == "South Africa"]
    assert len(sa) >= 20, f"expected ≥20 SA beers, got {len(sa)}"
