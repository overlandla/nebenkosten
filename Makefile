.PHONY: help install-dashboard update-dashboard configure-dashboard install-dagster update-dagster

help:
	@echo "Nebenkosten Installation Targets"
	@echo "================================="
	@echo ""
	@echo "Dashboard:"
	@echo "  make install-dashboard    - Install Utility Meter Dashboard"
	@echo "  make update-dashboard     - Update Dashboard to latest version"
	@echo "  make configure-dashboard  - Reconfigure database credentials"
	@echo ""
	@echo "Dagster Workflows:"
	@echo "  make install-dagster      - Install Dagster Workflows"
	@echo "  make update-dagster       - Update Dagster to latest version"
	@echo ""

install-dashboard:
	@echo "[INFO] Installing Utility Meter Dashboard..."
	@echo "[INFO] Installing system dependencies..."
	@apt-get update -qq
	@apt-get install -y -qq curl sudo mc git rsync
	@echo "[INFO] Installing Node.js v20 LTS..."
	@curl -fsSL https://deb.nodesource.com/setup_20.x | bash >/dev/null 2>&1
	@apt-get install -y -qq nodejs
	@echo "[INFO] Setting up Dashboard..."
	@mkdir -p /opt/utility-meter-dashboard
	@rsync -a --exclude='.git' --exclude='node_modules' --exclude='.next' \
		$(CURDIR)/dashboard/ /opt/utility-meter-dashboard/
	@echo ""
	@echo "[INFO] Configuring database connections..."
	@echo "Please provide the following connection details:"
	@echo ""
	@read -p "InfluxDB URL (e.g., http://192.168.1.75:8086): " INFLUX_URL; \
	read -p "InfluxDB Token: " INFLUX_TOKEN; \
	read -p "InfluxDB Organization: " INFLUX_ORG; \
	read -p "InfluxDB Raw Bucket [homeassistant_raw]: " INFLUX_BUCKET_RAW; \
	INFLUX_BUCKET_RAW=$${INFLUX_BUCKET_RAW:-homeassistant_raw}; \
	read -p "InfluxDB Processed Bucket [homeassistant_processed]: " INFLUX_BUCKET_PROCESSED; \
	INFLUX_BUCKET_PROCESSED=$${INFLUX_BUCKET_PROCESSED:-homeassistant_processed}; \
	read -p "PostgreSQL Config DB URL (e.g., postgresql://user:pass@host:5432/db): " CONFIG_DATABASE_URL; \
	printf '%s\n' \
		"# InfluxDB Configuration" \
		"INFLUX_URL=$$INFLUX_URL" \
		"INFLUX_TOKEN=$$INFLUX_TOKEN" \
		"INFLUX_ORG=$$INFLUX_ORG" \
		"INFLUX_BUCKET_RAW=$$INFLUX_BUCKET_RAW" \
		"INFLUX_BUCKET_PROCESSED=$$INFLUX_BUCKET_PROCESSED" \
		"" \
		"# PostgreSQL Configuration Database" \
		"CONFIG_DATABASE_URL=$$CONFIG_DATABASE_URL" \
		> /opt/utility-meter-dashboard/.env.local
	@echo ""
	@echo "[INFO] Configuration saved to /opt/utility-meter-dashboard/.env.local"
	@cd /opt/utility-meter-dashboard && npm install >/dev/null 2>&1
	@cd /opt/utility-meter-dashboard && npm run build >/dev/null 2>&1
	@echo "[INFO] Creating systemd service..."
	@printf '%s\n' \
		'[Unit]' \
		'Description=Utility Meter Dashboard' \
		'After=network.target' \
		'' \
		'[Service]' \
		'Type=simple' \
		'User=root' \
		'WorkingDirectory=/opt/utility-meter-dashboard' \
		'ExecStart=/usr/bin/npm start' \
		'Restart=on-failure' \
		'Environment=NODE_ENV=production' \
		'Environment=PORT=3000' \
		'' \
		'[Install]' \
		'WantedBy=multi-user.target' \
		> /etc/systemd/system/utility-meter-dashboard.service
	@systemctl daemon-reload
	@systemctl enable utility-meter-dashboard >/dev/null 2>&1
	@systemctl start utility-meter-dashboard
	@sleep 2
	@echo ""
	@echo "✓ Dashboard installed successfully!"
	@echo "  Access at: http://$$(hostname -I | awk '{print $$1}'):3000"
	@echo ""

update-dashboard:
	@echo "[INFO] Updating Utility Meter Dashboard..."
	@echo "[INFO] Pulling latest code..."
	@git pull origin main
	@echo "[INFO] Stopping service..."
	@systemctl stop utility-meter-dashboard || true
	@echo "[INFO] Updating files..."
	@rsync -a --exclude='.git' --exclude='node_modules' --exclude='.next' --exclude='.env.local' \
		$(CURDIR)/dashboard/ /opt/utility-meter-dashboard/
	@if [ ! -f /opt/utility-meter-dashboard/.env.local ]; then \
		echo "[WARN] No .env.local found. Run 'make configure-dashboard' to set up database credentials."; \
	fi
	@cd /opt/utility-meter-dashboard && npm install >/dev/null 2>&1
	@cd /opt/utility-meter-dashboard && npm run build >/dev/null 2>&1
	@echo "[INFO] Starting service..."
	@systemctl start utility-meter-dashboard
	@sleep 2
	@echo ""
	@echo "✓ Dashboard updated successfully!"
	@echo "  Access at: http://$$(hostname -I | awk '{print $$1}'):3000"
	@echo ""

configure-dashboard:
	@echo "[INFO] Configuring Dashboard database connections..."
	@if [ ! -d /opt/utility-meter-dashboard ]; then \
		echo "[ERROR] Dashboard not installed. Run 'make install-dashboard' first."; \
		exit 1; \
	fi
	@echo ""
	@echo "Please provide the following connection details:"
	@echo ""
	@read -p "InfluxDB URL (e.g., http://192.168.1.75:8086): " INFLUX_URL; \
	read -p "InfluxDB Token: " INFLUX_TOKEN; \
	read -p "InfluxDB Organization: " INFLUX_ORG; \
	read -p "InfluxDB Raw Bucket [homeassistant_raw]: " INFLUX_BUCKET_RAW; \
	INFLUX_BUCKET_RAW=$${INFLUX_BUCKET_RAW:-homeassistant_raw}; \
	read -p "InfluxDB Processed Bucket [homeassistant_processed]: " INFLUX_BUCKET_PROCESSED; \
	INFLUX_BUCKET_PROCESSED=$${INFLUX_BUCKET_PROCESSED:-homeassistant_processed}; \
	read -p "PostgreSQL Config DB URL (e.g., postgresql://user:pass@host:5432/db): " CONFIG_DATABASE_URL; \
	printf '%s\n' \
		"# InfluxDB Configuration" \
		"INFLUX_URL=$$INFLUX_URL" \
		"INFLUX_TOKEN=$$INFLUX_TOKEN" \
		"INFLUX_ORG=$$INFLUX_ORG" \
		"INFLUX_BUCKET_RAW=$$INFLUX_BUCKET_RAW" \
		"INFLUX_BUCKET_PROCESSED=$$INFLUX_BUCKET_PROCESSED" \
		"" \
		"# PostgreSQL Configuration Database" \
		"CONFIG_DATABASE_URL=$$CONFIG_DATABASE_URL" \
		> /opt/utility-meter-dashboard/.env.local
	@echo ""
	@echo "[INFO] Configuration saved. Restarting dashboard..."
	@systemctl restart utility-meter-dashboard
	@echo "✓ Dashboard reconfigured successfully!"
	@echo ""

install-dagster:
	@echo "[INFO] Installing Dagster Workflows (systemd native deployment)..."
	@bash workflows_dagster/install/dagster-workflows-install.sh

update-dagster:
	@echo "[INFO] Updating Dagster Workflows..."
	@bash workflows_dagster/install/dagster-workflows-install.sh
