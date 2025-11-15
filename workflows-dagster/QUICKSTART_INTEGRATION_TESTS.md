# Quick Start: Integration Testing

## TL;DR - Run Integration Tests Now

```bash
cd workflows-dagster
./run-integration-tests.sh --docker
```

This single command will:
- ✅ Build Dagster Docker images
- ✅ Start all required services (Postgres, Dagster, InfluxDB)
- ✅ Wait for services to be ready
- ✅ Run all integration tests
- ✅ Clean up containers automatically

## What Gets Tested

### Automatic Tests (No Manual Setup)
- ✅ Dagster connectivity
- ✅ GraphQL API functionality
- ✅ Repository loading
- ✅ Asset discovery and listing
- ✅ Job listing
- ✅ Schedule configuration
- ✅ Resource configuration
- ✅ Daemon health checks
- ✅ Code location health

### Manual/Skipped Tests (Need Real Credentials)
- ⚠️ Tibber API asset materialization
- ⚠️ Full analytics job execution
- ⚠️ InfluxDB read/write operations

## Common Commands

```bash
# Run integration tests with auto-cleanup
./run-integration-tests.sh --docker

# Keep environment running for debugging
./run-integration-tests.sh --docker --no-cleanup

# Access Dagster UI after tests (with --no-cleanup)
open http://localhost:3001

# View logs while tests run
docker-compose -f ../docker-compose.dagster-test.yml logs -f

# Stop test environment manually
docker-compose -f ../docker-compose.dagster-test.yml down -v
```

## Environment Ports

When test environment is running:

| Service | Port | URL |
|---------|------|-----|
| Dagster UI | 3001 | http://localhost:3001 |
| GraphQL API | 3001 | http://localhost:3001/graphql |
| InfluxDB UI | 8086 | http://localhost:8086 |

**Note:** Test port 3001 is different from production port 3000, so both can run simultaneously!

## Test Results Interpretation

```bash
# Successful run
✓ All integration tests passed!

# Failed tests
✗ Some integration tests failed
```

Check the pytest output for details on which tests failed and why.

## Troubleshooting

**Services won't start?**
```bash
# Check Docker logs
docker-compose -f docker-compose.dagster-test.yml logs

# Try increasing wait time
./run-integration-tests.sh --docker --wait 60
```

**Port already in use?**
```bash
# Check what's using port 3001
lsof -i :3001

# Or use different test compose file
```

**Tests timeout?**
- Slow system? Use `--wait 60` for longer startup
- Check `docker-compose.dagster-test.yml` service health

## Advanced Usage

See [INTEGRATION_TESTING.md](INTEGRATION_TESTING.md) for:
- Manual setup steps
- CI/CD integration
- Writing new integration tests
- Performance benchmarks
- Detailed debugging guide
