"""
Anomaly Alert Sensor
Monitors anomaly detection results and alerts on significant findings
"""
from dagster import (
    sensor,
    RunRequest,
    SensorEvaluationContext,
    AssetMaterialization,
    DefaultSensorStatus,
    DagsterEventType
)
import logging


@sensor(
    name="anomaly_alert_sensor",
    asset_selection=["anomaly_detection"],
    minimum_interval_seconds=3600,  # Check every hour
    default_status=DefaultSensorStatus.RUNNING
)
def anomaly_alert_sensor(context: SensorEvaluationContext):
    """
    Monitors anomaly detection asset for new findings

    When anomalies are detected:
    - Logs summary of anomalies by meter
    - Could trigger alerts if anomaly count exceeds threshold
    - Could generate a report job

    Args:
        context: Sensor evaluation context with event logs

    Yields:
        RunRequest if anomaly threshold exceeded (optional)
    """
    # Get recent materialization events for anomaly_detection asset
    events = context.instance.get_latest_materialization_event(
        asset_key=["anomaly_detection"]
    )

    if not events:
        context.log.debug("No anomaly detection materializations found")
        return

    # Extract metadata from the latest materialization
    if hasattr(events, 'asset_materialization') and events.asset_materialization:
        metadata = events.asset_materialization.metadata
        
        # Check if we have anomaly counts in metadata
        if metadata:
            total_anomalies = 0
            anomaly_meters = []
            
            for key, value in metadata.items():
                if 'anomaly' in key.lower() or 'count' in key.lower():
                    context.log.info(f"Anomaly metadata: {key} = {value}")
                    
            # TODO: Parse actual anomaly data
            # For now, log that we checked
            context.log.info(
                f"Anomaly detection sensor checked at {context.cursor}. "
                f"Materialization: {events.timestamp}"
            )

    # Example: Trigger alert job if anomalies exceed threshold
    # THRESHOLD = 10
    # if total_anomalies > THRESHOLD:
    #     context.log.warning(
    #         f"High anomaly count detected: {total_anomalies} anomalies "
    #         f"across {len(anomaly_meters)} meters"
    #     )
    #     
    #     # Could yield a RunRequest to trigger notification job
    #     # yield RunRequest(
    #     #     run_key=f"anomaly_alert_{context.cursor}",
    #     #     job_name="send_anomaly_report"
    #     # )

    # For production: send alerts
    # anomaly_webhook = os.getenv("ANOMALY_ALERT_WEBHOOK")
    # if anomaly_webhook and total_anomalies > THRESHOLD:
    #     import requests
    #     requests.post(anomaly_webhook, json={
    #         "alert": "High consumption anomalies detected",
    #         "count": total_anomalies,
    #         "meters": anomaly_meters,
    #         "timestamp": events.timestamp
    #     })
