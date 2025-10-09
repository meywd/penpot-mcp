# Integration Testing Against Local Penpot

This guide explains how to run integration tests against a real Penpot instance (local or cloud).

## Prerequisites

1. **Running Penpot instance** (local at http://localhost:9001 or cloud)
2. **Valid credentials** (username/email and password)
3. **Python environment** with penpot-mcp installed

## Setup

### 1. Set Environment Variables

Create a `.env.test` file or set environment variables:

```bash
# For local Penpot instance
export PENPOT_API_URL=http://localhost:9001/api
export PENPOT_USERNAME=your_email@example.com
export PENPOT_PASSWORD=your_password

# For cloud Penpot
export PENPOT_API_URL=https://design.penpot.app/api
export PENPOT_USERNAME=your_email@example.com
export PENPOT_PASSWORD=your_password
```

On Windows (PowerShell):
```powershell
$env:PENPOT_API_URL="http://localhost:9001/api"
$env:PENPOT_USERNAME="your_email@example.com"
$env:PENPOT_PASSWORD="your_password"
```

### 2. Run Integration Tests

Run all integration tests:
```bash
uv run pytest tests/test_integration_local.py -v -s
```

Run specific test class:
```bash
uv run pytest tests/test_integration_local.py::TestShapeCreation -v -s
```

Run specific test:
```bash
uv run pytest tests/test_integration_local.py::TestMCPTools::test_add_rectangle_tool -v -s
```

## What Gets Tested

### Project & File Management
- ✅ Get teams
- ✅ Create and delete projects
- ✅ Create and delete files
- ✅ Get file with vern field (self-hosted compatibility)

### Shape Creation (API Level)
- ✅ Add rectangle
- ✅ Add circle
- ✅ Add text
- ✅ Add frame

### MCP Tools (End-to-End)
- ✅ list_projects tool
- ✅ add_rectangle tool
- ✅ add_circle tool
- ✅ add_text tool

### Version Compatibility
- ✅ vern parameter handling for self-hosted instances

## Test Cleanup

The tests automatically clean up:
- Test projects created during tests
- Test files created during tests

If cleanup fails, you may need to manually delete test projects/files with names like:
- "MCP Integration Test {timestamp}"
- "Test File {timestamp}"

## Debugging

### Enable Debug Output

The integration tests run with `debug=True` by default, so you'll see:
- API request/response details
- Transit+JSON conversion
- Session management

### Common Issues

**Tests are skipped:**
- Make sure `PENPOT_USERNAME` and `PENPOT_PASSWORD` are set
- Check that your Penpot instance is running

**401/403 Authentication errors:**
- Verify credentials are correct
- Check API URL is correct (include `/api` suffix)

**400 Bad Request with vern validation:**
- This is what we're fixing! The tests should pass with the new vern support

**Connection refused:**
- Make sure Penpot is running at the specified URL
- For local: http://localhost:9001
- Check firewall settings

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run integration tests
  env:
    PENPOT_API_URL: ${{ secrets.PENPOT_API_URL }}
    PENPOT_USERNAME: ${{ secrets.PENPOT_USERNAME }}
    PENPOT_PASSWORD: ${{ secrets.PENPOT_PASSWORD }}
  run: |
    uv run pytest tests/test_integration_local.py -v
```

## Running Against Different Penpot Versions

### Self-Hosted (Latest)
```bash
export PENPOT_API_URL=http://localhost:9001/api
uv run pytest tests/test_integration_local.py -v -s
```

### Cloud (Production)
```bash
export PENPOT_API_URL=https://design.penpot.app/api
uv run pytest tests/test_integration_local.py -v -s
```

### Docker Compose Local Setup
```bash
# Start Penpot
cd penpot-docker
docker-compose up -d

# Wait for startup
sleep 30

# Run tests
export PENPOT_API_URL=http://localhost:9001/api
export PENPOT_USERNAME=admin@penpot.local
export PENPOT_PASSWORD=admin
uv run pytest tests/test_integration_local.py -v -s
```
