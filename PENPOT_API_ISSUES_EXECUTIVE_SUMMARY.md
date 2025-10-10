# Penpot API Integration Issues - Executive Summary

**Project:** Penpot MCP Server Integration
**Repository:** https://github.com/meywd/penpot-mcp
**Date:** January 2025
**Full Report:** [PENPOT_API_ISSUES_REPORT.md](./PENPOT_API_ISSUES_REPORT.md)

---

## Overview

While building a comprehensive MCP server for Penpot, we encountered significant API issues that impact reliability and developer experience. This summary highlights the **5 most critical problems** that need immediate attention.

---

## 🔴 Critical Issue #1: API Changes Don't Persist

**Problem:** API returns `200 OK` with `"success": true`, but changes are not visible when fetching the file again.

**Impact:** **Cannot reliably verify if operations work.** Makes it impossible to build production-ready integrations.

### Test Results

| Operation | API Response | Persists in DB | Status |
|-----------|--------------|----------------|--------|
| delete_object | ✅ 200 OK | ✅ Yes | PASS |
| move_object | ✅ 200 OK | ❌ No | **FAIL** |
| resize_object | ✅ 200 OK | ❌ No | **FAIL** |
| change_object_color | ✅ 200 OK | ❌ No | **FAIL** |
| rotate_object | ✅ 200 OK | ❌ No | **FAIL** |

**Source:** `tests/test_validate_local_updates.py`

### Root Cause (Suspected)

- Caching layer not invalidated after updates
- Read-after-write consistency issues
- Browser WebSocket conflicts (see Issue #2)

**Recommendation:** Implement immediate cache invalidation or read-after-write consistency guarantees.

---

## 🔴 Critical Issue #2: Browser Sessions Revert API Changes

**Problem:** If a file is open in a web browser, API changes are silently reverted.

**Discovery:** Took 3+ days to identify this behavior. **Not documented anywhere.**

### How It Happens

```
1. Developer makes API change via REST → Returns 200 OK
2. Browser has WebSocket connection to backend
3. Browser state conflicts with API change
4. Backend chooses browser state over API change
5. API change is silently reverted
```

### Impact

- API appears "broken" during development
- False test results (works when browser closed, fails when open)
- Unpredictable behavior in production

**Recommendation:** Document this behavior prominently OR implement file locking during API operations.

---

## 🟠 High Priority Issue #3: Text Objects Have Secret Rules

**Problem:** Text objects require completely different handling than other shapes, but this is **entirely undocumented**.

### What's Different (Discovered Through Trial & Error)

1. **No object-level fills** - Text objects ignore `fills` property
2. **Requires nested structure** - Must set fills at 3-4 levels deep in content structure
3. **Different format** - Uses kebab-case when sending, camelCase when receiving

### Time Cost

**2+ days** debugging why text color changes didn't work, despite API returning success.

### Code Comparison

```python
# Rectangles (works):
rect['fills'] = [{'fillColor': '#FF0000'}]

# Text (fails silently):
text['fills'] = [{'fillColor': '#FF0000'}]  # ✗ IGNORED

# Text (actual requirement):
text['content']['children'][0]['children'][0]['children'][0]['fills'] = [
    {'fill-color': '#FF0000'}  # Note: kebab-case!
]
```

**Recommendation:** Document text object special cases with clear examples.

---

## 🟠 High Priority Issue #4: Naming Convention Chaos

**Problem:** API uses **THREE different naming conventions** in the same response.

### Example from Real API Response

```json
{
  "project-id": "...",           // kebab-case
  "pagesIndex": {                // camelCase
    "page-123": {
      "objects": {
        "obj-456": {
          "fillColor": "#FF0000", // camelCase
          "fill-opacity": 1.0,    // kebab-case (?!)
          "parent-id": "...",     // kebab-case
          "frameId": "..."        // camelCase (same concept!)
        }
      }
    }
  }
}
```

### Impact on Code

Every field requires guessing which convention applies:

```python
# We had to maintain this mapping:
FIELD_VARIANTS = {
    'frame_id': ['frameId', 'frame-id', 'frame_id'],
    'parent_id': ['parentId', 'parent-id', 'parent_id'],
    # ... 50+ mappings
}
```

**Recommendation:** Standardize on ONE convention (prefer kebab-case for consistency with HTTP headers).

---

## 🟡 Medium Priority Issue #5: Silent Type Mismatch Failures

**Problem:** API silently rejects changes due to type mismatches without returning errors.

### Examples

```python
# This fails silently:
{"fill-opacity": 0.8}  # float

# This works:
{"fill-opacity": 1}    # int (when whole number)

# But API returns: 200 OK, "success": true
```

### Other Type Issues

- Rotation: degrees vs radians (undocumented which is expected)
- Coordinates: sometimes requires float, sometimes int
- UUIDs: sometimes needs `~u` prefix, sometimes doesn't

**Recommendation:** Return validation errors (400 Bad Request) with specific field information.

---

## Summary of Developer Experience

### Time Spent Debugging

- **camelCase vs kebab-case**: 3+ days
- **Text color issues**: 2+ days
- **Browser interference**: 3+ days (thought our code was broken)
- **Type mismatches**: 1+ day
- **Caching/persistence**: 2+ days (still not resolved)

**Total:** ~11+ days of debugging issues that should have been documented or caught by the API.

### What Makes This Challenging

❌ Silent failures (returns 200 OK but changes ignored)
❌ Inconsistent conventions (kebab-case, camelCase, both)
❌ Undocumented special cases (text objects)
❌ Unpredictable behavior (browser interference)
❌ No error messages explaining why things fail

### What Would Help

✅ Immediate cache invalidation after updates
✅ Validation errors with specific field feedback
✅ Document ALL special cases (especially text objects)
✅ Standardize naming conventions
✅ Warn about browser session conflicts

---

## Recommendations Priority Matrix

| Priority | Issue | Impact | Effort | ROI |
|----------|-------|--------|--------|-----|
| **P0** | Fix caching/persistence | CRITICAL | High | High |
| **P0** | Document browser interference | CRITICAL | Low | High |
| **P1** | Document text object rules | HIGH | Low | High |
| **P1** | Add validation errors | HIGH | Medium | High |
| **P2** | Standardize naming | MEDIUM | High | Medium |

---

## Code References

All findings are documented with:
- ✅ **Working code examples** in our repository
- ✅ **Test files** reproducing issues
- ✅ **Screenshots** of problems
- ✅ **Commit history** showing fixes

**Key Files:**
- `tests/test_validate_local_updates.py` - Comprehensive validation showing persistence issues
- `penpot_mcp/api/penpot_api.py` - Workarounds for naming/format issues
- `penpot_mcp/server/mcp_server.py` - Special text object handling

---

## Current Status

✅ **Penpot MCP Server is functional** for:
- Creating files and projects
- Adding shapes (rectangles, circles, text)
- Reading file structure
- Deleting objects

❌ **Not reliable** for:
- Modifying existing objects (changes don't persist)
- Text color changes (complex nested structure)
- Concurrent API + browser usage
- Production deployments requiring reliable updates

---

## Next Steps

We're happy to:
1. **Provide more details** on any specific issue
2. **Share our workarounds** that partially address these issues
3. **Test fixes** against our comprehensive validation suite
4. **Collaborate** on improving API documentation

**Contact:** GitHub issues at https://github.com/meywd/penpot-mcp

---

**Full Technical Report:** [PENPOT_API_ISSUES_REPORT.md](./PENPOT_API_ISSUES_REPORT.md) (31 pages with detailed examples, code samples, and test results)
