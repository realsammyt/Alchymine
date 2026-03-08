# Intake & Profile Persistence Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix intake and profile data not persisting correctly — users complete intake but data doesn't survive across sessions or devices.

**Architecture:** Dual-path intake persistence: (1) `PUT /profile/{id}/intake` on form submit (best-effort), (2) `POST /reports` side-effect persists intake+assessment to DB. Both paths have silent failure modes. Fix the API to properly handle errors and ensure the User row exists before upserting intake data. Fix the frontend to surface errors instead of silently swallowing them.

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL, Next.js 15 (App Router), pytest-asyncio

**GitHub Issue:** #115

---

## Root Cause Analysis

Three silent failure points prevent intake data from persisting:

1. **`reports.py:114-128`** — Bare `except Exception` swallows all intake persistence errors. If `update_layer` fails (user row missing, constraint violation, encryption key error), the report returns 202 but intake data is lost.

2. **`intake/page.tsx:202`** — `saveIntake(...).catch(() => {})` fire-and-forgets with no user feedback. If the API call fails, data exists only in sessionStorage.

3. **`intake/page.tsx:155` and `assessment/page.tsx:52`** — `getProfile` catch blocks treat ALL errors (including 500s) as "no profile yet" and silently redirect or ignore.

The most likely production failure: `update_layer` raises `LookupError("No user")` because the User row doesn't exist for the JWT sub, and the broad except swallows it.

---

## Task 1: Write failing tests for intake persistence via POST /reports

**Files:**

- Modify: `tests/api/test_reports_router.py`

**Step 1: Seed a User row in the test fixture**

The existing tests never create a User row for `user-1`. The `update_layer` call in `reports.py` does `SELECT User WHERE id = user_id` and raises `LookupError` when no user exists. This means intake persistence has been silently failing in ALL existing tests.

Add to the test file, after the existing `session` fixture:

```python
@pytest_asyncio.fixture
async def seeded_client(engine, client):
    """Client with a pre-seeded user row so update_layer can find it."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        from alchymine.db.models import User
        user = User(id=_TEST_USER_ID, email="test@example.com", password_hash="hashed")
        sess.add(user)
        await sess.commit()
    return client
```

**Step 2: Write test — intake data persists to DB via POST /reports**

```python
class TestIntakePersistence:
    """Tests for intake data persistence side-effect of POST /reports."""

    def test_post_reports_persists_intake_to_db(self, seeded_client, engine):
        """POST /reports should persist intake data to the intake_data table."""
        payload = {
            "intake": {
                "full_name": "Test User",
                "birth_date": "1990-05-15",
                "birth_time": "14:30",
                "birth_city": "Portland",
                "intention": "career",
                "intentions": ["career", "wealth"],
                "assessment_responses": {"bf_e1": 4, "bf_e2": 3, "bf_a1": 5},
            },
            "user_input": "Generate my report",
        }
        resp = seeded_client.post("/api/v1/reports", json=payload)
        assert resp.status_code == 202

        import asyncio
        from sqlalchemy import select as sa_select

        async def _verify():
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as sess:
                from alchymine.db.models import IntakeData
                result = await sess.execute(
                    sa_select(IntakeData).where(IntakeData.user_id == _TEST_USER_ID)
                )
                intake = result.scalar_one_or_none()
                assert intake is not None, "Intake data was NOT persisted to DB"
                assert intake.full_name == "Test User"
                assert intake.assessment_responses == {"bf_e1": 4, "bf_e2": 3, "bf_a1": 5}
                assert intake.intention == "career"

        asyncio.get_event_loop().run_until_complete(_verify())

    def test_post_reports_without_user_row_still_returns_202(self, client):
        """POST /reports should return 202 even if intake persist fails (no user row)."""
        resp = client.post("/api/v1/reports", json=_valid_report_payload())
        assert resp.status_code == 202

    def test_post_reports_intake_persist_logs_on_failure(self, client, caplog):
        """When intake persist fails, it should log a warning with the exception details."""
        import logging
        with caplog.at_level(logging.WARNING):
            client.post("/api/v1/reports", json=_valid_report_payload())
        assert any("Failed to persist intake" in r.message for r in caplog.records)
```

**Step 3: Run tests to verify they fail**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reports_router.py::TestIntakePersistence -v --tb=short`
Expected: `test_post_reports_persists_intake_to_db` FAILS (intake data not persisted because current code swallows the LookupError)

**Step 4: Commit**

```bash
git add tests/api/test_reports_router.py
git commit -m "test: add failing tests for intake persistence via POST /reports"
```

---

## Task 2: Write failing test for cross-session profile retrieval

**Files:**

- Modify: `tests/api/test_reports_router.py`

**Step 1: Write test — intake data readable via GET /profile after POST /reports**

```python
    def test_intake_retrievable_via_profile_after_report(self, seeded_client, engine):
        """After POST /reports, GET /profile/{id} should return the saved intake data."""
        payload = {
            "intake": {
                "full_name": "Cross Device User",
                "birth_date": "1985-12-01",
                "intention": "family",
                "intentions": ["family"],
                "assessment_responses": {"bf_e1": 3},
            },
            "user_input": "Generate report",
        }
        resp = seeded_client.post("/api/v1/reports", json=payload)
        assert resp.status_code == 202

        # Now retrieve the profile
        profile_resp = seeded_client.get(f"/api/v1/profile/{_TEST_USER_ID}")
        assert profile_resp.status_code == 200
        data = profile_resp.json()
        assert data["intake"] is not None
        assert data["intake"]["full_name"] == "Cross Device User"
        assert data["intake"]["birth_date"] == "1985-12-01"
        assert data["intake"]["assessment_responses"] == {"bf_e1": 3}
```

**Step 2: Run test to verify it fails**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reports_router.py::TestIntakePersistence::test_intake_retrievable_via_profile_after_report -v --tb=short`
Expected: FAIL (intake not persisted, so profile returns intake=None or 404)

**Step 3: Commit**

```bash
git add tests/api/test_reports_router.py
git commit -m "test: add failing test for cross-session intake retrieval"
```

---

## Task 3: Fix intake persistence in reports.py

**Files:**

- Modify: `alchymine/api/routers/reports.py:112-128`

**Step 1: Replace the bare except with proper error handling and logging**

Replace lines 112-128 with:

```python
    # Persist the intake data to the user's profile so it survives across
    # devices and sessions (sessionStorage is browser-tab-scoped).
    try:
        intake_persist = request.intake.model_dump(mode="json")
        # Convert date/time strings back to proper types for the ORM
        from datetime import date as date_type
        from datetime import time as time_type

        intake_persist["birth_date"] = date_type.fromisoformat(intake_persist["birth_date"])
        if intake_persist.get("birth_time"):
            intake_persist["birth_time"] = time_type.fromisoformat(intake_persist["birth_time"])
        else:
            intake_persist["birth_time"] = None
        # Convert intention enum value to plain string
        if hasattr(intake_persist.get("intention"), "value"):
            intake_persist["intention"] = intake_persist["intention"]
        await repository.update_layer(session, current_user["sub"], "intake", intake_persist)
    except LookupError:
        # User row doesn't exist yet — this can happen if JWT sub doesn't
        # match a DB user (e.g., user was deleted but token is still valid).
        logger.warning(
            "Cannot persist intake for user %s: user row not found in DB",
            current_user["sub"],
        )
    except Exception:
        logger.exception(
            "Failed to persist intake data for user %s",
            current_user["sub"],
        )
```

Key changes:

- `LookupError` gets a specific, clear log message
- Other exceptions use `logger.exception()` (includes traceback) instead of `logger.warning()`
- `birth_time` explicitly set to `None` when empty (prevents KeyError in edge cases)

**Step 2: Add LookupError import at top of file if not present**

Verify `LookupError` is a builtin (it is — no import needed).

**Step 3: Run the tests**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reports_router.py::TestIntakePersistence -v --tb=short`
Expected: `test_post_reports_persists_intake_to_db` PASSES, `test_intake_retrievable_via_profile_after_report` PASSES

**Step 4: Run full reports test suite**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reports_router.py -v --tb=short`
Expected: All existing tests still pass

**Step 5: Commit**

```bash
git add alchymine/api/routers/reports.py
git commit -m "fix: stop silently swallowing intake persistence errors in POST /reports"
```

---

## Task 4: Fix frontend error handling for saveIntake

**Files:**

- Modify: `alchymine/web/src/app/discover/intake/page.tsx:194-202`

**Step 1: Add console.warn on saveIntake failure instead of silent swallow**

Replace:

```typescript
saveIntake(user.id, {
  full_name: formData.fullName,
  birth_date: formData.birthDate,
  birth_time: formData.birthTime || null,
  birth_city: formData.birthCity || null,
  intention: formData.intentions[0],
  intentions: formData.intentions,
}).catch(() => {});
```

With:

```typescript
saveIntake(user.id, {
  full_name: formData.fullName,
  birth_date: formData.birthDate,
  birth_time: formData.birthTime || null,
  birth_city: formData.birthCity || null,
  intention: formData.intentions[0],
  intentions: formData.intentions,
}).catch((err) => {
  console.warn(
    "Failed to save intake to server (will retry on report submit):",
    err,
  );
});
```

This is intentionally NOT blocking — the user should still proceed to assessment. The `POST /reports` call is the authoritative persist. But we no longer silently swallow the error.

**Step 2: Commit**

```bash
git add alchymine/web/src/app/discover/intake/page.tsx
git commit -m "fix: log saveIntake failures instead of silently swallowing"
```

---

## Task 5: Fix frontend getProfile error handling

**Files:**

- Modify: `alchymine/web/src/app/discover/intake/page.tsx:139-157`
- Modify: `alchymine/web/src/app/discover/assessment/page.tsx:34-54`

**Step 1: Distinguish 404 from server errors in intake page**

Replace the intake page's getProfile catch block:

```typescript
      .catch(() => {
        // No saved profile yet — that's fine, user fills in fresh
      });
```

With:

```typescript
      .catch((err) => {
        // 404 = no saved profile yet, which is normal for new users.
        // Other errors (500, network) should be logged for debugging.
        if (err?.status !== 404) {
          console.warn("Failed to load profile:", err);
        }
      });
```

**Step 2: Distinguish 404 from server errors in assessment page**

Replace the assessment page's getProfile catch block:

```typescript
      .catch(() => {
        router.replace("/discover/intake");
      });
```

With:

```typescript
      .catch((err) => {
        // Only redirect to intake if the profile truly doesn't exist (404).
        // On transient errors (500, network), stay on the page — sessionStorage
        // may have the data from the previous page.
        if (err?.status === 404) {
          router.replace("/discover/intake");
        } else {
          console.warn("Failed to load profile (non-404):", err);
        }
      });
```

**Step 3: Check that api.ts getProfile throws errors with status property**

Read `alchymine/web/src/lib/api.ts` and verify the `getProfile` function throws an error object that includes a `status` property. If not, update the fetch wrapper to include it.

**Step 4: Commit**

```bash
git add alchymine/web/src/app/discover/intake/page.tsx alchymine/web/src/app/discover/assessment/page.tsx
git commit -m "fix: distinguish 404 from server errors in profile loading"
```

---

## Task 6: Run full test suite and verify

**Step 1: Run Python tests**

Run: `D:/Python/Python311/python.exe -m pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Run frontend build**

Run: `cd alchymine/web && npm run build`
Expected: Build succeeds with no type errors

**Step 3: Run frontend lint**

Run: `cd alchymine/web && npm run lint && npm run type-check`
Expected: No lint or type errors

**Step 4: Run Python lint**

Run: `ruff check alchymine/ && ruff format --check alchymine/`
Expected: No lint errors

**Step 5: Commit any formatting fixes**

```bash
git add -A
git commit -m "chore: formatting fixes"
```

---

## Task 7: Create PR and update GitHub issue

**Step 1: Push branch and create PR**

```bash
git push -u origin fix/intake-persistence
gh pr create -R realsammyt/Alchymine \
  --title "fix: intake and profile data persistence (#115)" \
  --body "..."
```

**Step 2: Comment on issue #115**

```bash
gh issue comment 115 -R realsammyt/Alchymine \
  --body "✅ Fix submitted in PR #XXX. Root cause: bare except Exception in reports.py swallowed all intake persistence errors. Fix: proper error handling, logging with tracebacks, frontend error surfacing."
```

---

## Summary of Changes

| File                                                 | Change                                            | Why                                                      |
| ---------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------- |
| `alchymine/api/routers/reports.py`                   | Replace bare except with specific error handling  | Stop silently swallowing intake persistence failures     |
| `tests/api/test_reports_router.py`                   | Add 3 tests for intake persistence                | Verify data actually persists to DB and is retrievable   |
| `alchymine/web/src/app/discover/intake/page.tsx`     | Log saveIntake failures, distinguish 404 from 500 | Surface errors for debugging, don't mask server failures |
| `alchymine/web/src/app/discover/assessment/page.tsx` | Don't redirect on transient server errors         | Only redirect to intake on genuine 404, not on 500s      |
