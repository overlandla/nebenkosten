# Dagster Integration Testing Guide

This guide explains how to run integration tests against a live Dagster instance.

## Overview

We have two types of integration tests:

1. **Mock Integration Tests** (`tests/integration/test_asset_integration.py`)
   - Test asset interactions with mocked dependencies
   - Fast execution, no external services required
   - Good for CI/CD pipelines

2. **Live Integration Tests** (`tests/integration/test_live_dagster.py`)
   - Test against actual running Dagster instance via GraphQL API
   - Requires Dagster services to be running
   - Tests real system behavior

## Quick Start

### Option 1: Auto-Start Test Environment (Recommended)

This will automatically spin up a test Dagster environment and run integration tests:

```bash
cd workflows-dagster
./run-integration-tests.sh --docker
```

**What it does:**
1. Builds Docker images for Dagster
2. Starts test services (Postgres, Dagster daemon, webserver, user code)
3. Waits for services to be ready
4. Runs all integration tests
5. Cleans up Docker containers

**Options:**
- `--docker` - Run against Docker Compose test environment (auto-start)
- `--no-cleanup` - Keep containers running after tests (useful for debugging)
- `--wait N` - Wait N seconds for services to be ready (default: 30)
- `--skip-build` - Skip Docker image building (faster if images exist)

**Examples:**

```bash
# Run with default settings
./run-integration-tests.sh --docker

# Keep environment running for debugging
./run-integration-tests.sh --docker --no-cleanup

# Skip build for faster iteration
./run-integration-tests.sh --docker --skip-build

# Custom wait time for slower systems
./run-integration-tests.sh --docker --wait 60
```

### Option 2: Test Against Existing Dagster Instance

If you already have Dagster running (e.g., via `docker-compose.dagster.yml`):

```bash
cd workflows-dagster
./run-integration-tests.sh
```

This assumes Dagster is accessible at `http://localhost:3000`.

### Option 3: Manual Setup

For full control over the test environment:

#### 1. Start Dagster Test Services

```bash
# From project root
docker-compose -f docker-compose.dagster-test.yml up -d
```

#### 2. Wait for Services

```bash
# Check Dagster UI is accessible
curl http://localhost:3001

# Or open in browser
open http://localhost:3001
```

#### 3. Run Tests

```bash
cd workflows-dagster

# Run all integration tests
pytest tests/integration/ -m integration -v

# Run only live tests
pytest tests/integration/test_live_dagster.py -m live -v

# Run only mock integration tests
pytest tests/integration/test_asset_integration.py -v
```

#### 4. Cleanup

```bash
# From project root
docker-compose -f docker-compose.dagster-test.yml down -v
```

## Test Environment Details

### Docker Compose Test Setup

The `docker-compose.dagster-test.yml` file creates an isolated test environment:

- **dagster-test-postgres**: Ephemeral PostgreSQL database
- **dagster-test-daemon**: Dagster daemon for schedules/sensors
- **dagster-test-webserver**: Dagster UI on port **3001**
- **dagster-test-user-code**: Python code location server
- **influxdb-test**: Mock InfluxDB instance (optional)

**Key Differences from Production:**
- Uses port 3001 instead of 3000 (can run alongside production)
- No persistent volumes (fresh start every time)
- Pre-configured test credentials
- Isolated network

### Environment Variables

The test environment uses these environment variables:

```bash
# InfluxDB
INFLUX_URL=http://influxdb-test:8086
INFLUX_TOKEN=test-token-12345
INFLUX_ORG=test-org
INFLUX_BUCKET=test-bucket

# Tibber
TIBBER_API_TOKEN=test-tibber-token

# Dagster
DAGSTER_TEST_URL=http://localhost:3001
```

## Test Coverage

### Mock Integration Tests

Located in `tests/integration/test_asset_integration.py`:

- ✅ Discovery to interpolation pipeline
- ✅ Asset dependency resolution
- ✅ Full analytics job execution
- ✅ Resource integration with assets

**Run with:**
```bash
pytest tests/integration/test_asset_integration.py -v
```

### Live Integration Tests

Located in `tests/integration/test_live_dagster.py`:

#### Connection Tests
- ✅ Dagster webserver reachability
- ✅ GraphQL endpoint functionality
- ✅ Repository loading

#### Asset Tests
- ✅ List all assets
- ⚠️ Asset materialization (requires real data sources)

#### Job Tests
- ✅ List all jobs
- ⚠️ Job execution (requires real data sources)

#### Schedule Tests
- ✅ List schedules
- ✅ Verify cron expressions

#### Resource Tests
- ✅ Resource configuration verification

#### Health Checks
- ✅ Daemon health status
- ✅ Code location health

**Run with:**
```bash
pytest tests/integration/test_live_dagster.py -m live -v

# Skip tests that need real data
pytest tests/integration/test_live_dagster.py -m "live and not slow" -v
```

## Debugging Integration Tests

### View Dagster Logs

```bash
# All services
docker-compose -f docker-compose.dagster-test.yml logs -f

# Specific service
docker-compose -f docker-compose.dagster-test.yml logs -f dagster-test-webserver
```

### Access Dagster UI

When using `--docker --no-cleanup`, the Dagster UI remains accessible:

```
http://localhost:3001
```

You can:
- View asset lineage
- Check run history
- Inspect logs
- Manually trigger materializations

### Interactive Testing

1. Start test environment with no cleanup:
   ```bash
   ./run-integration-tests.sh --docker --no-cleanup
   ```

2. Access the Python environment:
   ```bash
   docker exec -it dagster-test-user-code bash
   ```

3. Test interactively:
   ```bash
   python3
   >>> from dagster_project import utility_repository
   >>> utility_repository.get_all_asset_specs()
   ```

### Common Issues

**Services not starting:**
- Check Docker logs: `docker-compose -f docker-compose.dagster-test.yml logs`
- Verify port 3001 is not in use: `lsof -i :3001`
- Try increasing wait time: `./run-integration-tests.sh --docker --wait 60`

**Tests timing out:**
- Increase timeout in test code
- Check network connectivity between containers
- Verify InfluxDB/Tibber credentials if using real sources

**GraphQL errors:**
- Ensure webserver is fully started: `curl http://localhost:3001/graphql`
- Check code location is loaded: View UI at http://localhost:3001

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Run Integration Tests
        run: |
          cd workflows-dagster
          ./run-integration-tests.sh --docker --wait 45
        env:
          INFLUX_TOKEN: ${{ secrets.INFLUX_TEST_TOKEN }}
          TIBBER_API_TOKEN: ${{ secrets.TIBBER_TEST_TOKEN }}
```

### GitLab CI Example

```yaml
integration-tests:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  script:
    - cd workflows-dagster
    - ./run-integration-tests.sh --docker --wait 45
  variables:
    INFLUX_TOKEN: $INFLUX_TEST_TOKEN
    TIBBER_API_TOKEN: $TIBBER_TEST_TOKEN
```

## Performance Benchmarks

Typical execution times on modern hardware:

| Test Suite | Duration | Services |
|------------|----------|----------|
| Mock Integration | ~15s | None |
| Live Connection Tests | ~5s | Dagster only |
| Full Live Tests | ~30s | All services |
| Docker Startup | ~30-60s | All services |

## Best Practices

1. **Use `--docker` for reproducibility** - Ensures clean state every time
2. **Use `--no-cleanup` for debugging** - Allows inspection after test failures
3. **Run mock tests in CI** - Fast, reliable, no external dependencies
4. **Run live tests before releases** - Catch integration issues early
5. **Keep test data small** - Faster execution, easier debugging

## Next Steps

- Add more live integration tests for specific workflows
- Implement end-to-end tests with real (but test) data
- Add performance/load testing for Dagster jobs
- Create test data fixtures for InfluxDB
