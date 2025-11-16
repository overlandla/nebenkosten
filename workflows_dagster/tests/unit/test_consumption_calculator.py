"""
Unit tests for ConsumptionCalculator
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
workflows_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workflows_path))

from src.calculator import ConsumptionCalculator


class TestConsumptionCalculator:
    """Test suite for ConsumptionCalculator"""

    @pytest.fixture
    def calculator(self):
        """Create ConsumptionCalculator instance"""
        return ConsumptionCalculator()

    def test_calculate_consumption_from_readings_basic(self, calculator):
        """Test basic consumption calculation"""
        # Cumulative readings
        readings = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC"),
                "value": [100.0, 102.5, 105.0, 108.0, 110.5],
            }
        )

        result = calculator.calculate_consumption_from_readings(readings)

        assert len(result) == 5
        assert "value" in result.columns
        # First day should be 0 (no previous value)
        assert result.iloc[0]["value"] == 0.0
        # Second day: 102.5 - 100.0 = 2.5
        assert result.iloc[1]["value"] == 2.5
        # Third day: 105.0 - 102.5 = 2.5
        assert result.iloc[2]["value"] == 2.5

    def test_calculate_consumption_from_readings_with_index(self, calculator):
        """Test consumption calculation with DatetimeIndex"""
        readings = pd.DataFrame(
            {"value": [100.0, 102.5, 105.0]},
            index=pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"),
        )
        readings.index.name = "timestamp"

        result = calculator.calculate_consumption_from_readings(readings)

        assert len(result) == 3
        assert result.iloc[0]["value"] == 0.0  # First day
        assert result.iloc[1]["value"] == 2.5  # Second day

    def test_calculate_consumption_from_readings_negative_values(self, calculator):
        """Test that negative consumption is clipped to zero (meter reset)"""
        # Simulate meter reset
        readings = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC"),
                "value": [100.0, 102.5, 10.0, 12.5],  # Reset from 102.5 to 10.0
            }
        )

        result = calculator.calculate_consumption_from_readings(readings)

        # All consumption values should be non-negative
        assert (result["value"] >= 0).all()
        # Day 3 should be clipped to 0 (not -92.5)
        assert result.iloc[2]["value"] == 0.0

    def test_calculate_consumption_from_readings_empty(self, calculator):
        """Test consumption calculation with empty DataFrame"""
        readings = pd.DataFrame()

        result = calculator.calculate_consumption_from_readings(readings)

        assert result.empty

    def test_calculate_annual_consumption_basic(self, calculator):
        """Test annual consumption calculation"""
        # Year boundary values
        readings = pd.DataFrame(
            {
                "timestamp": [
                    pd.Timestamp("2023-12-31", tz="UTC"),
                    pd.Timestamp("2024-12-31", tz="UTC"),
                ],
                "value": [1000.0, 1500.0],
            }
        )

        consumption = calculator.calculate_annual_consumption(readings, 2024)

        assert consumption == 500.0  # 1500 - 1000

    def test_calculate_annual_consumption_interpolated(self, calculator):
        """Test annual consumption with interpolated boundaries"""
        # Data points around year boundaries
        readings = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-15", periods=12, freq="M", tz="UTC"
                ),
                "value": [100 + i * 10 for i in range(12)],
            }
        )

        consumption = calculator.calculate_annual_consumption(readings, 2024)

        assert consumption >= 0  # Should be non-negative
        assert consumption < 200  # Should be reasonable (< total range)

    def test_calculate_annual_consumption_empty(self, calculator):
        """Test annual consumption with empty data"""
        readings = pd.DataFrame()

        consumption = calculator.calculate_annual_consumption(readings, 2024)

        assert consumption == 0.0

    def test_calculate_annual_consumption_insufficient_data(self, calculator):
        """Test annual consumption with data outside year"""
        readings = pd.DataFrame(
            {"timestamp": [pd.Timestamp("2023-06-01", tz="UTC")], "value": [100.0]}
        )

        consumption = calculator.calculate_annual_consumption(readings, 2024)

        # Should return 0 or minimal value (can't calculate for 2024)
        assert consumption >= 0

    def test_combine_meter_readings_basic(self, calculator):
        """Test combining old and new meter readings"""
        old_dates = pd.date_range("2024-01-01", "2024-06-15", freq="D", tz="UTC")
        old_readings = pd.DataFrame(
            {
                "timestamp": old_dates,
                "value": [100 + i * 0.5 for i in range(len(old_dates))],
            }
        )

        new_dates = pd.date_range("2024-06-15", "2024-12-31", freq="D", tz="UTC")
        new_readings = pd.DataFrame(
            {
                "timestamp": new_dates,
                "value": [0 + i * 0.5 for i in range(len(new_dates))],  # New meter starts at 0
            }
        )

        combined, offset = calculator.combine_meter_readings(
            old_readings, new_readings, "2024-06-15"
        )

        assert not combined.empty
        assert len(combined) > len(old_readings)  # Should include both
        # Values should be continuous (offset applied)
        assert combined["value"].is_monotonic_increasing
        # Offset should be the last old value minus first new value
        last_old = old_readings.iloc[-1]["value"]
        assert abs(offset - last_old) < 0.1

    def test_combine_meter_readings_empty_old(self, calculator):
        """Test combining when old meter has no data"""
        old_readings = pd.DataFrame()
        new_readings = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-06-15", periods=10, freq="D", tz="UTC"
                ),
                "value": range(10),
            }
        )

        combined, offset = calculator.combine_meter_readings(
            old_readings, new_readings, "2024-06-15"
        )

        assert combined is None
        assert offset == 0.0

    def test_combine_meter_readings_empty_new(self, calculator):
        """Test combining when new meter has no data"""
        old_readings = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", periods=10, freq="D", tz="UTC"
                ),
                "value": range(100, 110),
            }
        )
        new_readings = pd.DataFrame()

        combined, offset = calculator.combine_meter_readings(
            old_readings, new_readings, "2024-06-15"
        )

        assert combined is None
        assert offset == 0.0

    def test_combine_meter_readings_no_overlap(self, calculator):
        """Test combining meters with gap at replacement date"""
        old_readings = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", "2024-06-10", freq="D", tz="UTC"
                ),
                "value": range(100, 262),
            }
        )

        new_readings = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-06-20", "2024-12-31", freq="D", tz="UTC"
                ),
                "value": range(0, 195),
            }
        )

        combined, offset = calculator.combine_meter_readings(
            old_readings, new_readings, "2024-06-15"
        )

        assert not combined.empty
        # Should have data from both meters
        assert len(combined) > 0
        # Offset should make new meter continue from old
        assert offset > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
