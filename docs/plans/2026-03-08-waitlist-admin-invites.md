# Waitlist Signup + Admin Panel Integration + Invite Emails

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire waitlist signups into the database, add admin panel management, and improve invite emails with code + expiry.

**Architecture:** New `WaitlistEntry` model stores signups. Admin panel gets a Waitlist tab for viewing/inviting. Invite emails show signup URL, raw code, and expiry. Signup page pre-fills code from URL param.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Next.js, Resend (email)

---

## Steps

### Step 1: DB Model — WaitlistEntry

- **Create:** `alchymine/db/models.py` (add model)
- Fields: id, email (unique), status (pending|invited|registered), invite_code_id (FK), notes, created_at, updated_at

### Step 2: Alembic Migration

- **Create:** migration `0008_add_waitlist_entries`

### Step 3: Public Waitlist API — `POST /auth/waitlist`

- **Modify:** `alchymine/api/routers/auth.py`
- Idempotent, no auth required, returns 200

### Step 4: Update Email Template

- **Modify:** `alchymine/email.py`
- Add `expires_at` param, show raw invite code + expiry in HTML

### Step 5: Pass Expiry to Email in Admin Invite

- **Modify:** `alchymine/api/routers/admin.py` — pass `expires_at` to `send_invitation_email`

### Step 6: Admin Waitlist API Endpoints

- **Modify:** `alchymine/api/routers/admin.py`
- `GET /admin/waitlist` — paginated list with status filter
- `POST /admin/waitlist/invite` — invite selected entries (create codes + send emails)
- `DELETE /admin/waitlist/{id}` — remove entry

### Step 7: Track Registered Status

- **Modify:** `alchymine/api/routers/auth.py` — update WaitlistEntry status on registration

### Step 8: Admin Waitlist UI Page

- **Create:** `alchymine/web/src/app/admin/waitlist/page.tsx`
- **Modify:** `alchymine/web/src/app/admin/layout.tsx` — add nav item

### Step 9: Frontend API Client

- **Modify:** `alchymine/web/src/lib/api.ts` — add waitlist functions

### Step 10: Landing Page — Wire Waitlist Form

- **Modify:** `alchymine/web/src/app/page.tsx` — replace localStorage with API call

### Step 11: Signup Page — Pre-fill Invite Code

- **Modify:** `alchymine/web/src/app/signup/page.tsx` — read `?invite=` URL param

### Step 12: Tests

- **Create:** `tests/api/test_waitlist.py`
- **Modify:** `tests/api/test_admin.py` — extend with waitlist admin tests
