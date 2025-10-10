# Integration Testing Against Local Penpot

This guide explains how to run integration tests against a real Penpot instance (local or cloud).

## Overview

The integration tests create a **persistent test project** with separate files for each test class, allowing you to visually verify the results in Penpot after tests run. This approach helps validate that all shapes, text, frames, and other design elements are created correctly.

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

## Test Organization

### Persistent Test Project

The tests create a project called **"MCP Integration Tests - {timestamp}"** that persists after the tests complete. This allows you to:

1. **Visually verify** all test results in Penpot
2. **Debug failures** by inspecting the actual design elements
3. **Track progress** across multiple test runs

Each test class creates its own file in the project:

| File Name | Test Class | Contents |
|-----------|-----------|----------|
| `01 - Project & File Management` | TestProjectFileManagement | Tests for CRUD operations |
| `02 - Shape Creation` | TestShapeCreation | Rectangle, circle, text, frame tests |
| `03 - MCP Tools` | TestMCPTools | End-to-end MCP tool validation |
| `04 - Version Compatibility` | TestVersionCompatibility | vern parameter handling |

### Test Cleanup

By default, **test projects are preserved** for visual inspection. To enable automatic cleanup:

```bash
export CLEANUP_TEST_FILES=true
```

When enabled, the test project and all its files will be deleted after tests complete.

### Manual Cleanup

If you want to manually delete old test projects:

1. Open Penpot in your browser
2. Look for projects named "MCP Integration Tests - {timestamp}"
3. Delete the ones you no longer need

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

## Example Test Output

When tests run successfully, you'll see output like:

```
============================================================
Created test project: MCP Integration Tests - 2025-10-09 12:20
Project ID: 689fbaf0-efce-81fe-8006-edb587995b16
============================================================

────────────────────────────────────────────────────────────
Created test file: 01 - Project & File Management - 2025-10-09 12:20
File ID: 689fbaf0-efce-81fe-8006-edb587c3b96a
────────────────────────────────────────────────────────────

tests/test_integration_local.py::TestProjectFileManagement::test_get_teams PASSED

────────────────────────────────────────────────────────────
Created test file: 02 - Shape Creation - 2025-10-09 12:20
File ID: 689fbaf0-efce-81fe-8006-edb587e27d06
────────────────────────────────────────────────────────────

Test: Add Rectangle
Page ID: 689fbaf0-efce-81fe-8006-edb587e27d07
Added rectangle, new revision: 2

tests/test_integration_local.py::TestShapeCreation::test_add_rectangle PASSED

============================================================
Test project preserved for visual inspection:
  Project: MCP Integration Tests - 2025-10-09 12:20
  ID: 689fbaf0-efce-81fe-8006-edb587995b16
  Set CLEANUP_TEST_FILES=true to auto-delete
============================================================

======================== 13 passed in 2.79s =========================
```

After tests complete, open Penpot and navigate to the test project to see all the created shapes, text, and frames!
