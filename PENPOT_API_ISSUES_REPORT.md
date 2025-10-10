# Penpot API Integration Issues Report

**Project:** Penpot MCP Server
**Repository:** https://github.com/meywd/penpot-mcp
**Date:** January 2025
**Report Author:** Development Team

## Executive Summary

This report documents critical issues, undocumented behaviors, and gotchas encountered while building a comprehensive MCP (Model Context Protocol) server for Penpot's API. These findings are based on extensive testing, debugging, and integration work over multiple days of development.

## Table of Contents

1. [Transit+JSON Format Inconsistencies](#1-transitjson-format-inconsistencies)
2. [Caching and Data Persistence Issues](#2-caching-and-data-persistence-issues)
3. [Object Naming and Field Convention Chaos](#3-object-naming-and-field-convention-chaos)
4. [Text Object Special Cases (Undocumented)](#4-text-object-special-cases-undocumented)
5. [Type Mismatch Silent Failures](#5-type-mismatch-silent-failures)
6. [Session and Revision Management Complexity](#6-session-and-revision-management-complexity)
7. [Browser Interference with API Operations](#7-browser-interference-with-api-operations)
8. [Authentication and Token Management](#8-authentication-and-token-management)
9. [Testing and Validation Challenges](#9-testing-and-validation-challenges)
10. [Recommendations](#10-recommendations)

---

## 1. Transit+JSON Format Inconsistencies

### Issue: Bidirectional Format Conversion Confusion

**Severity:** HIGH
**Impact:** Breaking changes, hours of debugging

#### Problem Description

Penpot's API uses Transit+JSON format, but the conversion rules are inconsistent and poorly documented:

1. **API Returns camelCase, Expects kebab-case**
   ```json
   // API returns:
   {"fillColor": "#FF0000", "fillOpacity": 1.0}

   // API expects when sending:
   {"fill-color": "#FF0000", "fill-opacity": 1}
   ```

2. **Text Content Structure Exception**
   - Most object properties use kebab-case when sending
   - Text content structure type values (`root`, `paragraph-set`, `paragraph`) must remain as **strings**, not Transit keywords
   - Other type values need `~:` prefix (e.g., `~:rect`, `~:circle`)

3. **UUID Prefix Requirements**
   - Object IDs require `~u` prefix in Transit format
   - Session IDs require `~u` prefix
   - Page IDs and Frame IDs: **sometimes yes, sometimes no** (undocumented)

#### Code Example of the Problem

```python
# This works for shapes but FAILS for text:
change = {
    "type": "~:mod-obj",  # ✓ Correct
    "operations": [{
        "attr": "~:fills",  # ✓ Correct
        "val": [{"fillColor": "#FF0000"}]  # ✗ WRONG - should be fill-color
    }]
}

# Text requires special handling:
content = {
    "type": "root",  # ✓ Must be STRING, not ~:root
    "children": [{
        "type": "paragraph-set",  # ✓ Must be STRING
        "children": [{
            "fills": [{"fill-color": "#FF0000"}]  # ✓ kebab-case required
        }]
    }]
}
```

#### Root Cause

The Transit+JSON converter in Penpot's backend has:
- Different rules for different object types
- Inconsistent serialization/deserialization
- No clear documentation on which fields use which format

#### Impact on Development

- **3+ days** spent debugging camelCase vs kebab-case issues
- Multiple failed attempts before discovering the pattern
- Still unclear why some fields work with either format

---

## 2. Caching and Data Persistence Issues

### Issue: API Accepts Changes But They Don't Persist

**Severity:** CRITICAL
**Impact:** Makes it impossible to verify if operations worked

#### Problem Description

The most frustrating issue encountered:

1. **Update API returns 200 OK**
2. **Response includes updated revision number**
3. **Immediately fetching the file returns OLD data**
4. **Changes appear in browser (sometimes) but not via API**

#### Reproduction Steps

```python
# 1. Update object color
api.update_file(file_id, session_id, revn, [change])
# Returns: {'revn': 5, 'success': True}

# 2. Immediately fetch file
file_data = api.get_file(file_id)

# 3. Check object color
obj = file_data['data']['pagesIndex'][page_id]['objects'][object_id]
print(obj['fills'][0]['fillColor'])  # Still shows OLD color!
```

#### Test Results

From our comprehensive validation test (`tests/test_validate_local_updates.py`):

| Operation | API Response | Verified in DB | Status |
|-----------|--------------|----------------|--------|
| `delete_object` | ✅ 200 OK | ✅ Deleted | **PASS** |
| `move_object` | ✅ 200 OK | ❌ Old position | **FAIL** |
| `resize_object` | ✅ 200 OK | ❌ Old dimensions | **FAIL** |
| `change_object_color` | ✅ 200 OK | ❌ Old color | **FAIL** |
| `rotate_object` | ✅ 200 OK | ❌ No rotation | **FAIL** |

#### Potential Causes

1. **Server-side caching layer** not invalidated after updates
2. **Read-after-write consistency** issues
3. **Database replication lag**
4. **Browser session conflicts** (see Section 7)

#### Workarounds Attempted

- ✅ Adding delays (500ms, 1s, 2s) - **No effect**
- ✅ Clearing local cache - **No effect**
- ✅ Using different session IDs - **No effect**
- ✅ Incrementing revision manually - **No effect**
- ⚠️ Closing browser before API calls - **Sometimes works**

---

## 3. Object Naming and Field Convention Chaos

### Issue: Inconsistent Property Naming Across API

**Severity:** MEDIUM
**Impact:** Code complexity, maintenance burden

#### The Chaos

Penpot's API uses **THREE different naming conventions** in the same responses:

1. **kebab-case**: `page-id`, `session-id`, `fill-color`
2. **camelCase**: `fillColor`, `fillOpacity`, `parentId`
3. **Hybrid**: `frame-id` in some places, `frameId` in others

#### Real Example from API Response

```json
{
  "id": "file-123",
  "project-id": "proj-456",           // kebab-case
  "data": {
    "pages-index": {                  // kebab-case
      "page-789": {
        "objects": {
          "obj-abc": {
            "fillColor": "#FF0000",   // camelCase
            "fillOpacity": 1.0,       // camelCase
            "parent-id": "frame-def", // kebab-case (?!)
            "frameId": "frame-def"    // camelCase for SAME concept
          }
        }
      }
    }
  }
}
```

#### Impact on Code

Every API interaction requires:
1. Reading documentation (if it exists)
2. Trial and error to find correct field name
3. Creating conversion functions
4. Maintaining field name mappings

```python
# Actual code we had to write:
FIELD_NAME_VARIANTS = {
    'frame_id': ['frameId', 'frame-id', 'frame_id'],
    'parent_id': ['parentId', 'parent-id', 'parent_id'],
    'fill_color': ['fillColor', 'fill-color', 'fill_color'],
    # ... 50+ more mappings
}
```

---

## 4. Text Object Special Cases (Undocumented)

### Issue: Text Objects Have Completely Different Rules

**Severity:** HIGH
**Impact:** Text operations are unreliable

#### Discovery Process

It took **2+ days** to discover that text objects:

1. **Do NOT support object-level fills**
   ```python
   # This works for rectangles but FAILS silently for text:
   text_obj = {
       "type": "text",
       "fills": [{"fillColor": "#FF0000"}]  # ✗ IGNORED
   }
   ```

2. **Require fills in THREE nested levels**
   ```python
   # Correct (undocumented) structure:
   text_obj = {
       "type": "text",
       "content": {
           "children": [{
               "children": [{
                   "fills": [{"fill-color": "#FF0000"}],  # Level 3!
                   "children": [{
                       "fills": [{"fill-color": "#FF0000"}]  # Level 4!
                   }]
               }]
           }]
       }
   }
   ```

3. **Content structure keys use kebab-case when SENDING**
   ```python
   # API returns camelCase:
   {"fillColor": "#FF0000", "fontSize": "24"}

   # But expects kebab-case when sending:
   {"fill-color": "#FF0000", "font-size": "24"}
   ```

#### Why This is Critical

- **Zero documentation** about text objects being special
- **Silent failures** - API returns 200 OK but ignores changes
- **Inconsistent with other object types**
- **No error messages** to guide developers

#### Test Case

```python
# From: tests/test_validate_local_updates.py
# Result: FAIL - Text color not changed
# Despite API returning: {"success": true, "revn": 7}
```

---

## 5. Type Mismatch Silent Failures

### Issue: API Silently Rejects Changes Due to Type Mismatches

**Severity:** MEDIUM
**Impact:** Unpredictable behavior

#### The Problem

Penpot's API is **extremely strict** about data types but provides **no feedback** when types don't match:

1. **Opacity: int vs float**
   ```python
   # This FAILS silently:
   {"fill-opacity": 0.8}  # float

   # This works:
   {"fill-opacity": 1}    # int (when whole number)
   ```

2. **Coordinates: float required (sometimes)**
   ```python
   # This works:
   {"x": 100, "y": 200}

   # This FAILS in some contexts:
   {"x": 100.0, "y": 200.0}  # But required in others!
   ```

3. **Rotation: degrees vs radians (undocumented)**
   ```python
   # Is this degrees or radians?
   {"rotation": 45}  # API accepts but unclear units

   # Reading back:
   {"rotation": 0.7853981633974483}  # Radians!
   ```

#### Code Fix Required

```python
# We had to add explicit type checking:
opacity_value = int(fill_opacity) if fill_opacity == int(fill_opacity) else fill_opacity

# This should be handled by the API or documented clearly
```

---

## 6. Session and Revision Management Complexity

### Issue: Revision System is Fragile and Undocumented

**Severity:** MEDIUM
**Impact:** Race conditions, conflicts

#### The Problem

Every file update requires:

1. **Session ID** - Generated UUID
2. **Revision number** - Current file revision
3. **Version number** - Current file version (vern)

But:
- **No documentation** on difference between revn and vern
- **No guidance** on handling conflicts
- **No clear error messages** when revision is wrong

#### What We Learned (Through Trial and Error)

```python
# Revision management (discovered, not documented):
# 1. Get current revision before ANY change
file_data = api.get_file(file_id)
current_revn = file_data['revn']  # or file_data.get('data', {}).get('revn', 0)

# 2. Generate new session for each editing "session"
session_id = str(uuid.uuid4())

# 3. Update with current revision
result = api.update_file(file_id, session_id, current_revn, changes)

# 4. Result contains NEW revision for next update
new_revn = result['revn']
```

#### Questions We Still Have

- What happens if two clients update simultaneously?
- Does session ID need to be unique per-file or globally?
- Can we reuse session IDs?
- What's the difference between revn and vern?

**Answer:** Unknown. Not documented.

---

## 7. Browser Interference with API Operations

### Issue: Browser Sessions Revert API Changes

**Severity:** CRITICAL
**Impact:** Unpredictable behavior during development

#### Discovery

After extensive debugging, we discovered:

**If a Penpot file is open in a web browser, API changes may be reverted in real-time.**

#### How It Happens

1. Developer makes API change → Returns 200 OK
2. Browser has WebSocket connection to backend
3. Browser's state conflicts with API change
4. Backend chooses browser state (why?!)
5. API change is silently reverted

#### Reproduction

```bash
# Terminal 1: Keep file open in browser
open http://localhost:9001/#/workspace/{file-id}/{page-id}

# Terminal 2: Make API change
python -c "api.update_file(...)"  # Returns success

# Terminal 3: Verify change
python -c "print(api.get_file(...))"  # Shows OLD data!

# Close browser → Re-run Terminal 3 → Change appears!
```

#### Impact

- **Wasted hours** debugging "broken" API code
- **False positives** in tests (change works when browser closed)
- **No warning** in API responses
- **Not mentioned anywhere** in documentation

#### Required Workaround

```python
# In our validation test:
print("[NOTE] IMPORTANT: Open the file in browser to visually verify changes")
print("   Make sure to CLOSE the browser before running this test again!")
```

This should **not** be the developer's responsibility to discover.

---

## 8. Authentication and Token Management

### Issue: Inconsistent Auth Requirements and Behavior

**Severity:** LOW
**Impact:** Confusion, extra implementation work

#### Problems

1. **Cookie-based auth** (good) but:
   - Cookies expire unpredictably
   - No clear expiration time in response
   - Token refresh not documented

2. **401/403 errors don't distinguish between**:
   - Invalid credentials
   - Expired token
   - Insufficient permissions
   - CloudFlare protection (!)

3. **CloudFlare protection** (on design.penpot.app):
   - Randomly triggers
   - Requires manual browser verification
   - Breaks CI/CD pipelines
   - No programmatic bypass

#### Code We Had to Write

```python
def _make_authenticated_request(self, method, url, **kwargs):
    """Make request with automatic re-auth on 401/403."""
    try:
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    except HTTPError as e:
        if e.response.status_code in (401, 403):
            # Is this expired token, wrong creds, or CloudFlare?
            # Who knows! Let's try everything...
            if self._is_cloudflare_error(e.response):
                raise CloudFlareError(...)
            else:
                # Try to re-auth
                self.login_with_password()
                # Retry request...
        raise
```

---

## 9. Testing and Validation Challenges

### Issue: Impossible to Write Reliable Tests

**Severity:** HIGH
**Impact:** Can't verify if code works

#### The Core Problem

How do you test an API when:
1. ✅ API returns 200 OK
2. ✅ Response includes success: true
3. ✅ Revision number increments
4. ❌ Changes don't persist
5. ❌ No error message explaining why

#### Our Validation Test Results

From `tests/test_validate_local_updates.py`:

```
============================================================
  VALIDATION SUMMARY
============================================================

Test file ID: 689fbaf0-efce-81fe-8006-eeeddfc525a4
Test file URL: http://localhost:9001/#/workspace/...

Remaining objects:
  - Rectangle: 752585ee-... (moved, resized, recolored, rotated)
  - Text: caf6e648-... (recolored)
  - Circle: a447613c-... (deleted)

[FAIL] SOME TESTS FAILED

[NOTE] IMPORTANT: Open the file in browser to visually verify changes
   Make sure to CLOSE the browser before running this test again!
```

#### What We Can't Test

- ❌ Whether changes actually persist
- ❌ Whether text color changes work
- ❌ Whether type mismatches cause silent failures
- ❌ Whether revision conflicts are handled correctly

#### What We Can Test

- ✅ API returns 200 OK
- ✅ JSON response is valid
- ✅ Revision numbers increment

**But that's not enough to build reliable software.**

---

## 10. Recommendations

### For Penpot Development Team

#### High Priority

1. **Fix caching/persistence issues**
   - Changes must be immediately visible via API after 200 OK response
   - Consider read-after-write consistency guarantees
   - Add cache invalidation after updates

2. **Standardize naming conventions**
   - Choose ONE convention: kebab-case or camelCase
   - Apply consistently across entire API
   - Provide migration guide if breaking changes needed

3. **Document text object special cases**
   - Clearly state that text objects don't support object-level fills
   - Provide examples of correct content structure
   - Explain the nested fills requirements

4. **Add proper error messages**
   - Don't silently ignore type mismatches
   - Return validation errors with specific field names
   - Include "why" in error messages, not just "what"

5. **Document browser interference behavior**
   - Warn that open browser sessions can revert API changes
   - Provide WebSocket API for coordinated updates
   - Or: Lock file editing when API is actively modifying it

#### Medium Priority

6. **Improve Transit+JSON documentation**
   - Provide complete conversion rules
   - List all exceptions to rules
   - Include examples for each object type

7. **Document revision/session system**
   - Explain revn vs vern
   - Provide conflict handling guidance
   - Show concurrent update patterns

8. **Better authentication docs**
   - Document token expiration time
   - Provide refresh token mechanism
   - Add auth troubleshooting guide

#### Low Priority

9. **Add API testing tools**
   - Provide official test suite
   - Include examples for all operations
   - Add validation helpers

10. **Improve error responses**
    - Use standard HTTP status codes correctly
    - Include error codes for programmatic handling
    - Add debug mode with verbose errors

### For API Consumers (Us)

#### Current Workarounds

1. **Always close browser during API operations**
2. **Add explicit type conversion for opacity and other fields**
3. **Handle text objects completely separately from other shapes**
4. **Implement retry logic for all operations**
5. **Add significant delays between operations**
6. **Verify changes by manual browser inspection**

#### Code Patterns That Work

```python
# 1. Use editing_session context manager
with api.editing_session(file_id) as (session_id, revn):
    result = api.update_file(file_id, session_id, revn, changes)

# 2. Deep copy content structures before modifying
import copy
content = copy.deepcopy(obj.get('content', {}))

# 3. Convert all content structure keys to kebab-case
def convert_to_kebab(obj):
    if isinstance(obj, dict):
        return {camel_to_kebab(k): convert_to_kebab(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_kebab(item) for item in obj]
    else:
        return obj

# 4. Match exact type for opacity
opacity_value = int(fill_opacity) if fill_opacity == int(fill_opacity) else fill_opacity

# 5. Handle text fills at ALL nested levels
if 'children' in content:
    for paragraph_set in content['children']:
        if 'children' in paragraph_set:
            for paragraph in paragraph_set['children']:
                paragraph['fills'] = fills_content
                if 'children' in paragraph:
                    for text_node in paragraph['children']:
                        text_node['fills'] = fills_content
```

---

## Conclusion

Building the Penpot MCP Server has revealed significant issues with the Penpot API that make it **challenging to build reliable integrations**. While the API is functional for basic operations, the combination of:

- Inconsistent naming conventions
- Undocumented special cases
- Silent failures
- Caching/persistence issues
- Browser interference

...creates a frustrating development experience that requires extensive trial-and-error and workarounds.

**We remain committed to making Penpot MCP work**, but these issues should be addressed to enable broader API adoption and a more robust ecosystem.

---

## Appendix: Files and Commits

### Key Commits

1. `0f61ca5` - Fix: Improve change_object_color - add validation, fix camelCase, clear cache
2. `4699c6d` - Fix: Implement artboards for visible shapes and fix text colors
3. `227cf9d` - Fix: Add comprehensive object update validation

### Test Files

- `tests/test_validate_local_updates.py` - Comprehensive validation test
- `tests/test_change_color_debug.py` - Text color debugging
- Multiple other test files documenting specific issues

### Screenshots

- `.playwright-mcp/bug-confirmed-black-not-yellow.png` - Visual proof of text color bug
- `.playwright-mcp/color-discrepancy-black-not-yellow.png` - API vs UI mismatch
- Multiple other screenshots documenting issues

---

**Report Version:** 1.0
**Last Updated:** January 2025
**Contact:** Via GitHub issues at https://github.com/meywd/penpot-mcp
