"""
Unit tests for DataProcessor
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock

import numpy as np
import pandas as pd
import pytest
import yaml

# Add src to path
workflows_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workflows_path))

from src.data_processor import DataProcessor
from src.influx_client import InfluxClient


class TestDataProcessor:
    """Test suite for DataProcessor"""

    @pytest.fixture
    def mock_influx_client(self):
        """Create mock InfluxClient"""
        client = Mock(spec=InfluxClient)
        client.meter_data_cache = {}
        return client

    @pytest.fixture
    def processor(self, mock_influx_client):
        """Create DataProcessor with mock client"""
        return DataProcessor(mock_influx_client)

    def test_initialization(self, processor, mock_influx_client):
        """Test DataProcessor initializes correctly"""
        assert processor.influx_client == mock_influx_client
        assert isinstance(processor.interpolated_series_cache, dict)
        assert processor.high_freq_threshold_medium == 100
        assert processor.high_freq_threshold_very == 1000

    def test_estimate_consumption_rate_insufficient_data(self, processor):
        """Test rate estimation with insufficient data"""
        df = pd.DataFrame(
            {"timestamp": [pd.Timestamp("2024-01-01", tz="UTC")], "value": [100.0]}
        )

        rate, r2, method = processor.estimate_consumption_rate(df)

        assert rate == 0.0
        assert r2 == 0.0
        assert method == "insufficient_data"

    def test_estimate_consumption_rate_linear_data(self, processor):
        """Test rate estimation with linear data"""
        # Create perfect linear data: 2.5 units per day
        timestamps = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
        values = [100 + 2.5 * i for i in range(10)]
        df = pd.DataFrame({"timestamp": timestamps, "value": values})

        rate, r2, method = processor.estimate_consumption_rate(df)

        assert abs(rate - 2.5) < 0.01  # Should be very close to 2.5
        assert r2 > 0.99  # Should have excellent fit
        assert "regression" in method.lower()

    def test_estimate_consumption_rate_noisy_data(self, processor):
        """Test rate estimation with noisy data"""
        np.random.seed(42)
        timestamps = pd.date_range("2024-01-01", periods=30, freq="D", tz="UTC")
        # Base rate of 2.0 with noise
        values = [100 + 2.0 * i + np.random.normal(0, 0.5) for i in range(30)]
        df = pd.DataFrame({"timestamp": timestamps, "value": values})

        rate, r2, method = processor.estimate_consumption_rate(df)

        assert 1.5 < rate < 2.5  # Should be close to 2.0
        assert r2 > 0.7  # Should still have decent fit

    def test_estimate_consumption_rate_zero_rate(self, processor):
        """Test rate estimation with constant value (zero consumption)"""
        timestamps = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
        values = [100.0] * 10  # Constant value
        df = pd.DataFrame({"timestamp": timestamps, "value": values})

        rate, r2, method = processor.estimate_consumption_rate(df)

        assert abs(rate) < 0.01  # Should be approximately zero
        assert r2 >= 0  # R² should be non-negative

    def test_reduce_high_frequency_data_no_reduction_needed(self, processor):
        """Test that low-frequency data is not reduced"""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", periods=50, freq="D", tz="UTC"
                ),
                "value": range(50),
            }
        )

        result = processor.reduce_high_frequency_data(df, "test_meter")

        assert len(result) == len(df)  # No reduction

    def test_reduce_high_frequency_data_medium_density(self, processor):
        """Test reduction of medium density data"""
        # 500 points (> 100 threshold)
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", periods=500, freq="H", tz="UTC"
                ),
                "value": range(500),
            }
        )

        result = processor.reduce_high_frequency_data(df, "test_meter")

        assert len(result) < len(df)  # Should be reduced
        assert result["timestamp"].iloc[0] == df["timestamp"].iloc[0]  # First preserved
        assert (
            result["timestamp"].iloc[-1] == df["timestamp"].iloc[-1]
        )  # Last preserved

    def test_reduce_high_frequency_data_very_dense(self, processor):
        """Test reduction of very dense data"""
        # 2000 points (> 1000 threshold)
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", periods=2000, freq="T", tz="UTC"
                ),
                "value": range(2000),
            }
        )

        result = processor.reduce_high_frequency_data(df, "test_meter")

        assert len(result) <= 55  # Should be close to target (50) + first/last
        assert len(result) >= 45
        assert result["timestamp"].iloc[0] == df["timestamp"].iloc[0]  # First preserved
        assert (
            result["timestamp"].iloc[-1] == df["timestamp"].iloc[-1]
        )  # Last preserved

    def test_aggregate_daily_to_frequency_daily(self, processor):
        """Test that daily data returns unchanged"""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", periods=10, freq="D", tz="UTC"
                ),
                "value": range(10),
            }
        )

        result = processor.aggregate_daily_to_frequency(df, "D")

        pd.testing.assert_frame_equal(result, df)

    def test_aggregate_daily_to_frequency_monthly(self, processor):
        """Test aggregation to monthly frequency"""
        # Create 3 months of daily data
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2024-01-01", periods=90, freq="D", tz="UTC"
                ),
                "value": range(90),
            }
        )

        result = processor.aggregate_daily_to_frequency(df, "M")

        assert len(result) == 3  # Should have 3 months
        assert "timestamp" in result.columns
        assert "value" in result.columns
        # Last value of each month should be preserved
        assert result.iloc[0]["value"] == 30  # Last day of Jan (approx)

    def test_aggregate_daily_to_frequency_empty(self, processor):
        """Test aggregation of empty DataFrame"""
        df = pd.DataFrame()

        result = processor.aggregate_daily_to_frequency(df, "M")

        assert result.empty


class TestDataProcessorIntegration:
    """Integration tests for create_standardized_daily_series"""

    @pytest.fixture
    def mock_influx_client_with_data(self):
        """Create mock client with test data"""
        client = Mock(spec=InfluxClient)
        client.meter_data_cache = {}

        # Mock fetch method to return test data
        def mock_fetch(entity_id, start_date=None):
            # Return sparse data (readings every 5 days)
            timestamps = pd.date_range("2024-01-01", "2024-01-31", freq="5D", tz="UTC")
            values = [100 + 2.5 * i for i in range(len(timestamps))]
            return pd.DataFrame({"timestamp": timestamps, "value": values})

        client.fetch_all_meter_data = Mock(side_effect=mock_fetch)
        return client

    def test_create_standardized_daily_series_basic(self, mock_influx_client_with_data):
        """Test basic daily series creation"""
        processor = DataProcessor(mock_influx_client_with_data)

        result = processor.create_standardized_daily_series(
            "test_meter",
            "2024-01-01",
            "2024-01-31",
            installation_date="2024-01-01",  # Required parameter
        )

        assert not result.empty
        assert "timestamp" in result.columns
        assert "value" in result.columns
        assert len(result) == 31  # Should have exactly 31 daily points
        # Values should be monotonically increasing
        assert result["value"].is_monotonic_increasing

    def test_create_standardized_daily_series_with_installation_date(
        self, mock_influx_client_with_data
    ):
        """Test series creation respects installation date"""
        processor = DataProcessor(mock_influx_client_with_data)

        result = processor.create_standardized_daily_series(
            "test_meter",
            "2024-01-01",
            "2024-01-31",
            installation_date="2024-01-10",  # Meter installed mid-month
        )

        assert not result.empty
        # Should start from installation date or later
        assert result["timestamp"].min() >= pd.Timestamp("2024-01-10", tz="UTC")

    def test_create_standardized_daily_series_caching(
        self, mock_influx_client_with_data
    ):
        """Test that results are cached"""
        processor = DataProcessor(mock_influx_client_with_data)

        # First call
        result1 = processor.create_standardized_daily_series(
            "test_meter",
            "2024-01-01",
            "2024-01-31",
            installation_date="2024-01-01",  # Required parameter
        )

        # Second call with same parameters
        result2 = processor.create_standardized_daily_series(
            "test_meter",
            "2024-01-01",
            "2024-01-31",
            installation_date="2024-01-01",  # Required parameter
        )

        # Should be cached - fetch should only be called once
        assert mock_influx_client_with_data.fetch_all_meter_data.call_count == 1
        pd.testing.assert_frame_equal(result1, result2)

    def test_missing_installation_date_raises_error(self, mock_influx_client_with_data):
        """Test that missing installation_date raises ValueError"""
        processor = DataProcessor(mock_influx_client_with_data)

        with pytest.raises(ValueError, match="missing required installation_date"):
            processor.create_standardized_daily_series(
                "test_meter",
                "2024-01-01",
                "2024-01-31",
                installation_date=None,  # Missing - should raise error
            )

    def test_seasonal_pattern_loading(self, mock_influx_client):
        """Test that seasonal patterns are loaded correctly"""
        # Create a temporary seasonal patterns file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            patterns = {
                "patterns": {
                    "test_meter": {
                        "monthly_percentages": [
                            10,
                            10,
                            10,
                            8,
                            7,
                            6,
                            6,
                            6,
                            7,
                            8,
                            11,
                            11,
                        ],
                        "description": "Test pattern",
                    }
                }
            }
            yaml.dump(patterns, f)
            temp_path = f.name

        try:
            processor = DataProcessor(
                mock_influx_client, seasonal_patterns_path=temp_path
            )

            assert "test_meter" in processor.seasonal_patterns
            assert len(processor.seasonal_patterns["test_meter"]) == 12
            # Should normalize to 100%
            assert abs(sum(processor.seasonal_patterns["test_meter"]) - 100.0) < 0.01
        finally:
            os.unlink(temp_path)

    def test_seasonal_distribution(self, mock_influx_client):
        """Test seasonal consumption distribution"""
        # Create seasonal pattern (winter-heavy)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            patterns = {
                "patterns": {
                    "test_meter": {
                        "monthly_percentages": [
                            15,
                            12,
                            10,
                            8,
                            5,
                            4,
                            4,
                            4,
                            5,
                            8,
                            12,
                            13,
                        ],
                        "description": "Winter-heavy pattern",
                    }
                }
            }
            yaml.dump(patterns, f)
            temp_path = f.name

        try:
            processor = DataProcessor(
                mock_influx_client, seasonal_patterns_path=temp_path
            )

            # Test distribution for January (should be higher than June)
            result = processor._distribute_consumption_by_seasonal_pattern(
                start_timestamp=pd.Timestamp("2024-01-01", tz="UTC"),
                end_timestamp=pd.Timestamp("2024-02-01", tz="UTC"),
                total_consumption=100.0,
                seasonal_pattern=processor.seasonal_patterns["test_meter"],
                start_value=0.0,
            )

            assert not result.empty
            assert "timestamp" in result.columns
            assert "value" in result.columns
            # Values should be cumulative and monotonically increasing
            assert result["value"].is_monotonic_increasing
            # Final value should equal total consumption
            assert abs(result["value"].iloc[-1] - 100.0) < 0.01
        finally:
            os.unlink(temp_path)

    def test_forward_extrapolation_with_seasonal_pattern(self, mock_influx_client):
        """Test that forward extrapolation uses seasonal patterns for long gaps"""
        # Create seasonal pattern
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            patterns = {
                "patterns": {
                    "test_meter": {
                        "monthly_percentages": [
                            10,
                            10,
                            10,
                            8,
                            7,
                            6,
                            6,
                            6,
                            7,
                            8,
                            11,
                            11,
                        ],
                        "description": "Test pattern",
                    }
                }
            }
            yaml.dump(patterns, f)
            temp_path = f.name

        try:
            # Mock fetch to return data ending 30 days ago
            def mock_fetch(entity_id, start_date=None):
                timestamps = pd.date_range(
                    "2024-01-01", "2024-01-10", freq="2D", tz="UTC"
                )
                values = [100 + 2 * i for i in range(len(timestamps))]
                return pd.DataFrame({"timestamp": timestamps, "value": values})

            mock_influx_client.fetch_all_meter_data = Mock(side_effect=mock_fetch)
            mock_influx_client.meter_data_cache = {}

            processor = DataProcessor(
                mock_influx_client, seasonal_patterns_path=temp_path
            )

            result = processor.create_standardized_daily_series(
                "test_meter",
                "2024-01-01",
                "2024-02-15",  # 35+ days after last reading
                installation_date="2024-01-01",
            )

            assert not result.empty
            # Should have data up to end date
            assert result["timestamp"].max() >= pd.Timestamp("2024-02-15", tz="UTC")
            # Should use seasonal pattern for forward extrapolation
            assert len(result) > 10  # More than just raw data points
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
