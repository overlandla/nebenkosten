.PHONY: help install-dashboard update-dashboard install-dagster update-dagster

help:
	@echo "Nebenkosten Installation Targets"
	@echo "================================="
	@echo ""
	@echo "Dashboard:"
	@echo "  make install-dashboard  - Install Utility Meter Dashboard"
	@echo "  make update-dashboard   - Update Dashboard to latest version"
	@echo ""
	@echo "Dagster Workflows:"
	@echo "  make install-dagster    - Install Dagster Workflows"
	@echo "  make update-dagster     - Update Dagster to latest version"
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
	@rsync -a --exclude='.git' --exclude='node_modules' --exclude='.next' \
		$(CURDIR)/dashboard/ /opt/utility-meter-dashboard/
	@cd /opt/utility-meter-dashboard && npm install >/dev/null 2>&1
	@cd /opt/utility-meter-dashboard && npm run build >/dev/null 2>&1
	@echo "[INFO] Starting service..."
	@systemctl start utility-meter-dashboard
	@sleep 2
	@echo ""
	@echo "✓ Dashboard updated successfully!"
	@echo "  Access at: http://$$(hostname -I | awk '{print $$1}'):3000"
	@echo ""

install-dagster:
	@echo "[INFO] Installing Dagster Workflows (systemd native deployment)..."
	@bash workflows_dagster/install/dagster-workflows-install.sh

update-dagster:
	@echo "[INFO] Updating Dagster Workflows..."
	@bash workflows_dagster/install/dagster-workflows-install.sh
