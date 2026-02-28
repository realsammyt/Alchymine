/**
 * Alchymine API client — typed fetch wrappers for the FastAPI backend.
 */

const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BASE = `${API_URL}/api/v1`;

// ─── Shared types ────────────────────────────────────────────────────

export interface IntakePayload {
  full_name: string;
  birth_date: string; // YYYY-MM-DD
  birth_time?: string | null; // HH:MM or null
  birth_city?: string | null;
  intention: string;
  assessment_responses: Record<string, number>;
}

export interface ReportRequest {
  intake: IntakePayload;
  modules?: string[];
  tone?: string;
}

export interface ReportStatus {
  id: string;
  status: 'queued' | 'generating' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  completed_at: string | null;
  quality_gates_passed: boolean | null;
}

// ─── Identity sub-types ──────────────────────────────────────────────

export interface NumerologyProfile {
  life_path: number;
  expression: number;
  soul_urge: number;
  personality: number;
  personal_year: number;
  personal_month: number;
  maturity: number;
  is_master_number: boolean;
  chaldean_name: number | null;
  calculation_system: string;
}

export interface AstrologyProfile {
  sun_sign: string;
  moon_sign: string;
  rising_sign: string | null;
  sun_degree: number;
  moon_degree: number;
  rising_degree: number | null;
  venus_retrograde: boolean;
  mercury_retrograde: boolean;
}

export interface ArchetypeProfile {
  primary: string;
  secondary: string | null;
  shadow: string;
  shadow_secondary: string | null;
  light_qualities: string[];
  shadow_qualities: string[];
}

export interface BigFiveScores {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
}

export interface PersonalityProfile {
  big_five: BigFiveScores;
  attachment_style: string;
  enneagram_type: number | null;
  enneagram_wing: number | null;
}

export interface IdentityLayer {
  numerology: NumerologyProfile;
  astrology: AstrologyProfile;
  archetype: ArchetypeProfile;
  personality: PersonalityProfile;
  strengths_map: string[];
}

// ─── Report response ─────────────────────────────────────────────────

export interface ReportResponse {
  id: string;
  status: string;
  profile_summary: {
    identity: IdentityLayer;
    [key: string]: unknown;
  } | null;
  modules: Record<string, unknown> | null;
  quality_gates: Record<string, boolean> | null;
  created_at: string;
  completed_at: string | null;
}

// ─── Numerology endpoint types ───────────────────────────────────────

export interface NumerologyResponse {
  life_path: number;
  expression: number;
  soul_urge: number;
  personality: number;
  personal_year: number;
  personal_month: number;
  maturity: number;
  is_master_number: boolean;
  chaldean_name: number | null;
  system: string;
  name_used: string;
  birth_date: string;
}

// ─── Astrology endpoint types ────────────────────────────────────────

export interface AstrologyResponse {
  sun_sign: string;
  sun_degree: number;
  moon_sign: string;
  moon_degree: number;
  rising_sign: string | null;
  rising_degree: number | null;
  mercury_retrograde: boolean;
  venus_retrograde: boolean;
  birth_date: string;
  calculation_note: string | null;
}

// ─── Healing types ──────────────────────────────────────────────────

export interface ModalityResponse {
  name: string;
  skill_trigger: string;
  category: string;
  description: string;
  contraindications: string[];
  min_difficulty: string;
  traditions: string[];
  evidence_level: string;
}

export interface ModalityListResponse {
  modalities: ModalityResponse[];
  total: number;
}

export interface HealingMatchResponse {
  modality: string;
  skill_trigger: string;
  preference_score: number;
  contraindicated: boolean;
  difficulty_level: string;
}

export interface HealingMatchListResponse {
  matches: HealingMatchResponse[];
  total: number;
}

export interface BreathworkResponse {
  name: string;
  inhale_seconds: number;
  hold_seconds: number;
  exhale_seconds: number;
  hold_empty_seconds: number;
  cycles: number;
  difficulty: string;
  description: string;
}

// ─── Wealth types ───────────────────────────────────────────────────

export interface WealthProfileResponse {
  wealth_archetype: string;
  description: string;
  primary_levers: string[];
  strengths: string[];
  blind_spots: string[];
  recommended_actions: string[];
  scores: Record<string, number>;
}

export interface PlanPhaseResponse {
  name: string;
  days: [number, number];
  focus_lever: string;
  actions: string[];
  milestones: string[];
}

export interface WealthPlanResponse {
  wealth_archetype: string;
  phases: PlanPhaseResponse[];
  daily_habits: string[];
  weekly_reviews: string[];
}

export interface LeverResponse {
  levers: string[];
}

// ─── Creative types ─────────────────────────────────────────────────

export interface GuilfordScoresResponse {
  fluency: number;
  flexibility: number;
  originality: number;
  elaboration: number;
  sensitivity: number;
  redefinition: number;
}

export interface StyleFingerprintResponse {
  guilford_summary: Record<string, unknown>;
  dna_summary: Record<string, unknown>;
  dominant_components: string[];
  creative_style: string;
  overall_score: number;
  strengths: string[];
  growth_areas: string[];
  recommended_mediums: string[];
}

export interface ProjectResponse {
  title: string;
  description: string;
  type: string;
  medium: string;
  skill_level: string;
}

export interface ProjectListResponse {
  projects: ProjectResponse[];
  total: number;
  orientation: string;
}

// ─── Perspective types ──────────────────────────────────────────────

export interface BiasDetectResponse {
  biases_detected: Array<Record<string, unknown>>;
  total: number;
  disclaimer: string;
}

export interface KeganAssessResponse {
  stage: string;
  stage_number: number;
  name: string;
  description: string;
  strengths: string[];
  growth_edges: string[];
  growth_practices: string[];
  supportive_environments: string[];
  encouragement: string;
  methodology: string;
}

// ─── API functions ───────────────────────────────────────────────────

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  // 202 is used for "still generating" status — we handle it differently
  if (res.status === 202) {
    const body = await res.json();
    throw new ApiError(202, body.detail || 'Still processing');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ─── Reports ────────────────────────────────────────────────────────

export async function createReport(
  intake: IntakePayload,
  modules: string[] = ['full'],
  tone: string = 'balanced',
): Promise<ReportStatus> {
  return request<ReportStatus>(`${BASE}/reports`, {
    method: 'POST',
    body: JSON.stringify({ intake, modules, tone }),
  });
}

export async function getReport(id: string): Promise<ReportResponse> {
  return request<ReportResponse>(`${BASE}/reports/${id}`);
}

// ─── Numerology ─────────────────────────────────────────────────────

export async function getNumerology(
  name: string,
  birthDate?: string,
  system: string = 'pythagorean',
): Promise<NumerologyResponse> {
  const params = new URLSearchParams();
  if (birthDate) params.set('birth_date', birthDate);
  if (system !== 'pythagorean') params.set('system', system);
  const query = params.toString();
  return request<NumerologyResponse>(
    `${BASE}/numerology/${encodeURIComponent(name)}${query ? `?${query}` : ''}`,
  );
}

// ─── Astrology ──────────────────────────────────────────────────────

export async function getAstrology(
  birthDate: string,
  birthTime?: string,
  birthCity?: string,
): Promise<AstrologyResponse> {
  const params = new URLSearchParams();
  if (birthTime) params.set('birth_time', birthTime);
  if (birthCity) params.set('birth_city', birthCity);
  const query = params.toString();
  return request<AstrologyResponse>(
    `${BASE}/astrology/${birthDate}${query ? `?${query}` : ''}`,
  );
}

// ─── Healing ────────────────────────────────────────────────────────

export async function getHealingModalities(): Promise<ModalityListResponse> {
  return request<ModalityListResponse>(`${BASE}/healing/modalities`);
}

export async function getHealingMatch(
  profile: Record<string, unknown>,
): Promise<HealingMatchListResponse> {
  return request<HealingMatchListResponse>(`${BASE}/healing/match`, {
    method: 'POST',
    body: JSON.stringify(profile),
  });
}

export async function getBreathwork(
  intention: string,
): Promise<BreathworkResponse> {
  return request<BreathworkResponse>(
    `${BASE}/healing/breathwork/${encodeURIComponent(intention)}`,
  );
}

// ─── Wealth ─────────────────────────────────────────────────────────

export async function getWealthProfile(
  data: Record<string, unknown>,
): Promise<WealthProfileResponse> {
  return request<WealthProfileResponse>(`${BASE}/wealth/profile`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getWealthPlan(
  data: Record<string, unknown>,
): Promise<WealthPlanResponse> {
  return request<WealthPlanResponse>(`${BASE}/wealth/plan`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getWealthLevers(
  data: Record<string, unknown>,
): Promise<LeverResponse> {
  return request<LeverResponse>(`${BASE}/wealth/levers`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── Creative ───────────────────────────────────────────────────────

export async function getCreativeAssessment(
  responses: Record<string, number>,
): Promise<GuilfordScoresResponse> {
  return request<GuilfordScoresResponse>(`${BASE}/creative/assessment`, {
    method: 'POST',
    body: JSON.stringify({ responses }),
  });
}

export async function getCreativeStyle(
  data: Record<string, unknown>,
): Promise<StyleFingerprintResponse> {
  return request<StyleFingerprintResponse>(`${BASE}/creative/style`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getCreativeProjects(
  data: Record<string, unknown>,
): Promise<ProjectListResponse> {
  return request<ProjectListResponse>(`${BASE}/creative/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── Perspective ────────────────────────────────────────────────────

export async function detectBiases(
  text: string,
): Promise<BiasDetectResponse> {
  return request<BiasDetectResponse>(`${BASE}/perspective/biases/detect`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export async function getKeganAssessment(
  responses: Record<string, unknown>,
): Promise<KeganAssessResponse> {
  return request<KeganAssessResponse>(`${BASE}/perspective/kegan/assess`, {
    method: 'POST',
    body: JSON.stringify(responses),
  });
}

// ─── Journal ──────────────────────────────────────────────────────

export interface JournalEntry {
  id: string;
  user_id: string;
  system: string;
  entry_type: string;
  title: string;
  content: string;
  tags: string[];
  mood_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface JournalListResponse {
  entries: JournalEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface JournalStatsResponse {
  total_entries: number;
  entries_by_system: Record<string, number>;
  entries_by_type: Record<string, number>;
  average_mood: number | null;
  streak_days: number;
  tags_used: string[];
}

export async function createJournalEntry(
  data: Record<string, unknown>,
): Promise<JournalEntry> {
  return request<JournalEntry>(`${BASE}/journal`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getJournalEntries(
  userId: string,
  opts?: { system?: string; entryType?: string; page?: number; perPage?: number },
): Promise<JournalListResponse> {
  const params = new URLSearchParams({ user_id: userId });
  if (opts?.system) params.set('system', opts.system);
  if (opts?.entryType) params.set('entry_type', opts.entryType);
  if (opts?.page) params.set('page', String(opts.page));
  if (opts?.perPage) params.set('per_page', String(opts.perPage));
  return request<JournalListResponse>(`${BASE}/journal?${params}`);
}

export async function getJournalStats(
  userId: string,
): Promise<JournalStatsResponse> {
  return request<JournalStatsResponse>(`${BASE}/journal/stats/${userId}`);
}

// ─── Outcomes ─────────────────────────────────────────────────────

export interface SystemProgress {
  system: string;
  engagement_score: number;
  milestones_total: number;
  milestones_completed: number;
  completion_pct: number;
  active_days: number;
  last_activity: string | null;
}

export interface OutcomeSummary {
  user_id: string;
  overall_score: number;
  systems: SystemProgress[];
  total_milestones: number;
  completed_milestones: number;
  total_journal_entries: number;
  active_plan_day: number | null;
  generated_at: string;
}

export async function getOutcomeSummary(
  userId: string,
  journalCount?: number,
): Promise<OutcomeSummary> {
  const params = new URLSearchParams();
  if (journalCount !== undefined) params.set('journal_count', String(journalCount));
  const query = params.toString();
  return request<OutcomeSummary>(
    `${BASE}/outcomes/summary/${userId}${query ? `?${query}` : ''}`,
  );
}

export async function createMilestone(
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${BASE}/outcomes/milestones`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function logActivity(
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${BASE}/outcomes/activity`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export { ApiError };
