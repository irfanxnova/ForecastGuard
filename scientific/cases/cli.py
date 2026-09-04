"""Command-line interface for ForecastGuard historical case runner.

Usage:
    python -m scientific.cases.cli run-case --case-id demo_001 \\
        --forecast data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib \\
        --observation data/raw/observations/imd_daily/01092025.grd \\
        --observation-date 2025-09-01
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scientific.cases import RainfallCase, run_rainfall_case, persist_rainfall_case

UTC = timezone.utc


def run_case_command(args: argparse.Namespace) -> int:
	"""Execute a single rainfall case and optionally persist results."""
	try:
		# Parse observation date
		obs_date_str = args.observation_date
		if obs_date_str:
			obs_date = datetime.fromisoformat(obs_date_str).date() if "T" not in obs_date_str else datetime.fromisoformat(obs_date_str)
		else:
			obs_date = None

		# Parse observation window if provided
		obs_start: Optional[datetime] = None
		obs_end: Optional[datetime] = None
		if args.observation_start and args.observation_end:
			obs_start = datetime.fromisoformat(args.observation_start)
			obs_end = datetime.fromisoformat(args.observation_end)

		# Create case
		case = RainfallCase(
			case_id=args.case_id,
			forecast_path=Path(args.forecast),
			observation_path=Path(args.observation),
			observation_date=obs_date,
			observation_start=obs_start,
			observation_end=obs_end,
		)

		# Run case
		print(f"Running case: {case.case_id}")
		result = run_rainfall_case(case)

		# Print result summary
		print(f"Status: {result.status.value}")
		print(f"Valid cells: {result.valid_cell_count}")
		print(f"Missing cells: {result.missing_cell_count}")
		if result.error_statistics:
			print(f"Error statistics: {result.error_statistics}")

		# Optionally persist
		if args.persist:
			output_base = Path(args.output_base) if args.output_base else Path("data/interim/cases")
			updated = persist_rainfall_case(result, output_base)
			print(f"Case persisted to: {output_base / case.case_id}")

		# Output JSON if requested
		if args.json_output:
			output_dict = {
				"case_id": result.case_id,
				"status": result.status.value,
				"forecast_metadata": result.forecast_metadata,
				"observation_metadata": result.observation_metadata,
				"forecast_window": result.forecast_window,
				"observation_window": result.observation_window,
				"valid_cell_count": result.valid_cell_count,
				"missing_cell_count": result.missing_cell_count,
				"error_statistics": result.error_statistics,
				"provenance": result.provenance,
			}
			json_output = Path(args.json_output)
			json_output.parent.mkdir(parents=True, exist_ok=True)
			with open(json_output, "w") as f:
				json.dump(output_dict, f, indent=2)
			print(f"JSON output written to: {json_output}")

		return 0

	except Exception as exc:
		print(f"Error: {exc}")
		return 1


def main() -> int:
	"""Main CLI entry point."""
	parser = argparse.ArgumentParser(
		description="ForecastGuard historical case runner",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  # Run case without observation window (expects BLOCKED status)
  python -m scientific.cases.cli run-case \\
    --case-id test_001 \\
    --forecast data/raw/tigge/forecast.grib \\
    --observation data/raw/observations/obs.grd \\
    --observation-date 2025-09-01

  # Run case with explicit observation window
  python -m scientific.cases.cli run-case \\
    --case-id test_002 \\
    --forecast data/raw/tigge/forecast.grib \\
    --observation data/raw/observations/obs.grd \\
    --observation-date 2025-09-01 \\
    --observation-start "2025-09-01T00:00:00+00:00" \\
    --observation-end "2025-09-02T00:00:00+00:00"

  # Run and persist with JSON output
  python -m scientific.cases.cli run-case \\
    --case-id test_003 \\
    --forecast data/raw/tigge/forecast.grib \\
    --observation data/raw/observations/obs.grd \\
    --observation-date 2025-09-01 \\
    --persist \\
    --json-output result.json
		""",
	)

	subparsers = parser.add_subparsers(dest="command", help="Available commands")

	# run-case subcommand
	run_parser = subparsers.add_parser("run-case", help="Run a single forecast case")
	run_parser.add_argument("--case-id", required=True, help="Unique case identifier")
	run_parser.add_argument("--forecast", required=True, help="Path to GRIB forecast file")
	run_parser.add_argument("--observation", required=True, help="Path to IMD observation file")
	run_parser.add_argument("--observation-date", required=True, help="Observation date (YYYY-MM-DD)")
	run_parser.add_argument(
		"--observation-start", help="Observation window start (ISO format with timezone)"
	)
	run_parser.add_argument(
		"--observation-end", help="Observation window end (ISO format with timezone)"
	)
	run_parser.add_argument(
		"--persist", action="store_true", help="Persist case result to disk"
	)
	run_parser.add_argument(
		"--output-base", help="Base directory for case outputs (default: data/interim/cases)"
	)
	run_parser.add_argument("--json-output", help="Write JSON result to file")
	run_parser.set_defaults(func=run_case_command)

	args = parser.parse_args()

	if not hasattr(args, "func"):
		parser.print_help()
		return 0

	return args.func(args)


if __name__ == "__main__":
	exit(main())
