#!/usr/bin/env bash

# Dagster Installation Diagnostic Script
# Run this on your LXC to diagnose installation issues

set +e  # Don't exit on errors, we want to check everything

# Colors
BL="\033[36m"
GN="\033[1;92m"
CL="\033[m"
YW="\033[1;33m"
RD="\033[01;31m"

echo -e "${BL}═══════════════════════════════════════════════════════${CL}"
echo -e "${BL}  Dagster Installation Diagnostics${CL}"
echo -e "${BL}═══════════════════════════════════════════════════════${CL}\n"

ERRORS=0
WARNINGS=0

check_file() {
    local file=$1
    local required=$2

    if [ -f "$file" ]; then
        echo -e "${GN}✓${CL} File exists: $file"
        ls -lh "$file"
    else
        if [ "$required" = "required" ]; then
            echo -e "${RD}✗${CL} REQUIRED file missing: $file"
            ((ERRORS++))
        else
            echo -e "${YW}⚠${CL} Optional file missing: $file"
            ((WARNINGS++))
        fi
    fi
}

check_dir() {
    local dir=$1
    local required=$2

    if [ -d "$dir" ]; then
        echo -e "${GN}✓${CL} Directory exists: $dir"
        ls -ld "$dir"
    else
        if [ "$required" = "required" ]; then
            echo -e "${RD}✗${CL} REQUIRED directory missing: $dir"
            ((ERRORS++))
        else
            echo -e "${YW}⚠${CL} Optional directory missing: $dir"
            ((WARNINGS++))
        fi
    fi
}

check_command() {
    local cmd=$1
    local required=$2

    if command -v "$cmd" &> /dev/null; then
        echo -e "${GN}✓${CL} Command available: $cmd"
        which "$cmd"
    else
        if [ "$required" = "required" ]; then
            echo -e "${RD}✗${CL} REQUIRED command missing: $cmd"
            ((ERRORS++))
        else
            echo -e "${YW}⚠${CL} Optional command missing: $cmd"
            ((WARNINGS++))
        fi
    fi
}

echo -e "${BL}Checking directories...${CL}\n"
check_dir "/opt/dagster-workflows" "required"
check_dir "/opt/dagster-workflows/nebenkosten" "required"
check_dir "/opt/dagster-workflows/nebenkosten/secrets" "required"
check_dir "/opt/dagster-workflows/nebenkosten/config" "required"
check_dir "/opt/dagster-workflows/nebenkosten/logs" "required"
check_dir "/opt/dagster-workflows/nebenkosten/storage" "required"
check_dir "/opt/dagster-workflows/venv" "required"

echo -e "\n${BL}Checking virtual environment...${CL}\n"
check_file "/opt/dagster-workflows/venv/bin/python" "required"
check_file "/opt/dagster-workflows/venv/bin/dagster" "required"
check_file "/opt/dagster-workflows/venv/bin/dagster-webserver" "required"
check_file "/opt/dagster-workflows/venv/bin/dagster-daemon" "required"

if [ -f "/opt/dagster-workflows/venv/bin/dagster" ]; then
    echo -e "\n${BL}Dagster version:${CL}"
    /opt/dagster-workflows/venv/bin/dagster --version || echo -e "${RD}Failed to get version${CL}"
fi

echo -e "\n${BL}Checking secrets files...${CL}\n"
check_file "/opt/dagster-workflows/nebenkosten/secrets/influxdb.env" "required"
check_file "/opt/dagster-workflows/nebenkosten/secrets/tibber.env" "optional"

echo -e "\n${BL}Checking config files...${CL}\n"
check_file "/opt/dagster-workflows/nebenkosten/config/config.yaml" "required"
check_file "/opt/dagster-workflows/nebenkosten/config/meters.yaml" "optional"
check_file "/opt/dagster-workflows/nebenkosten/config/seasonal_patterns.yaml" "optional"

echo -e "\n${BL}Checking Dagster config files...${CL}\n"
check_file "/opt/dagster-workflows/nebenkosten/workflows_dagster/dagster.yaml" "required"
check_file "/opt/dagster-workflows/nebenkosten/workflows_dagster/workspace.yaml" "required"

echo -e "\n${BL}Checking systemd service files...${CL}\n"
check_file "/etc/systemd/system/dagster-user-code.service" "required"
check_file "/etc/systemd/system/dagster-daemon.service" "required"
check_file "/etc/systemd/system/dagster-webserver.service" "required"

echo -e "\n${BL}Checking PostgreSQL...${CL}\n"
check_command "psql" "required"

if command -v psql &> /dev/null; then
    echo -e "\n${BL}Checking PostgreSQL databases...${CL}"

    if sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw dagster; then
        echo -e "${GN}✓${CL} Database 'dagster' exists"
    else
        echo -e "${RD}✗${CL} Database 'dagster' missing"
        ((ERRORS++))
    fi

    if sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw nebenkosten_config; then
        echo -e "${GN}✓${CL} Database 'nebenkosten_config' exists"

        # Check if schema is initialized
        if sudo -u postgres psql -d nebenkosten_config -c '\dt' 2>/dev/null | grep -q 'meters'; then
            echo -e "${GN}✓${CL} Configuration database schema initialized"

            # Check data
            METER_COUNT=$(sudo -u postgres psql -d nebenkosten_config -tAc "SELECT COUNT(*) FROM meters;" 2>/dev/null)
            HOUSEHOLD_COUNT=$(sudo -u postgres psql -d nebenkosten_config -tAc "SELECT COUNT(*) FROM households;" 2>/dev/null)

            echo -e "${GN}✓${CL} Found $METER_COUNT meters in database"
            echo -e "${GN}✓${CL} Found $HOUSEHOLD_COUNT households in database"
        else
            echo -e "${YW}⚠${CL} Configuration database schema not initialized"
            ((WARNINGS++))
        fi
    else
        echo -e "${RD}✗${CL} Database 'nebenkosten_config' missing"
        ((ERRORS++))
    fi
fi

echo -e "\n${BL}Checking system users...${CL}\n"
if id -u dagster &>/dev/null; then
    echo -e "${GN}✓${CL} User 'dagster' exists"
    id dagster
else
    echo -e "${RD}✗${CL} User 'dagster' missing"
    ((ERRORS++))
fi

echo -e "\n${BL}Checking file permissions...${CL}\n"
if [ -d "/opt/dagster-workflows" ]; then
    OWNER=$(stat -c '%U:%G' /opt/dagster-workflows/nebenkosten 2>/dev/null)
    if [ "$OWNER" = "dagster:dagster" ]; then
        echo -e "${GN}✓${CL} Correct ownership: /opt/dagster-workflows/nebenkosten ($OWNER)"
    else
        echo -e "${RD}✗${CL} Wrong ownership: /opt/dagster-workflows/nebenkosten ($OWNER, should be dagster:dagster)"
        ((ERRORS++))
    fi
fi

echo -e "\n${BL}Checking service status...${CL}\n"
for service in dagster-user-code dagster-daemon dagster-webserver; do
    if systemctl is-active --quiet ${service}.service; then
        echo -e "${GN}✓${CL} Service ${service} is running"
    elif systemctl is-enabled --quiet ${service}.service 2>/dev/null; then
        echo -e "${YW}⚠${CL} Service ${service} is enabled but not running"
        ((WARNINGS++))
    else
        echo -e "${RD}✗${CL} Service ${service} is not running or not enabled"
        ((ERRORS++))
    fi
done

echo -e "\n${BL}═══════════════════════════════════════════════════════${CL}"
echo -e "${BL}  Summary${CL}"
echo -e "${BL}═══════════════════════════════════════════════════════${CL}\n"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GN}✓ All checks passed!${CL}\n"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YW}⚠ $WARNINGS warning(s) found (optional items missing)${CL}\n"
    exit 0
else
    echo -e "${RD}✗ $ERRORS error(s) found${CL}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YW}⚠ $WARNINGS warning(s) found${CL}"
    fi
    echo -e "\n${YW}Recommended action:${CL}"
    echo -e "1. Review the errors above"
    echo -e "2. Fix missing files/directories"
    echo -e "3. Re-run the installation script if needed\n"
    exit 1
fi
