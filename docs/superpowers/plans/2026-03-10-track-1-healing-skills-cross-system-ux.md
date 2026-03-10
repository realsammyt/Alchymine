# Track 1: Healing-Swarm-Skills + Cross-System UX — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate the healing-swarm-skills YAML corpus, wire MCP HTTP/SSE transport so external agents can call it, surface all 7 cross-system bridges in the frontend, and build the interactive healing/journal UX needed to close the "Healing + UX" track of the 90-day roadmap.

**Architecture:**

- Skills live in `alchymine/engine/healing/skills/` as individual YAML files loaded at startup into a `SkillRegistry` singleton
- MCP transport wraps the existing in-process `MCPServer` with a FastAPI `APIRouter` that speaks the JSON-RPC MCP protocol over HTTP + SSE
- Cross-system bridges are exposed through a new `/api/v1/bridges` router and a `CrossSystemBridgePanel` React component reused across all 5 system pages
- Journal is already wired (API + UI both exist); the gap is edit/delete UI and mood trend chart
- Spiral integration calls `/api/v1/spiral/route` and surfaces the result in a `SpiralRecommendation` banner on each system page

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Next.js 15 App Router, React 18, TypeScript, Tailwind CSS, pytest, Vitest/React Testing Library

---

## Sprint 1 (Weeks 1–2): Skills Loader + Schema

### Task 1.1 — Define skill YAML schema and write the loader

**Files:**

- Create: `alchymine/engine/healing/skills/schema.py`
- Create: `alchymine/engine/healing/skills/loader.py`
- Create: `alchymine/engine/healing/skills/__init__.py`
- Create: `tests/engine/test_skills_loader.py`

**Steps:**

- [ ] Define `HealingSkill` Pydantic model mirroring the upstream YAML structure:

  ```python
  # alchymine/engine/healing/skills/schema.py
  from pydantic import BaseModel, Field

  class HealingSkill(BaseModel):
      id: str
      modality: str
      title: str
      duration_minutes: int
      difficulty: str
      instructions: list[str]
      contraindications: list[str] = Field(default_factory=list)
      traditions: list[str] = Field(default_factory=list)
      evidence_level: str = "traditional"
      tags: list[str] = Field(default_factory=list)
  ```

- [ ] Write `SkillRegistry` in `loader.py`:

  ```python
  # alchymine/engine/healing/skills/loader.py
  import yaml
  from pathlib import Path
  from .schema import HealingSkill

  _SKILLS_DIR = Path(__file__).parent / "yaml"

  class SkillRegistry:
      def __init__(self) -> None:
          self._skills: dict[str, HealingSkill] = {}

      def load_from_dir(self, directory: Path = _SKILLS_DIR) -> int:
          for path in sorted(directory.glob("*.yaml")):
              data = yaml.safe_load(path.read_text(encoding="utf-8"))
              skill = HealingSkill.model_validate(data)
              self._skills[skill.id] = skill
          return len(self._skills)

      def get(self, skill_id: str) -> HealingSkill | None:
          return self._skills.get(skill_id)

      def by_modality(self, modality: str) -> list[HealingSkill]:
          return [s for s in self._skills.values() if s.modality == modality]

      def all(self) -> list[HealingSkill]:
          return list(self._skills.values())

  registry = SkillRegistry()
  ```

- [ ] Write failing tests first:

  ```python
  # tests/engine/test_skills_loader.py
  def test_registry_loads_yaml_files(tmp_path):
      yaml_dir = tmp_path / "yaml"
      yaml_dir.mkdir()
      (yaml_dir / "bw_001.yaml").write_text("""
  id: bw_001
  modality: breathwork
  title: Box Breathing Baseline
  duration_minutes: 5
  difficulty: foundation
  instructions:
    - Inhale for 4 counts
  """)
      from alchymine.engine.healing.skills.loader import SkillRegistry
      reg = SkillRegistry()
      count = reg.load_from_dir(yaml_dir)
      assert count == 1
      skill = reg.get("bw_001")
      assert skill is not None
      assert skill.modality == "breathwork"

  def test_by_modality_filter(tmp_path):
      ...  # similar fixture, 2 modalities, verify filter
  ```

- [ ] Run: `pytest tests/engine/test_skills_loader.py -v` — expect failure on missing `yaml/` dir
- [ ] Create `alchymine/engine/healing/skills/yaml/.gitkeep`
- [ ] Run tests again — they should pass with the fixture `tmp_path` approach

**Commit:** `feat(skills): add HealingSkill schema and SkillRegistry loader`

---

### Task 1.2 — Populate 15 seed YAML skills (one per modality)

**Files:**

- Create: `alchymine/engine/healing/skills/yaml/bw_001.yaml` through `bw_003.yaml`
- Create: one seed file per modality (15 total; breathwork gets 3, others get 1 each)

**Steps:**

- [ ] Create `alchymine/engine/healing/skills/yaml/bw_001.yaml`:

  ```yaml
  id: bw_001
  modality: breathwork
  title: Box Breathing Baseline
  duration_minutes: 5
  difficulty: foundation
  instructions:
    - Find a comfortable seated position and close your eyes
    - Inhale slowly through your nose for 4 counts
    - Hold your breath for 4 counts
    - Exhale slowly through your mouth for 4 counts
    - Hold empty for 4 counts
    - Repeat for 6 cycles
  contraindications:
    - severe asthma
    - panic disorder
  traditions:
    - Pranayama (Yogic)
  evidence_level: strong
  tags: [calm, focus, foundation]
  ```

- [ ] Create seed files for remaining 14 modalities following the same structure. One file each:
      `coherence_001.yaml`, `language_001.yaml`, `resilience_001.yaml`, `consciousness_001.yaml`,
      `sound_001.yaml`, `somatic_001.yaml`, `sleep_001.yaml`, `nature_001.yaml`,
      `pni_001.yaml`, `grief_001.yaml`, `water_001.yaml`, `community_001.yaml`,
      `expressive_001.yaml`, `inquiry_001.yaml`

- [ ] Write test verifying registry loads all 15+ seed files at module import:

  ```python
  def test_module_level_registry_has_seeds():
      from alchymine.engine.healing.skills.loader import registry
      registry.load_from_dir()  # loads from package yaml/ dir
      assert len(registry.all()) >= 15
  ```

- [ ] Run: `pytest tests/engine/test_skills_loader.py -v`

**Commit:** `feat(skills): seed 15 healing skill YAML files, one per modality`

---

### Task 1.3 — Wire skills into healing API

**Files:**

- Modify: `alchymine/api/routers/healing.py`
- Create: `tests/api/test_healing_skills.py`

**Steps:**

- [ ] Add two new endpoints to `alchymine/api/routers/healing.py`:

  ```python
  from alchymine.engine.healing.skills.loader import registry as skill_registry
  from alchymine.engine.healing.skills.schema import HealingSkill

  class SkillResponse(BaseModel):
      id: str
      modality: str
      title: str
      duration_minutes: int
      difficulty: str
      instructions: list[str]
      contraindications: list[str]
      traditions: list[str]
      evidence_level: str
      tags: list[str]

  @router.get("/healing/skills")
  async def list_skills(
      modality: str | None = Query(None),
      current_user: dict = Depends(get_current_user),
  ) -> list[SkillResponse]:
      skills = skill_registry.by_modality(modality) if modality else skill_registry.all()
      return [SkillResponse(**s.model_dump()) for s in skills]

  @router.get("/healing/skills/{skill_id}")
  async def get_skill(
      skill_id: str,
      current_user: dict = Depends(get_current_user),
  ) -> SkillResponse:
      skill = skill_registry.get(skill_id)
      if skill is None:
          raise HTTPException(status_code=404, detail="Skill not found")
      return SkillResponse(**skill.model_dump())
  ```

- [ ] Write API tests in `tests/api/test_healing_skills.py` following the pattern in `tests/api/test_journal.py` (TestClient with SQLite fixture)

- [ ] Run: `pytest tests/api/test_healing_skills.py -v`
- [ ] Run: `ruff check alchymine/ && ruff format --check alchymine/`

**Commit:** `feat(api): expose /healing/skills endpoints for skill registry`

---

## Sprint 2 (Weeks 3–4): MCP HTTP/SSE Transport

### Task 2.1 — MCP transport router

**Files:**

- Create: `alchymine/mcp/transport.py`
- Modify: `alchymine/api/main.py`
- Create: `tests/mcp/test_transport.py`

**Steps:**

- [ ] Write failing test first:

  ```python
  # tests/mcp/test_transport.py
  def test_initialize_returns_server_info(mcp_client):
      resp = mcp_client.post("/mcp/healing", json={
          "jsonrpc": "2.0", "id": 1,
          "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "test"}}
      })
      assert resp.status_code == 200
      body = resp.json()
      assert body["result"]["serverInfo"]["name"] == "alchymine-healing"

  def test_tools_list(mcp_client):
      resp = mcp_client.post("/mcp/healing", json={
          "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
      })
      assert resp.status_code == 200
      tools = resp.json()["result"]["tools"]
      assert any(t["name"] == "detect_crisis" for t in tools)
  ```

- [ ] Implement `alchymine/mcp/transport.py`:

  ```python
  # alchymine/mcp/transport.py
  from fastapi import APIRouter
  from fastapi.responses import JSONResponse
  from .base import MCPServer

  def make_mcp_router(server: MCPServer, prefix: str) -> APIRouter:
      router = APIRouter(prefix=f"/mcp/{prefix}", tags=["mcp"])

      @router.post("")
      async def handle_jsonrpc(body: dict) -> JSONResponse:
          method = body.get("method", "")
          req_id = body.get("id")

          if method == "initialize":
              return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {
                  "protocolVersion": "2024-11-05",
                  "capabilities": {"tools": {}, "resources": {}},
                  "serverInfo": {"name": server.name, "version": server.version},
              }})

          if method == "tools/list":
              return JSONResponse({"jsonrpc": "2.0", "id": req_id,
                  "result": {"tools": server.list_tools()}})

          if method == "tools/call":
              params = body.get("params", {})
              try:
                  result = await server.call_tool(params["name"], params.get("arguments", {}))
                  return JSONResponse({"jsonrpc": "2.0", "id": req_id,
                      "result": {"content": [{"type": "text", "text": str(result)}]}})
              except ValueError as exc:
                  return JSONResponse({"jsonrpc": "2.0", "id": req_id,
                      "error": {"code": -32602, "message": str(exc)}})

          if method == "resources/list":
              return JSONResponse({"jsonrpc": "2.0", "id": req_id,
                  "result": {"resources": server.list_resources()}})

          return JSONResponse({"jsonrpc": "2.0", "id": req_id,
              "error": {"code": -32601, "message": f"Unknown method: {method}"}})

      return router
  ```

- [ ] Mount the five MCP routers in `alchymine/api/main.py`:

  ```python
  from alchymine.mcp.transport import make_mcp_router
  from alchymine.mcp.healing_server import server as healing_mcp
  from alchymine.mcp.intelligence_server import server as intelligence_mcp
  # ... etc for all 5

  app.include_router(make_mcp_router(healing_mcp, "healing"))
  app.include_router(make_mcp_router(intelligence_mcp, "intelligence"))
  # ... etc
  ```

- [ ] Run: `pytest tests/mcp/test_transport.py -v`
- [ ] Run: `ruff check alchymine/ && ruff format --check alchymine/`

**Commit:** `feat(mcp): add JSON-RPC HTTP transport for all 5 MCP servers`

---

### Task 2.2 — Register skill tools in healing MCP server

**Files:**

- Modify: `alchymine/mcp/healing_server.py`
- Modify: `tests/mcp/test_healing_server.py`

**Steps:**

- [ ] Add `list_skills` and `get_skill` tools to `alchymine/mcp/healing_server.py`:

  ```python
  from alchymine.engine.healing.skills.loader import registry as skill_registry

  @server.tool(
      name="list_skills",
      description="List healing skills, optionally filtered by modality.",
      input_schema={
          "type": "object",
          "properties": {"modality": {"type": "string", "description": "Optional modality filter"}},
          "required": [],
      },
  )
  def list_skills_tool(modality: str | None = None) -> list[dict]:
      skills = skill_registry.by_modality(modality) if modality else skill_registry.all()
      return [s.model_dump() for s in skills]
  ```

- [ ] Update `test_lists_all_tools` to include `list_skills` and `get_skill`
- [ ] Run: `pytest tests/mcp/test_healing_server.py -v`

**Commit:** `feat(mcp): expose skill registry tools in healing MCP server`

---

## Sprint 3 (Weeks 5–6): Cross-System Bridges Backend

### Task 3.1 — Bridges router

**Files:**

- Create: `alchymine/engine/bridges/__init__.py`
- Create: `alchymine/engine/bridges/registry.py`
- Create: `alchymine/api/routers/bridges.py`
- Modify: `alchymine/api/main.py`
- Create: `tests/api/test_bridges.py`

**Steps:**

- [ ] Define the 7 bridges (XS-01 through XS-07) in `alchymine/engine/bridges/registry.py`:

  ```python
  from dataclasses import dataclass

  @dataclass(frozen=True)
  class BridgeDefinition:
      id: str            # "XS-01"
      from_system: str   # "healing"
      to_system: str     # "perspective"
      title: str
      description: str
      mechanism: str     # how the connection works
      action_label: str  # CTA text for frontend
      action_href: str   # e.g. "/perspective"

  BRIDGES: list[BridgeDefinition] = [
      BridgeDefinition(
          id="XS-01", from_system="healing", to_system="perspective",
          title="Healing Primes Perspective",
          description="Breathwork and somatic work soften rigid thinking patterns, making Kegan stage transitions more accessible.",
          mechanism="Breathwork → reduced amygdala reactivity → increased cognitive flexibility",
          action_label="Explore Perspective Prism",
          action_href="/perspective",
      ),
      BridgeDefinition(
          id="XS-02", from_system="intelligence", to_system="healing",
          title="Numerology Selects Modality",
          description="Your Life Path number has strong affinity with specific healing traditions. The engine pre-selects modalities aligned to your number.",
          mechanism="Life Path → archetype affinity weights → modality scoring boost",
          action_label="See Your Modalities",
          action_href="/healing",
      ),
      BridgeDefinition(
          id="XS-03", from_system="wealth", to_system="healing",
          title="Financial Stress → Somatic Release",
          description="Money anxiety activates the same stress circuits as physical threat. Somatic and breathwork practices directly address wealth-related cortisol.",
          mechanism="Financial anxiety → HPA axis → somatic/breathwork protocols target cortisol",
          action_label="Start Somatic Practice",
          action_href="/healing",
      ),
      BridgeDefinition(
          id="XS-04", from_system="creative", to_system="healing",
          title="Creative Expression Heals",
          description="Expressive healing modalities use art, movement, and writing to access pre-verbal experience — the same materials your Creative system works with.",
          mechanism="Creative output → expressive healing modalities → embodied integration",
          action_label="Explore Expressive Healing",
          action_href="/healing",
      ),
      BridgeDefinition(
          id="XS-05", from_system="perspective", to_system="wealth",
          title="Kegan Stage Unlocks Money Mindset",
          description="Stage 4 development (self-authoring) is the psychological prerequisite for the generative wealth mindset. Perspective work directly enables wealth expansion.",
          mechanism="Kegan 4 attainment → reduced external validation seeking → wealth mindset access",
          action_label="Explore Wealth",
          action_href="/wealth",
      ),
      BridgeDefinition(
          id="XS-06", from_system="healing", to_system="creative",
          title="Healed Expression Flows",
          description="Clearing somatic blocks through healing practices removes the psychological censorship that suppresses creative output.",
          mechanism="Somatic healing → nervous system regulation → creative inhibition reduction",
          action_label="Explore Creative",
          action_href="/creative",
      ),
      BridgeDefinition(
          id="XS-07", from_system="intelligence", to_system="perspective",
          title="Archetype Shapes Stage Pathway",
          description="Your Jungian archetype has natural affinity with specific Kegan developmental stages. Intelligence data fast-tracks your perspective growth path.",
          mechanism="Archetype → Kegan stage attractor → personalized perspective curriculum",
          action_label="Explore Perspective",
          action_href="/perspective",
      ),
  ]

  def get_bridges_for_system(system: str) -> list[BridgeDefinition]:
      return [b for b in BRIDGES if b.from_system == system or b.to_system == system]
  ```

- [ ] Write `alchymine/api/routers/bridges.py` with GET endpoints:

  ```python
  @router.get("/bridges")
  async def list_bridges(
      system: str | None = Query(None),
      current_user: dict = Depends(get_current_user),
  ) -> list[dict]:
      bridges = get_bridges_for_system(system) if system else BRIDGES
      return [dataclasses.asdict(b) for b in bridges]
  ```

- [ ] Add to `main.py`: `app.include_router(bridges_router, prefix="/api/v1")`
- [ ] Write tests verifying 200 responses, system filter, and all 7 bridges present
- [ ] Run: `pytest tests/api/test_bridges.py -v`

**Commit:** `feat(bridges): add XS-01 through XS-07 definitions and /bridges API router`

---

## Sprint 4 (Weeks 7–8): Cross-System Bridges Frontend

### Task 4.1 — CrossSystemBridgePanel component

**Files:**

- Create: `alchymine/web/src/components/shared/CrossSystemBridgePanel.tsx`
- Create: `alchymine/web/src/components/shared/__tests__/CrossSystemBridgePanel.test.tsx`

**Steps:**

- [ ] Write the component:

  ```typescript
  // alchymine/web/src/components/shared/CrossSystemBridgePanel.tsx
  "use client";
  import Link from "next/link";

  interface Bridge {
    id: string;
    from_system: string;
    to_system: string;
    title: string;
    description: string;
    action_label: string;
    action_href: string;
  }

  interface Props {
    currentSystem: string;
    bridges: Bridge[];
  }

  export default function CrossSystemBridgePanel({ currentSystem, bridges }: Props) {
    if (bridges.length === 0) return null;
    return (
      <section aria-labelledby="bridges-heading" data-testid="bridge-panel">
        <h2 id="bridges-heading" className="section-heading-sm mb-2">
          System Connections
        </h2>
        <hr className="rule-gold mb-6" aria-hidden="true" />
        <div className="grid sm:grid-cols-2 gap-4">
          {bridges.map((bridge) => {
            const isSource = bridge.from_system === currentSystem;
            const partner = isSource ? bridge.to_system : bridge.from_system;
            return (
              <div key={bridge.id} className="card-surface p-5 hover:glow-teal hover:-translate-y-1 transition-all duration-500">
                <p className="font-body text-[0.65rem] uppercase tracking-wider text-accent/60 mb-1">
                  {bridge.id} · {bridge.from_system} → {bridge.to_system}
                </p>
                <h3 className="font-display text-base font-light text-text/80 mb-2">
                  {bridge.title}
                </h3>
                <p className="font-body text-sm text-text/40 leading-relaxed mb-4">
                  {bridge.description}
                </p>
                <Link
                  href={bridge.action_href}
                  className="font-body text-xs text-accent underline underline-offset-2"
                >
                  {bridge.action_label} &rarr;
                </Link>
              </div>
            );
          })}
        </div>
      </section>
    );
  }
  ```

- [ ] Write Vitest/RTL test:

  ```typescript
  // ...test renders bridge cards, shows correct count, link has correct href
  ```

- [ ] Run: `cd alchymine/web && npm test -- --run CrossSystemBridgePanel`

**Commit:** `feat(ui): add CrossSystemBridgePanel component`

---

### Task 4.2 — Wire bridges panel into all 5 system pages

**Files:**

- Modify: `alchymine/web/src/lib/api.ts` (add `getBridges` function)
- Modify: `alchymine/web/src/app/healing/page.tsx`
- Modify: `alchymine/web/src/app/intelligence/page.tsx`
- Modify: `alchymine/web/src/app/wealth/page.tsx`
- Modify: `alchymine/web/src/app/creative/page.tsx`
- Modify: `alchymine/web/src/app/perspective/page.tsx`

**Steps:**

- [ ] Add to `alchymine/web/src/lib/api.ts`:

  ```typescript
  export interface Bridge {
    id: string;
    from_system: string;
    to_system: string;
    title: string;
    description: string;
    mechanism: string;
    action_label: string;
    action_href: string;
  }

  export async function getBridges(system?: string): Promise<Bridge[]> {
    const params = system ? `?system=${system}` : "";
    const res = await apiFetch(`/api/v1/bridges${params}`);
    return res.json();
  }
  ```

- [ ] In `healing/page.tsx`, add near the bottom (before the existing hardcoded Connections section, which should be removed):

  ```typescript
  const bridges = useApi<Bridge[]>(() => getBridges("healing"), []);
  // ...
  {bridges.data && bridges.data.length > 0 && (
    <MotionReveal>
      <CrossSystemBridgePanel currentSystem="healing" bridges={bridges.data} />
    </MotionReveal>
  )}
  ```

- [ ] Remove the hardcoded "Connected: Healing & Perspective" card from `healing/page.tsx` (it is now superseded by the dynamic panel)
- [ ] Repeat pattern for `intelligence`, `wealth`, `creative`, `perspective` pages
- [ ] Run: `cd alchymine/web && npm run type-check && npm run lint`

**Commit:** `feat(ui): wire CrossSystemBridgePanel into all 5 system pages`

---

## Sprint 5 (Weeks 9–10): Interactive Healing UX

### Task 5.1 — Skill detail drawer

**Files:**

- Create: `alchymine/web/src/components/shared/SkillDrawer.tsx`
- Modify: `alchymine/web/src/app/healing/page.tsx`

**Steps:**

- [ ] Write `SkillDrawer.tsx` — slide-in panel showing skill title, instructions as numbered steps, duration badge, evidence badge, traditions, contraindications. Uses `role="dialog"` with `aria-modal="true"`. Close on Escape and backdrop click.

- [ ] In `healing/page.tsx`, make modality cards clickable: clicking a modality opens the `SkillDrawer` for that modality's first skill. Fetch from `/api/v1/healing/skills?modality={name}` on demand (lazy).

- [ ] Write RTL test: renders drawer with skill instructions, close button focuses correctly

- [ ] Run: `cd alchymine/web && npm test -- --run SkillDrawer`

**Commit:** `feat(ui): add SkillDrawer component for healing skill detail`

---

### Task 5.2 — Guided breathwork with API-driven timing

**Files:**

- Modify: `alchymine/web/src/app/healing/page.tsx`
- Modify: `alchymine/web/src/components/shared/BreathworkTimer.tsx`

**Steps:**

- [ ] The existing `BreathworkTimer` uses hardcoded `PATTERNS`. Extend it to accept an optional `apiPattern` prop typed as the `BreathworkResponse` from the API.

- [ ] In the breathwork section of `healing/page.tsx`, add a "Personalized Pattern" card that fetches `/api/v1/healing/breathwork/{intention}` using the user's first intention from intake data (falls back to `health`). Shows alongside the 3 hardcoded patterns.

- [ ] Map the API response fields (`inhale_seconds`, `hold_seconds`, `exhale_seconds`, `hold_empty_seconds`, `cycles`) to `BreathworkPhase[]` and pass into `BreathworkTimer`.

- [ ] Ensure `logActivity` is called on completion as existing patterns already do.

- [ ] Run: `cd alchymine/web && npm run type-check`

**Commit:** `feat(ui): wire API-driven breathwork pattern into healing page`

---

### Task 5.3 — Journal edit and delete UI

**Files:**

- Modify: `alchymine/web/src/app/journal/page.tsx`
- Modify: `alchymine/web/src/lib/api.ts`

**Steps:**

- [ ] Add `updateJournalEntry` and `deleteJournalEntry` to `alchymine/web/src/lib/api.ts`:

  ```typescript
  export async function updateJournalEntry(
    id: string,
    data: Partial<JournalEntryCreate>,
  ): Promise<JournalEntry> {
    const res = await apiFetch(`/api/v1/journal/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    return res.json();
  }

  export async function deleteJournalEntry(id: string): Promise<void> {
    await apiFetch(`/api/v1/journal/${id}`, { method: "DELETE" });
  }
  ```

- [ ] In the entry detail modal in `journal/page.tsx`, add "Edit" and "Delete" buttons in the modal footer.
  - "Edit" toggles inline edit mode for `title` and `content` fields within the modal
  - "Delete" shows a confirmation message before calling `deleteJournalEntry` and refreshing the list
  - Both update local state without requiring full page reload

- [ ] Run: `cd alchymine/web && npm run type-check && npm run lint`

**Commit:** `feat(ui): add edit and delete actions to journal entry modal`

---

### Task 5.4 — Mood trend sparkline

**Files:**

- Create: `alchymine/web/src/components/shared/MoodSparkline.tsx`
- Modify: `alchymine/web/src/app/journal/page.tsx`

**Steps:**

- [ ] Build `MoodSparkline` using a pure SVG polyline (no external charting library). Accepts `data: Array<{ date: string; score: number }>`. Renders a 200×40 inline SVG with the mood score trend, capped axis labels at 1 and 10, and a teal stroke.

- [ ] In `journal/page.tsx`, after the stats bar, add `<MoodSparkline>` populated from `entries.slice(0, 30).map(e => ({ date: e.created_at, score: e.mood_score ?? 5 }))`.

- [ ] Write a simple RTL test verifying the SVG renders with `role="img"` and an accessible `aria-label`.

- [ ] Run: `cd alchymine/web && npm test -- --run MoodSparkline`

**Commit:** `feat(ui): add MoodSparkline component to journal page`

---

## Sprint 6 (Weeks 11–12): Spiral Integration + Polish

### Task 6.1 — Spiral recommendation banner

**Files:**

- Create: `alchymine/web/src/components/shared/SpiralBanner.tsx`
- Modify: `alchymine/web/src/lib/api.ts` (add `getSpiralRoute` function)
- Modify: `alchymine/web/src/app/healing/page.tsx`

**Steps:**

- [ ] Add `getSpiralRoute` to `api.ts`:

  ```typescript
  export interface SpiralRouteResult {
    recommended_system: string;
    reason: string;
    confidence: number;
    next_steps: string[];
  }

  export async function getSpiralRoute(params: {
    intention: string;
    systems_engaged?: string[];
    life_path?: number | null;
  }): Promise<SpiralRouteResult> {
    const res = await apiFetch("/api/v1/spiral/route", {
      method: "POST",
      body: JSON.stringify(params),
    });
    return res.json();
  }
  ```

- [ ] Write `SpiralBanner.tsx` — a compact banner card showing the recommended next system, confidence percentage, and the first `next_step`. Includes a link to the recommended system's page. Renders nothing if `confidence < 0.4`.

- [ ] Wire into `healing/page.tsx`: fetch spiral recommendation using intake intention + `["healing"]` as `systems_engaged`. Show banner below the page header when data is available and recommendation is NOT `healing`.

- [ ] Run: `cd alchymine/web && npm run type-check && npm run lint`

**Commit:** `feat(ui): add SpiralBanner component and wire into healing page`

---

### Task 6.2 — healing-swarm-skills as git submodule (upstream integration)

**Files:**

- Modify: `.gitmodules` (new file)
- Modify: `pyproject.toml`
- Modify: `alchymine/engine/healing/skills/loader.py`

**Steps:**

- [ ] Add the upstream repo as a submodule:

  ```bash
  git submodule add https://github.com/realsammyt/healing-swarm-skills \
    alchymine/engine/healing/skills/upstream
  ```

- [ ] Update `loader.py` to try the upstream directory first, then fall back to the local `yaml/` seed files:

  ```python
  _UPSTREAM_DIR = Path(__file__).parent / "upstream" / "skills"
  _SEED_DIR = Path(__file__).parent / "yaml"

  def load_from_dir(self, directory: Path | None = None) -> int:
      target = directory or (_UPSTREAM_DIR if _UPSTREAM_DIR.exists() else _SEED_DIR)
      # existing glob logic
  ```

- [ ] Add to `pyproject.toml` under `[tool.pytest.ini_options]` or similar: document the submodule requirement. Do NOT declare it as a Python dependency (it is YAML data, not a package).

- [ ] Update CI (`.github/workflows/ci.yml`) to add `git submodule update --init --recursive` before the test step if not already present.

- [ ] Run: `pytest tests/engine/test_skills_loader.py -v`

**Commit:** `feat(skills): add healing-swarm-skills as git submodule with upstream fallback`

---

### Task 6.3 — Accessibility and final polish pass

**Files:**

- Modify: `alchymine/web/src/app/healing/page.tsx`
- Modify: `alchymine/web/src/app/journal/page.tsx`
- Modify: `alchymine/web/src/components/shared/CrossSystemBridgePanel.tsx`
- Modify: `alchymine/web/src/components/shared/SkillDrawer.tsx`

**Steps:**

- [ ] Audit all new interactive elements for `aria-label`, `role`, and keyboard navigation using `Tab`/`Escape`
- [ ] Verify focus trapping in `SkillDrawer` modal (focus must not escape the drawer while open)
- [ ] Ensure all new images and SVGs have `aria-hidden="true"` or a meaningful `alt`/`aria-label`
- [ ] Run: `cd alchymine/web && npm run build` — zero TypeScript errors required
- [ ] Run: `CELERY_ALWAYS_EAGER=true pytest tests/ -v --tb=short` — all tests must pass
- [ ] Run: `ruff check alchymine/ && ruff format --check alchymine/ && mypy alchymine/`

**Commit:** `chore(a11y): accessibility and polish pass on Track 1 UX components`

---

## Validation Checklist

Before marking Track 1 complete:

- [ ] `pytest tests/engine/test_skills_loader.py` — all pass
- [ ] `pytest tests/api/test_healing_skills.py` — all pass
- [ ] `pytest tests/api/test_bridges.py` — all pass
- [ ] `pytest tests/mcp/test_transport.py` — all pass
- [ ] `pytest tests/mcp/test_healing_server.py` — all pass (including new skill tools)
- [ ] `cd alchymine/web && npm test -- --run` — all component tests pass
- [ ] `cd alchymine/web && npm run build` — zero errors
- [ ] `ruff check alchymine/` — zero errors
- [ ] `ruff format --check alchymine/` — zero violations
- [ ] `mypy alchymine/` — no issues found
- [ ] Healing page shows CrossSystemBridgePanel with at least 2 bridges
- [ ] Journal page has edit/delete working end-to-end
- [ ] MCP `/mcp/healing` endpoint responds to `tools/list` with `detect_crisis`, `match_modalities`, `get_breathwork`, `list_skills`, `get_skill`
- [ ] Spiral banner appears on healing page when recommended system differs from healing

---

## File Index

| File                                                             | Status | Sprint  |
| ---------------------------------------------------------------- | ------ | ------- |
| `alchymine/engine/healing/skills/schema.py`                      | Create | 1       |
| `alchymine/engine/healing/skills/loader.py`                      | Create | 1       |
| `alchymine/engine/healing/skills/__init__.py`                    | Create | 1       |
| `alchymine/engine/healing/skills/yaml/*.yaml` (15+)              | Create | 1       |
| `alchymine/api/routers/healing.py`                               | Modify | 1       |
| `alchymine/mcp/transport.py`                                     | Create | 2       |
| `alchymine/mcp/healing_server.py`                                | Modify | 2       |
| `alchymine/api/main.py`                                          | Modify | 2, 3    |
| `alchymine/engine/bridges/__init__.py`                           | Create | 3       |
| `alchymine/engine/bridges/registry.py`                           | Create | 3       |
| `alchymine/api/routers/bridges.py`                               | Create | 3       |
| `alchymine/web/src/lib/api.ts`                                   | Modify | 4, 5, 6 |
| `alchymine/web/src/components/shared/CrossSystemBridgePanel.tsx` | Create | 4       |
| `alchymine/web/src/app/healing/page.tsx`                         | Modify | 4, 5, 6 |
| `alchymine/web/src/app/intelligence/page.tsx`                    | Modify | 4       |
| `alchymine/web/src/app/wealth/page.tsx`                          | Modify | 4       |
| `alchymine/web/src/app/creative/page.tsx`                        | Modify | 4       |
| `alchymine/web/src/app/perspective/page.tsx`                     | Modify | 4       |
| `alchymine/web/src/components/shared/SkillDrawer.tsx`            | Create | 5       |
| `alchymine/web/src/components/shared/MoodSparkline.tsx`          | Create | 5       |
| `alchymine/web/src/components/shared/SpiralBanner.tsx`           | Create | 6       |
| `alchymine/web/src/app/journal/page.tsx`                         | Modify | 5       |
| `.gitmodules`                                                    | Create | 6       |
| `tests/engine/test_skills_loader.py`                             | Create | 1       |
| `tests/api/test_healing_skills.py`                               | Create | 1       |
| `tests/mcp/test_transport.py`                                    | Create | 2       |
| `tests/api/test_bridges.py`                                      | Create | 3       |
