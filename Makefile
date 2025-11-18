SHELL := /bin/bash

.PHONY: help install-dashboard update-dashboard configure-dashboard dashboard-connection-test install-dagster update-dagster

help:
	@echo "Nebenkosten Installation Targets"
	@echo "================================="
	@echo ""
	@echo "Dashboard:"
	@echo "  make install-dashboard        - Install Utility Meter Dashboard"
	@echo "  make update-dashboard         - Update Dashboard to latest version"
	@echo "  make configure-dashboard      - Reconfigure database credentials"
	@echo "  make dashboard-connection-test - Test InfluxDB and PostgreSQL connectivity"
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
	echo ""; \
	echo "[INFO] PostgreSQL Configuration Database Setup"; \
	echo "If you installed Dagster using 'make install-dagster', it created a PostgreSQL database with:"; \
	echo "  - Host: IP address of the Dagster LXC (e.g., 192.168.1.94)"; \
	echo "  - Port: 5432"; \
	echo "  - Database: nebenkosten_config"; \
	echo "  - Username: dagster"; \
	echo "  - Password: dagster"; \
	echo ""; \
	echo "Connection string format: postgresql://dagster:dagster@DAGSTER_IP:5432/nebenkosten_config"; \
	echo "Example: postgresql://dagster:dagster@192.168.1.94:5432/nebenkosten_config"; \
	echo ""; \
	read -p "PostgreSQL Config DB URL: " CONFIG_DATABASE_URL; \
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
	fi || true
	@echo "[INFO] Installing dependencies..."
	@cd /opt/utility-meter-dashboard && npm install >/dev/null 2>&1 || { echo "[ERROR] npm install failed"; exit 1; }
	@echo "[INFO] Building dashboard..."
	@cd /opt/utility-meter-dashboard && \
		npm run build 2>&1 | tee /tmp/dashboard-build.log | grep -E "(error|Error|ERROR|✓|✗)" || true; \
		if [ $${PIPESTATUS[0]} -ne 0 ]; then \
			echo "[ERROR] Build failed. Check /tmp/dashboard-build.log for details"; \
			tail -50 /tmp/dashboard-build.log; \
			exit 1; \
		fi
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
	echo ""; \
	echo "[INFO] PostgreSQL Configuration Database Setup"; \
	echo "If you installed Dagster using 'make install-dagster', it created a PostgreSQL database with:"; \
	echo "  - Host: IP address of the Dagster LXC (e.g., 192.168.1.94)"; \
	echo "  - Port: 5432"; \
	echo "  - Database: nebenkosten_config"; \
	echo "  - Username: dagster"; \
	echo "  - Password: dagster"; \
	echo ""; \
	echo "Connection string format: postgresql://dagster:dagster@DAGSTER_IP:5432/nebenkosten_config"; \
	echo "Example: postgresql://dagster:dagster@192.168.1.94:5432/nebenkosten_config"; \
	echo ""; \
	read -p "PostgreSQL Config DB URL: " CONFIG_DATABASE_URL; \
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

dashboard-connection-test:
	@echo "[INFO] Testing Dashboard database connections..."
	@if [ ! -d /opt/utility-meter-dashboard ]; then \
		echo "[ERROR] Dashboard not installed. Run 'make install-dashboard' first."; \
		exit 1; \
	fi
	@if [ ! -f /opt/utility-meter-dashboard/.env.local ]; then \
		echo "[ERROR] Configuration file not found. Run 'make configure-dashboard' first."; \
		exit 1; \
	fi
	@echo ""
	@echo "Loading configuration from /opt/utility-meter-dashboard/.env.local..."
	@echo ""
	@bash -c ' \
		set -a; \
		source /opt/utility-meter-dashboard/.env.local 2>/dev/null || { echo "[ERROR] Failed to load .env.local"; exit 1; }; \
		set +a; \
		echo "=== Testing InfluxDB Connection ==="; \
		echo "URL: $$INFLUX_URL"; \
		echo "Organization: $$INFLUX_ORG"; \
		echo ""; \
		if [ -z "$$INFLUX_URL" ]; then \
			echo "[ERROR] INFLUX_URL not set in .env.local"; \
			exit 1; \
		fi; \
		if [ -z "$$INFLUX_TOKEN" ]; then \
			echo "[ERROR] INFLUX_TOKEN not set in .env.local"; \
			exit 1; \
		fi; \
		echo "Testing health endpoint..."; \
		if curl -s -f -o /dev/null -w "%{http_code}" "$$INFLUX_URL/health" | grep -q "200"; then \
			echo "✓ InfluxDB health check: OK"; \
		else \
			echo "✗ InfluxDB health check: FAILED"; \
			echo "  Please verify INFLUX_URL is correct and InfluxDB is running"; \
			exit 1; \
		fi; \
		echo ""; \
		echo "Testing authentication and buckets..."; \
		BUCKETS_RESPONSE=$$(curl -s -H "Authorization: Token $$INFLUX_TOKEN" "$$INFLUX_URL/api/v2/buckets?org=$$INFLUX_ORG" 2>/dev/null); \
		if echo "$$BUCKETS_RESPONSE" | grep -q "\"buckets\""; then \
			echo "✓ InfluxDB authentication: OK"; \
			if echo "$$BUCKETS_RESPONSE" | grep -q "$$INFLUX_BUCKET_RAW"; then \
				echo "✓ Raw bucket ($$INFLUX_BUCKET_RAW): Found"; \
			else \
				echo "⚠ Raw bucket ($$INFLUX_BUCKET_RAW): Not found"; \
			fi; \
			if echo "$$BUCKETS_RESPONSE" | grep -q "$$INFLUX_BUCKET_PROCESSED"; then \
				echo "✓ Processed bucket ($$INFLUX_BUCKET_PROCESSED): Found"; \
			else \
				echo "⚠ Processed bucket ($$INFLUX_BUCKET_PROCESSED): Not found"; \
			fi; \
		else \
			echo "✗ InfluxDB authentication: FAILED"; \
			echo "  Please verify INFLUX_TOKEN and INFLUX_ORG are correct"; \
			exit 1; \
		fi; \
		echo ""; \
		echo "=== Testing PostgreSQL Connection ==="; \
		if [ -z "$$CONFIG_DATABASE_URL" ]; then \
			echo "[ERROR] CONFIG_DATABASE_URL not set in .env.local"; \
			exit 1; \
		fi; \
		echo "Connection string: $$CONFIG_DATABASE_URL" | sed "s/:\/\/[^:]*:[^@]*@/:\/\/***:***@/"; \
		echo ""; \
		if ! command -v psql >/dev/null 2>&1; then \
			echo "[WARN] psql not installed, installing postgresql-client..."; \
			apt-get update -qq && apt-get install -y -qq postgresql-client >/dev/null 2>&1; \
		fi; \
		echo "Testing connection..."; \
		if psql "$$CONFIG_DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then \
			echo "✓ PostgreSQL connection: OK"; \
			echo ""; \
			echo "Testing database schema..."; \
			TABLE_COUNT=$$(psql "$$CONFIG_DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '\''public'\'';" 2>/dev/null | tr -d " "); \
			if [ "$$TABLE_COUNT" -gt 0 ]; then \
				echo "✓ Database tables found: $$TABLE_COUNT tables"; \
			else \
				echo "⚠ No tables found in database (this is normal for a fresh installation)"; \
			fi; \
		else \
			echo "✗ PostgreSQL connection: FAILED"; \
			echo ""; \
			echo "Common issues:"; \
			echo "  1. PostgreSQL is not running on the Dagster LXC"; \
			echo "  2. Remote connections not enabled (see PROXMOX_INSTALLATION.md)"; \
			echo "  3. Firewall blocking connection"; \
			echo "  4. Incorrect credentials in CONFIG_DATABASE_URL"; \
			exit 1; \
		fi; \
		echo ""; \
		echo "=== Connection Test Summary ==="; \
		echo "✓ All connections successful!"; \
		echo ""; \
		echo "Your dashboard is properly configured and ready to use."; \
	'

install-dagster:
	@echo "[INFO] Installing Dagster Workflows (systemd native deployment)..."
	@bash workflows_dagster/install/dagster-workflows-install.sh

update-dagster:
	@echo "[INFO] Updating Dagster Workflows..."
	@bash workflows_dagster/install/dagster-workflows-install.sh
