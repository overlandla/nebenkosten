# Secrets Directory

This directory contains sensitive credentials that should **NEVER** be committed to version control.

## Required Files

### 1. `influxdb.env`
```bash
INFLUX_TOKEN=your_influxdb_api_token_here
INFLUX_ORG=your_influxdb_org_id_here
```

**How to get these values:**
1. Log into your InfluxDB web UI (http://your-influxdb-ip:8086)
2. Go to **Data** > **API Tokens**
3. Click **Generate API Token** > **All Access Token**
4. Copy the token value
5. For ORG ID: Click your organization name in top-left, copy the org ID from the URL

### 2. `tibber.env`
```bash
TIBBER_API_TOKEN=your_tibber_api_token_here
```

**How to get this value:**
1. Log into https://developer.tibber.com/
2. Create a personal access token
3. Copy the token value

## Setup Instructions

1. Copy the template files:
   ```bash
   cp ../env.example influxdb.env
   cp ../env.example tibber.env
   ```

2. Edit each file and replace placeholders with actual values:
   ```bash
   nano influxdb.env  # or use your preferred editor
   nano tibber.env
   ```

3. Verify permissions (should not be world-readable):
   ```bash
   chmod 600 *.env
   ```

4. Test the secrets:
   ```bash
   # From the project root
   docker-compose config  # This will show if environment variables are loaded correctly
   ```

## Security Notes

- ✅ This directory is in `.gitignore` - secrets will not be committed
- ✅ Docker Compose will load these files via `env_file` directive
- ⚠️ **Never share these files** - they provide full access to your data
- ⚠️ If a secret is compromised, **rotate it immediately**:
  - InfluxDB: Generate a new API token and delete the old one
  - Tibber: Generate a new token in the developer portal

## Troubleshooting

**Problem:** Container fails to start with "environment variable not set"

**Solution:**
1. Check that the `.env` file exists in this directory
2. Verify the file has the correct format (KEY=value, no spaces around `=`)
3. Check Docker Compose is using `env_file: - secrets/influxdb.env`
4. Restart the Docker Compose stack: `docker-compose down && docker-compose up -d`

**Problem:** "Permission denied" when reading secrets

**Solution:**
```bash
chmod 600 secrets/*.env
```

**Problem:** Need to test if secrets are valid

**Solution:**
```bash
# Test InfluxDB connection
docker run --rm --env-file secrets/influxdb.env curlimages/curl:latest \
  sh -c 'curl -X GET "$INFLUX_URL/api/v2/buckets" -H "Authorization: Token $INFLUX_TOKEN"'

# Test Tibber connection
docker run --rm --env-file secrets/tibber.env curlimages/curl:latest \
  sh -c 'curl -X POST https://api.tibber.com/v1-beta/gql -H "Authorization: Bearer $TIBBER_API_TOKEN" -d "{\"query\":\"{ viewer { userId } }\"}"'
```
