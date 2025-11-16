"""
Failure Sensor for Analytics Pipeline
Monitors for failed runs and sends alerts
"""

import logging

from dagster import (
    DefaultSensorStatus,
    RunFailureSensorContext,
    RunRequest,
    run_failure_sensor,
    sensor,
)

from ..jobs import analytics_job


@run_failure_sensor(
    name="analytics_failure_sensor",
    monitored_jobs=[analytics_job],
    default_status=DefaultSensorStatus.RUNNING,
)
def analytics_failure_sensor(context: RunFailureSensorContext):
    """
    Monitors analytics job for failures and logs alerts

    In production, this could:
    - Send emails via SMTP
    - Post to Slack/Discord webhooks
    - Create PagerDuty incidents
    - Write to a monitoring system

    For now, it logs detailed failure information.
    """
    run_id = context.dagster_run.run_id
    job_name = context.dagster_run.job_name

    # Extract failure information
    failure_event = context.failure_event
    if failure_event:
        error_message = (
            str(failure_event.message)
            if hasattr(failure_event, "message")
            else "Unknown error"
        )
        step_key = (
            failure_event.step_key
            if hasattr(failure_event, "step_key")
            else "Unknown step"
        )
    else:
        error_message = "No failure event details available"
        step_key = "Unknown"

    # Log the failure
    logging.error(
        f"⚠️  ANALYTICS PIPELINE FAILURE\n"
        f"   Run ID: {run_id}\n"
        f"   Job: {job_name}\n"
        f"   Failed Step: {step_key}\n"
        f"   Error: {error_message}\n"
        f"   Timestamp: {context.dagster_run.create_timestamp}\n"
    )

    # TODO: Add alert integrations here
    # Examples:
    # - send_email(to="ops@example.com", subject="Analytics Pipeline Failed", body=...)
    # - post_to_slack(webhook_url, message=...)
    # - create_pagerduty_incident(...)

    # For Slack integration (when webhook configured):
    # slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    # if slack_webhook:
    #     import requests
    #     requests.post(slack_webhook, json={
    #         "text": f"🚨 Analytics pipeline failed: {error_message}",
    #         "attachments": [{
    #             "color": "danger",
    #             "fields": [
    #                 {"title": "Job", "value": job_name, "short": True},
    #                 {"title": "Run ID", "value": run_id, "short": True},
    #                 {"title": "Failed Step", "value": step_key, "short": False},
    #                 {"title": "Error", "value": error_message, "short": False}
    #             ]
    #         }]
    #     })

    # Return nothing - this sensor only observes, doesn't trigger new runs
    return
