"""
Tests for interpolation validation and quality report assets
"""

import pandas as pd
import pytest
from unittest.mock import Mock

# Import Dagster testing utilities
from dagster import build_asset_context

# Import the functions we want to test
import sys
from pathlib import Path

# Add workflows_dagster to path
workflows_dagster_path = Path(__file__).parent.parent.parent / "workflows_dagster"
sys.path.insert(0, str(workflows_dagster_path))

from dagster_project.assets.analytics_assets import (
    interpolation_validation,
    interpolation_quality_report,
)


class TestInterpolationValidation:
    """Tests for interpolation_validation asset"""

    @pytest.fixture
    def mock_config(self):
        """Mock config resource"""
        config = Mock()
        config.load_config.return_value = {"start_year": 2020}
        return config

    @pytest.fixture
    def matching_data(self):
        """Create raw and interpolated data that match perfectly"""
        # Raw data (sparse - every 5 days)
        raw_timestamps = pd.date_range("2024-01-01", "2024-01-31", freq="5D", tz="UTC")
        raw_data = pd.DataFrame(
            {
                "timestamp": raw_timestamps,
                "value": [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0],
            }
        )

        # Interpolated data (daily - includes all raw timestamps with same values)
        interp_timestamps = pd.date_range(
            "2024-01-01", "2024-01-31", freq="D", tz="UTC"
        )
        # Create interpolated values that match raw values at raw timestamps
        interp_values = []
        for ts in interp_timestamps:
            if ts in raw_timestamps.values:
                # Find matching raw value
                idx = raw_timestamps.get_loc(ts)
                interp_values.append(raw_data.iloc[idx]["value"])
            else:
                # Linear interpolation for intermediate points
                interp_values.append(100.0 + (ts.day - 1) * 1.0)

        interp_data = pd.DataFrame(
            {
                "timestamp": interp_timestamps,
                "value": interp_values,
            }
        )

        return {
            "raw": {"test_meter": raw_data},
            "interpolated": {"test_meter": interp_data},
        }

    @pytest.fixture
    def mismatched_data(self):
        """Create raw and interpolated data that don't match"""
        # Raw data
        raw_timestamps = pd.date_range("2024-01-01", "2024-01-31", freq="5D", tz="UTC")
        raw_data = pd.DataFrame(
            {
                "timestamp": raw_timestamps,
                "value": [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0],
            }
        )

        # Interpolated data with DIFFERENT values at raw timestamps
        interp_timestamps = pd.date_range(
            "2024-01-01", "2024-01-31", freq="D", tz="UTC"
        )
        # Create interpolated values that DON'T match raw values
        interp_values = [100.0 + i * 0.9 for i in range(len(interp_timestamps))]

        interp_data = pd.DataFrame(
            {
                "timestamp": interp_timestamps,
                "value": interp_values,
            }
        )

        return {
            "raw": {"test_meter": raw_data},
            "interpolated": {"test_meter": interp_data},
        }

    def test_validation_passes_with_matching_data(self, matching_data):
        """Test that validation passes when interpolated matches raw"""
        context = build_asset_context()

        result = interpolation_validation(
            context,
            matching_data["interpolated"],
            matching_data["raw"],
        )

        assert "test_meter" in result
        assert result["test_meter"]["all_match"] is True
        assert result["test_meter"]["validated_points"] == 7  # 7 raw readings
        assert result["test_meter"]["max_deviation"] < 0.01
        assert len(result["test_meter"]["mismatches"]) == 0

    def test_validation_fails_with_mismatched_data(self, mismatched_data):
        """Test that validation fails when interpolated doesn't match raw"""
        context = build_asset_context()

        with pytest.raises(ValueError, match="Interpolation validation FAILED"):
            interpolation_validation(
                context,
                mismatched_data["interpolated"],
                mismatched_data["raw"],
            )

    def test_validation_handles_empty_data(self):
        """Test that validation handles empty data gracefully"""
        context = build_asset_context()

        empty_data = {
            "raw": {"test_meter": pd.DataFrame()},
            "interpolated": {"test_meter": pd.DataFrame()},
        }

        result = interpolation_validation(
            context,
            empty_data["interpolated"],
            empty_data["raw"],
        )

        assert "test_meter" in result
        assert result["test_meter"]["all_match"] is True
        assert result["test_meter"]["validated_points"] == 0

    def test_validation_handles_missing_meter(self, matching_data):
        """Test that validation handles meter in interpolated but not in raw"""
        context = build_asset_context()

        # Add meter to interpolated that's not in raw
        matching_data["interpolated"]["missing_meter"] = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", "2024-01-10", freq="D", tz="UTC"
                ),
                "value": [100.0 + i for i in range(10)],
            }
        )

        result = interpolation_validation(
            context,
            matching_data["interpolated"],
            matching_data["raw"],
        )

        # Should still validate the meter that exists
        assert "test_meter" in result
        # Missing meter should not be in results
        assert "missing_meter" not in result or result["missing_meter"]["all_match"]


class TestInterpolationQualityReport:
    """Tests for interpolation_quality_report asset"""

    @pytest.fixture
    def mock_config(self):
        """Mock config resource"""
        config = Mock()
        config.load_config.return_value = {"start_year": 2024}
        return config

    @pytest.fixture
    def sample_data(self):
        """Create sample raw and interpolated data for quality report"""
        # Raw data (sparse - weekly readings)
        raw_timestamps = pd.date_range("2024-01-01", "2024-03-01", freq="7D", tz="UTC")
        raw_data = pd.DataFrame(
            {
                "timestamp": raw_timestamps,
                "value": [100.0 + i * 10 for i in range(len(raw_timestamps))],
            }
        )

        # Interpolated data (daily)
        interp_timestamps = pd.date_range(
            "2024-01-01", "2024-03-31", freq="D", tz="UTC"
        )
        interp_data = pd.DataFrame(
            {
                "timestamp": interp_timestamps,
                "value": [100.0 + i * 1.5 for i in range(len(interp_timestamps))],
            }
        )

        return {
            "raw": {"test_meter": raw_data},
            "interpolated": {"test_meter": interp_data},
        }

    def test_quality_report_generation(self, mock_config, sample_data):
        """Test that quality report is generated correctly"""
        context = build_asset_context()

        report = interpolation_quality_report(
            context,
            sample_data["interpolated"],
            sample_data["raw"],
            mock_config,
        )

        assert isinstance(report, pd.DataFrame)
        assert not report.empty
        assert "meter_id" in report.columns
        assert "raw_readings_count" in report.columns
        assert "interpolated_days_count" in report.columns
        assert "largest_gap_days" in report.columns
        assert "avg_gap_size_days" in report.columns
        assert "extrapolation_forward_days" in report.columns
        assert "extrapolation_backward_days" in report.columns
        assert "raw_data_coverage_pct" in report.columns

        # Check values for test_meter
        test_row = report[report["meter_id"] == "test_meter"].iloc[0]
        assert test_row["raw_readings_count"] == 9  # Weekly readings for ~60 days
        assert test_row["interpolated_days_count"] == 91  # Daily from Jan 1 to Mar 31
        assert test_row["largest_gap_days"] == 7.0  # Weekly gaps
        assert test_row["avg_gap_size_days"] == 7.0  # Consistent weekly gaps

    def test_quality_report_handles_empty_data(self, mock_config):
        """Test that quality report handles empty data"""
        context = build_asset_context()

        empty_data = {
            "raw": {},
            "interpolated": {},
        }

        report = interpolation_quality_report(
            context,
            empty_data["interpolated"],
            empty_data["raw"],
            mock_config,
        )

        assert isinstance(report, pd.DataFrame)
        assert report.empty  # Should be empty if no data

    def test_quality_report_multiple_meters(self, mock_config):
        """Test quality report with multiple meters"""
        context = build_asset_context()

        # Create data for multiple meters
        data = {
            "raw": {},
            "interpolated": {},
        }

        for meter_id in ["meter_1", "meter_2", "meter_3"]:
            # Different patterns for each meter
            if meter_id == "meter_1":
                freq = "7D"  # Weekly
            elif meter_id == "meter_2":
                freq = "1D"  # Daily
            else:
                freq = "14D"  # Bi-weekly

            raw_timestamps = pd.date_range(
                "2024-01-01", "2024-02-29", freq=freq, tz="UTC"
            )
            data["raw"][meter_id] = pd.DataFrame(
                {
                    "timestamp": raw_timestamps,
                    "value": [100.0 + i * 5 for i in range(len(raw_timestamps))],
                }
            )

            # All interpolated to daily
            interp_timestamps = pd.date_range(
                "2024-01-01", "2024-03-31", freq="D", tz="UTC"
            )
            data["interpolated"][meter_id] = pd.DataFrame(
                {
                    "timestamp": interp_timestamps,
                    "value": [100.0 + i * 1.0 for i in range(len(interp_timestamps))],
                }
            )

        report = interpolation_quality_report(
            context,
            data["interpolated"],
            data["raw"],
            mock_config,
        )

        assert len(report) == 3  # Three meters
        assert set(report["meter_id"]) == {"meter_1", "meter_2", "meter_3"}

        # Verify different gap sizes
        meter_1_gaps = report[report["meter_id"] == "meter_1"]["largest_gap_days"].iloc[
            0
        ]
        meter_2_gaps = report[report["meter_id"] == "meter_2"]["largest_gap_days"].iloc[
            0
        ]
        meter_3_gaps = report[report["meter_id"] == "meter_3"]["largest_gap_days"].iloc[
            0
        ]

        assert meter_1_gaps == 7.0  # Weekly
        assert meter_2_gaps == 0.0  # Daily (no gaps)
        assert meter_3_gaps == 14.0  # Bi-weekly


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
