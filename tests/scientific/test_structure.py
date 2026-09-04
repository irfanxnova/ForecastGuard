"""Tests verifying scientific and data architectural directory boundaries."""

import importlib
from pathlib import Path


def test_scientific_packages_importable() -> None:
    """Verify scientific subpackages can be imported cleanly."""
    subpackages = [
        "scientific",
        "scientific.ingestion",
        "scientific.parsing",
        "scientific.qc",
        "scientific.alignment",
        "scientific.verification",
        "scientific.features",
        "scientific.targets",
        "scientific.ml",
    ]

    for pkg_name in subpackages:
        module = importlib.import_module(pkg_name)
        assert module is not None, f"Failed to import package: {pkg_name}"


def test_data_directory_structure_exists() -> None:
    """Verify required data taxonomy directories exist with .gitkeep."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    expected_dirs = [
        repo_root / "data" / "raw" / "tigge",
        repo_root / "data" / "raw" / "observations",
        repo_root / "data" / "interim",
        repo_root / "data" / "processed",
        repo_root / "data" / "features",
        repo_root / "data" / "manifests",
    ]

    for directory in expected_dirs:
        assert directory.exists(), f"Missing directory: {directory}"
        assert directory.is_dir(), f"Not a directory: {directory}"
        gitkeep = directory / ".gitkeep"
        assert gitkeep.exists(), f"Missing .gitkeep in {directory}"
