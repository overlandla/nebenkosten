#!/bin/bash
# Setup script for Tibber sync cron job

# 1. Create directories
sudo mkdir -p /opt/tibber-sync
sudo mkdir -p /var/log
sudo mkdir -p /var/lib

# 2. Copy the Python script
sudo cp tibber_influxdb_sync.py /opt/tibber-sync/
sudo chmod +x /opt/tibber-sync/tibber_influxdb_sync.py

# 3. Install Python dependencies
pip3 install requests influxdb-client

# 4. Create a wrapper script for better cron execution
sudo tee /opt/tibber-sync/run_sync.sh > /dev/null << 'EOF'
#!/bin/bash
# Wrapper script for Tibber sync

# Set PATH for cron
export PATH="/usr/local/bin:/usr/bin:/bin"

# Change to script directory
cd /opt/tibber-sync

# Run with Python3 and log output
/usr/bin/python3 tibber_influxdb_sync.py >> /var/log/tibber_sync.log 2>&1

# Log exit code
echo "$(date): Sync completed with exit code $?" >> /var/log/tibber_sync.log
EOF

sudo chmod +x /opt/tibber-sync/run_sync.sh

# 5. Create logrotate configuration
sudo tee /etc/logrotate.d/tibber-sync > /dev/null << 'EOF'
/var/log/tibber_sync.log {
    daily
    rotate 7
    compress
    missingok
    create 0644 root root
}
EOF

# 6. Add cron job (runs every hour at minute 5)
echo "5 * * * * /opt/tibber-sync/run_sync.sh" | sudo crontab -

echo "✅ Tibber sync cron job setup completed!"
echo "📝 Logs will be written to /var/log/tibber_sync.log"
echo "⏰ Sync will run every hour at 5 minutes past the hour"
echo "🔍 State will be tracked in /var/lib/tibber_sync_state.json"

# 7. Test the setup
echo "🧪 Running initial test..."
sudo /opt/tibber-sync/run_sync.sh
echo "📋 Check /var/log/tibber_sync.log for results"

# ============================================================================
# Alternative: Systemd Service + Timer (more robust than cron)
# ============================================================================

# Create systemd service
sudo tee /etc/systemd/system/tibber-sync.service > /dev/null << 'EOF'
[Unit]
Description=Tibber InfluxDB Sync Service
After=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/opt/tibber-sync
ExecStart=/usr/bin/python3 /opt/tibber-sync/tibber_influxdb_sync.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer
sudo tee /etc/systemd/system/tibber-sync.timer > /dev/null << 'EOF'
[Unit]
Description=Run Tibber InfluxDB Sync every hour
Requires=tibber-sync.service

[Timer]
OnCalendar=*:05:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start the timer (uncomment to use systemd instead of cron)
# sudo systemctl daemon-reload
# sudo systemctl enable tibber-sync.timer
# sudo systemctl start tibber-sync.timer
# sudo systemctl status tibber-sync.timer

echo ""
echo "🔧 Systemd service files created but not enabled."
echo "To use systemd instead of cron:"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable tibber-sync.timer"
echo "  sudo systemctl start tibber-sync.timer"
echo "  sudo systemctl status tibber-sync.timer"