"""
Live Integration Tests for Dagster
Tests that interact with actual running Dagster instance via GraphQL API
"""

import os
import time
from typing import Any, Dict, Optional

import pytest
import requests

# Get Dagster URL from environment or use default
DAGSTER_URL = os.getenv("DAGSTER_TEST_URL", "http://localhost:3000")
DAGSTER_GRAPHQL_URL = f"{DAGSTER_URL}/graphql"


def execute_graphql(
    query: str, variables: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a GraphQL query against Dagster
    """
    response = requests.post(
        DAGSTER_GRAPHQL_URL, json={"query": query, "variables": variables or {}}
    )
    response.raise_for_status()
    return response.json()


def wait_for_run_completion(run_id: str, timeout: int = 300) -> str:
    """
    Wait for a Dagster run to complete and return final status
    """
    query = """
    query GetRunStatus($runId: ID!) {
        runOrError(runId: $runId) {
            ... on Run {
                status
                stats {
                    stepsSucceeded
                    stepsFailed
                }
            }
        }
    }
    """

    start_time = time.time()
    while time.time() - start_time < timeout:
        result = execute_graphql(query, {"runId": run_id})

        run_data = result.get("data", {}).get("runOrError", {})
        status = run_data.get("status")

        if status in ["SUCCESS", "FAILURE", "CANCELED"]:
            return status

        time.sleep(2)

    raise TimeoutError(f"Run {run_id} did not complete within {timeout} seconds")


@pytest.mark.integration
@pytest.mark.live
class TestDagsterConnection:
    """Test connectivity to Dagster instance"""

    def test_dagster_is_reachable(self):
        """Test that Dagster webserver is accessible"""
        response = requests.get(DAGSTER_URL)
        assert response.status_code == 200

    def test_graphql_endpoint_works(self):
        """Test that GraphQL endpoint is functional"""
        query = """
        query {
            __schema {
                types {
                    name
                }
            }
        }
        """
        result = execute_graphql(query)
        assert "data" in result
        assert "__schema" in result["data"]

    def test_repository_is_loaded(self):
        """Test that our utility repository is loaded"""
        query = """
        query {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        name
                        location {
                            name
                        }
                    }
                }
            }
        }
        """
        result = execute_graphql(query)
        repos = result["data"]["repositoriesOrError"]["nodes"]
        assert len(repos) > 0


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.slow
class TestAssetMaterialization:
    """Test asset materialization via GraphQL"""

    def test_list_all_assets(self):
        """Test listing all available assets"""
        query = """
        query {
            assetsOrError {
                ... on AssetConnection {
                    nodes {
                        key {
                            path
                        }
                    }
                }
            }
        }
        """
        result = execute_graphql(query)
        assets = result["data"]["assetsOrError"]["nodes"]

        # Verify our expected assets exist
        asset_keys = [asset["key"]["path"] for asset in assets]

        # Check for key assets (note: fetch_meter_data outputs raw_meter_data)
        expected_assets = [
            ["tibber_consumption_raw"],
            ["meter_discovery"],
            ["raw_meter_data"],  # Output from fetch_meter_data
            ["daily_interpolated_series"],  # Output from interpolated_meter_series
            ["monthly_interpolated_series"],  # Output from interpolated_meter_series
            ["consumption_data"],
            ["virtual_meter_data"],
            ["anomaly_detection"],
        ]

        for expected in expected_assets:
            assert (
                expected in asset_keys
            ), f"Asset {expected} not found. Available: {asset_keys}"

    @pytest.mark.skip(reason="Requires real InfluxDB and Tibber credentials")
    def test_materialize_tibber_asset(self):
        """Test materializing Tibber ingestion asset"""
        query = """
        mutation LaunchRun($assetKeys: [AssetKeyInput!]!) {
            launchPipelineExecution(
                executionParams: {
                    mode: "default"
                    selector: {
                        assetKeys: $assetKeys
                    }
                }
            ) {
                ... on LaunchRunSuccess {
                    run {
                        runId
                        status
                    }
                }
                ... on PythonError {
                    message
                }
            }
        }
        """

        variables = {"assetKeys": [{"path": ["tibber_consumption_raw"]}]}

        result = execute_graphql(query, variables)
        launch_result = result["data"]["launchPipelineExecution"]

        # Check if launch was successful
        if "run" in launch_result:
            run_id = launch_result["run"]["runId"]
            status = wait_for_run_completion(run_id)
            assert status == "SUCCESS", f"Run failed with status: {status}"
        else:
            pytest.fail(f"Failed to launch run: {launch_result.get('message')}")


@pytest.mark.integration
@pytest.mark.live
class TestJobExecution:
    """Test job execution via GraphQL"""

    def test_list_jobs(self):
        """Test listing all available jobs"""
        query = """
        query {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        name
                        pipelines {
                            name
                            isJob
                        }
                    }
                }
            }
        }
        """
        result = execute_graphql(query)
        repos = result["data"]["repositoriesOrError"]["nodes"]

        # Find jobs
        all_jobs = []
        for repo in repos:
            jobs = [p["name"] for p in repo["pipelines"] if p["isJob"]]
            all_jobs.extend(jobs)

        # Verify our expected jobs exist (actual job names from repository)
        assert (
            "tibber_sync" in all_jobs
        ), f"tibber_sync job not found. Available: {all_jobs}"
        assert (
            "analytics_processing" in all_jobs
        ), f"analytics_processing job not found. Available: {all_jobs}"

    @pytest.mark.skip(reason="Requires real data sources")
    def test_execute_analytics_job(self):
        """Test executing the full analytics job"""
        query = """
        mutation LaunchJob($jobName: String!) {
            launchPipelineExecution(
                executionParams: {
                    mode: "default"
                    selector: {
                        pipelineName: $jobName
                    }
                }
            ) {
                ... on LaunchRunSuccess {
                    run {
                        runId
                        status
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
            }
        }
        """

        variables = {"jobName": "analytics"}

        result = execute_graphql(query, variables)
        launch_result = result["data"]["launchPipelineExecution"]

        if "run" in launch_result:
            run_id = launch_result["run"]["runId"]
            status = wait_for_run_completion(run_id, timeout=600)  # 10 min timeout
            assert status == "SUCCESS", f"Analytics job failed with status: {status}"
        else:
            pytest.fail(f"Failed to launch job: {launch_result.get('message')}")


@pytest.mark.integration
@pytest.mark.live
class TestSchedules:
    """Test schedule configuration"""

    def test_list_schedules(self):
        """Test listing all configured schedules"""
        query = """
        query {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        name
                        schedules {
                            name
                            cronSchedule
                            pipelineName
                        }
                    }
                }
            }
        }
        """
        result = execute_graphql(query)
        repos = result["data"]["repositoriesOrError"]["nodes"]

        # Find schedules
        all_schedules = []
        for repo in repos:
            all_schedules.extend(repo["schedules"])

        # Verify our expected schedules exist (actual schedule names from repository)
        schedule_names = [s["name"] for s in all_schedules]
        assert (
            "tibber_sync_hourly" in schedule_names
        ), f"tibber_sync_hourly schedule not found. Available: {schedule_names}"
        assert (
            "analytics_daily" in schedule_names
        ), f"analytics_daily schedule not found. Available: {schedule_names}"

        # Verify cron expressions
        for schedule in all_schedules:
            if "hourly" in schedule["name"].lower():
                # Hourly schedules run every hour (e.g., "5 * * * *" or "0 * * * *")
                assert (
                    "* * * *" in schedule["cronSchedule"]
                ), f"Hourly schedule has wrong cron: {schedule['cronSchedule']}"
            elif "daily" in schedule["name"].lower():
                # Daily schedules should run once per day at 2 AM
                assert (
                    "0 2 * * *" in schedule["cronSchedule"]
                ), f"Daily schedule has wrong cron: {schedule['cronSchedule']}"


@pytest.mark.integration
@pytest.mark.live
class TestResources:
    """Test resource configuration"""

    def test_resources_are_configured(self):
        """Test that resources are properly configured"""
        query = """
        query {
            repositoriesOrError {
                ... on RepositoryConnection {
                    nodes {
                        name
                        allTopLevelResourceDetails {
                            name
                            description
                        }
                    }
                }
            }
        }
        """
        result = execute_graphql(query)
        repos = result["data"]["repositoriesOrError"]["nodes"]

        # Find resources
        all_resources = []
        for repo in repos:
            all_resources.extend(repo["allTopLevelResourceDetails"])

        resource_names = [r["name"] for r in all_resources]

        # Verify our expected resources are configured
        expected_resources = ["influxdb", "tibber", "config"]
        for expected in expected_resources:
            assert expected in resource_names, f"Resource {expected} not found"


@pytest.mark.integration
@pytest.mark.live
class TestHealthChecks:
    """Test system health and monitoring"""

    def test_daemon_health(self):
        """Test that Dagster daemon is healthy"""
        query = """
        query {
            instance {
                daemonHealth {
                    allDaemonStatuses {
                        daemonType
                        healthy
                        required
                    }
                }
            }
        }
        """
        result = execute_graphql(query)
        daemon_statuses = result["data"]["instance"]["daemonHealth"][
            "allDaemonStatuses"
        ]

        # Check that required daemons are healthy
        for daemon in daemon_statuses:
            if daemon["required"]:
                assert daemon[
                    "healthy"
                ], f"Required daemon {daemon['daemonType']} is not healthy"

    def test_code_location_health(self):
        """Test that code location is loaded and healthy"""
        query = """
        query {
            workspaceOrError {
                ... on Workspace {
                    locationEntries {
                        name
                        locationOrLoadError {
                            ... on RepositoryLocation {
                                name
                                repositories {
                                    name
                                }
                            }
                            ... on PythonError {
                                message
                            }
                        }
                    }
                }
            }
        }
        """
        result = execute_graphql(query)
        workspace = result["data"]["workspaceOrError"]
        locations = workspace["locationEntries"]

        assert len(locations) > 0, "No code locations found"

        # Verify locations are loaded without errors
        for location in locations:
            location_data = location["locationOrLoadError"]
            assert (
                "repositories" in location_data
            ), f"Location {location['name']} failed to load"
