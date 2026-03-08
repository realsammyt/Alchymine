/**
 * Alchymine API client — typed fetch wrappers for the FastAPI backend.
 */

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1";

// ─── Shared types ────────────────────────────────────────────────────

export interface IntakePayload {
  full_name: string;
  birth_date: string; // YYYY-MM-DD
  birth_time?: string | null; // HH:MM or null
  birth_city?: string | null;
  intention: string; // Primary intention (first selected) — backward compat for report creation
  intentions?: string[]; // All selected intentions (1-3)
  assessment_responses: Record<string, number>;
}

export interface ReportRequest {
  intake: IntakePayload;
  modules?: string[];
  tone?: string;
}

export interface ReportStatus {
  id: string;
  status: "pending" | "generating" | "complete" | "failed";
  created_at: string;
  updated_at: string | null;
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
  result: {
    profile_summary?: {
      identity?: IdentityLayer;
      [key: string]: unknown;
    };
    narratives?: Record<
      string,
      { text: string; disclaimers?: string[]; ethics_passed?: boolean }
    >;
    [key: string]: unknown;
  } | null;
  error: string | null;
  created_at: string;
  updated_at: string | null;
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
    this.name = "ApiError";
  }
}

/** Map an ApiError from an auth endpoint to a user-friendly message. */
export function friendlyAuthError(
  err: unknown,
  context: "login" | "signup" | "forgot-password" | "reset-password",
): string {
  if (!(err instanceof ApiError)) {
    return "An unexpected error occurred";
  }
  // Connection refused / DNS failure
  if (err.status === 0 || err.status === 404) {
    return "Unable to connect to server. Please try again.";
  }
  if (err.status === 500) {
    return "Something went wrong. Please try again.";
  }
  if (context === "login" && err.status === 401) {
    return "Invalid email or password";
  }
  if (context === "signup") {
    if (err.status === 403) return "Invalid invitation code";
    if (err.status === 409) return "An account with this email already exists";
  }
  // 400 validation — show the backend's detail message
  if (err.status === 400 && err.message && err.message !== `HTTP 400`) {
    return err.message;
  }
  return err.message || "An unexpected error occurred";
}

// Provide the Authorization header as a migration fallback when a token is
// still present in localStorage.  New sessions rely on httpOnly cookies sent
// automatically via credentials: "include".
function getLegacyAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  url: string,
  options?: RequestInit,
  allow202 = false,
): Promise<T> {
  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...getLegacyAuthHeaders(),
      ...options?.headers,
    },
  });

  // 202 is used for "still generating" status — throw so callers can
  // handle polling.  Callers that expect 202 as a success (e.g. report
  // creation) pass allow202=true to receive the parsed body instead.
  if (res.status === 202 && !allow202) {
    const body = await res.json();
    throw new ApiError(202, body.detail || "Still processing");
  }

  // Attempt token refresh on 401.  The refresh request uses credentials: "include"
  // so the httpOnly refresh_token cookie is sent automatically.  As a migration
  // fallback we also pass the stored refresh token in the JSON body.
  if (res.status === 401 && typeof window !== "undefined") {
    const legacyRefreshToken = localStorage.getItem("refresh_token");
    try {
      const refreshRes = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          refresh_token: legacyRefreshToken ?? undefined,
        }),
      });
      if (refreshRes.ok) {
        const tokens = await refreshRes.json();
        // Persist to localStorage for the header-based fallback path so that
        // the migration window works correctly; cookies are set by the server.
        localStorage.setItem("access_token", tokens.access_token);
        localStorage.setItem("refresh_token", tokens.refresh_token);
        // Retry the original request
        const retryRes = await fetch(url, {
          ...options,
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tokens.access_token}`,
            ...options?.headers,
          },
        });
        if (retryRes.ok) return retryRes.json();
      }
      // Refresh failed — clear legacy localStorage tokens
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ─── Reports ────────────────────────────────────────────────────────

export async function createReport(
  intake: IntakePayload,
  modules: string[] = ["full"],
  tone: string = "balanced",
): Promise<ReportStatus> {
  return request<ReportStatus>(
    `${BASE}/reports`,
    {
      method: "POST",
      body: JSON.stringify({ intake, modules, tone }),
    },
    true, // POST /reports returns 202 on success — don't throw
  );
}

export async function getReport(id: string): Promise<ReportResponse> {
  return request<ReportResponse>(`${BASE}/reports/${id}`);
}

export interface ReportListItem {
  id: string;
  status: string;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ReportListResponse {
  reports: ReportListItem[];
  count: number;
  skip: number;
  limit: number;
}

export async function listUserReports(
  userId: string,
  opts?: { skip?: number; limit?: number },
): Promise<ReportListResponse> {
  const params = new URLSearchParams();
  if (opts?.skip) params.set("skip", String(opts.skip));
  if (opts?.limit) params.set("limit", String(opts.limit));
  const query = params.toString();
  return request<ReportListResponse>(
    `${BASE}/reports/user/${encodeURIComponent(userId)}${query ? `?${query}` : ""}`,
  );
}

// ─── Numerology ─────────────────────────────────────────────────────

export async function getNumerology(
  name: string,
  birthDate?: string,
  system: string = "pythagorean",
): Promise<NumerologyResponse> {
  const params = new URLSearchParams();
  if (birthDate) params.set("birth_date", birthDate);
  if (system !== "pythagorean") params.set("system", system);
  const query = params.toString();
  return request<NumerologyResponse>(
    `${BASE}/numerology/${encodeURIComponent(name)}${query ? `?${query}` : ""}`,
  );
}

// ─── Astrology ──────────────────────────────────────────────────────

export async function getAstrology(
  birthDate: string,
  birthTime?: string,
  birthCity?: string,
): Promise<AstrologyResponse> {
  const params = new URLSearchParams();
  if (birthTime) params.set("birth_time", birthTime);
  if (birthCity) params.set("birth_city", birthCity);
  const query = params.toString();
  return request<AstrologyResponse>(
    `${BASE}/astrology/${birthDate}${query ? `?${query}` : ""}`,
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
    method: "POST",
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
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getWealthPlan(
  data: Record<string, unknown>,
): Promise<WealthPlanResponse> {
  return request<WealthPlanResponse>(`${BASE}/wealth/plan`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getWealthLevers(
  data: Record<string, unknown>,
): Promise<LeverResponse> {
  return request<LeverResponse>(`${BASE}/wealth/levers`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ─── Creative ───────────────────────────────────────────────────────

export async function getCreativeAssessment(
  responses: Record<string, number>,
): Promise<GuilfordScoresResponse> {
  return request<GuilfordScoresResponse>(`${BASE}/creative/assessment`, {
    method: "POST",
    body: JSON.stringify({ responses }),
  });
}

export async function getCreativeStyle(
  data: Record<string, unknown>,
): Promise<StyleFingerprintResponse> {
  return request<StyleFingerprintResponse>(`${BASE}/creative/style`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getCreativeProjects(
  data: Record<string, unknown>,
): Promise<ProjectListResponse> {
  return request<ProjectListResponse>(`${BASE}/creative/projects`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ─── Perspective ────────────────────────────────────────────────────

export async function detectBiases(text: string): Promise<BiasDetectResponse> {
  return request<BiasDetectResponse>(`${BASE}/perspective/biases/detect`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function getKeganAssessment(
  responses: Record<string, unknown>,
): Promise<KeganAssessResponse> {
  return request<KeganAssessResponse>(`${BASE}/perspective/kegan/assess`, {
    method: "POST",
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
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getJournalEntries(
  userId: string,
  opts?: {
    system?: string;
    entryType?: string;
    page?: number;
    perPage?: number;
  },
): Promise<JournalListResponse> {
  const params = new URLSearchParams({ user_id: userId });
  if (opts?.system) params.set("system", opts.system);
  if (opts?.entryType) params.set("entry_type", opts.entryType);
  if (opts?.page) params.set("page", String(opts.page));
  if (opts?.perPage) params.set("per_page", String(opts.perPage));
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
  if (journalCount !== undefined)
    params.set("journal_count", String(journalCount));
  const query = params.toString();
  return request<OutcomeSummary>(
    `${BASE}/outcomes/summary/${userId}${query ? `?${query}` : ""}`,
  );
}

export async function createMilestone(
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${BASE}/outcomes/milestones`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function logActivity(
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${BASE}/outcomes/activity`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ─── Auth ──────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthUser {
  id: string;
  email: string;
  version: string;
  created_at: string;
  is_admin: boolean;
}

export async function registerUser(
  email: string,
  password: string,
  promoCode: string,
): Promise<TokenResponse> {
  return request<TokenResponse>(`${BASE}/auth/register`, {
    method: "POST",
    body: JSON.stringify({ email, password, promo_code: promoCode }),
  });
}

export async function loginUser(
  email: string,
  password: string,
): Promise<TokenResponse> {
  return request<TokenResponse>(`${BASE}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<AuthUser> {
  return request<AuthUser>(`${BASE}/auth/me`);
}

export async function logoutUser(): Promise<{ message: string }> {
  return request<{ message: string }>(`${BASE}/auth/logout`, {
    method: "POST",
  });
}

export async function forgotPassword(
  email: string,
): Promise<{ message: string }> {
  return request<{ message: string }>(`${BASE}/auth/forgot-password`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<{ message: string }> {
  return request<{ message: string }>(`${BASE}/auth/reset-password`, {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

// ─── Integration / Cross-System types ────────────────────────────

export interface BridgeInsightResponse {
  source_system: string;
  target_system: string;
  bridge_type: string;
  insight: string;
  action: string;
  confidence: number;
}

export interface ProfileSynthesisRequest {
  numerology?: Record<string, unknown> | null;
  archetype?: Record<string, unknown> | null;
  personality?: Record<string, unknown> | null;
  wealth_archetype?: string | null;
  creative_style?: string | null;
  kegan_stage?: number | null;
}

export interface IntakeProfileData {
  full_name: string;
  birth_date: string;
  birth_time?: string | null;
  birth_city?: string | null;
  intention: string;
  intentions: string[];
  assessment_responses?: Record<string, unknown> | null;
  family_structure?: string | null;
}

export interface ProfileResponse {
  id: string;
  version: string;
  created_at: string | null;
  updated_at: string | null;
  intake: IntakeProfileData | null;
  identity: Record<string, unknown> | null;
  healing: Record<string, unknown> | null;
  wealth: Record<string, unknown> | null;
  creative: Record<string, unknown> | null;
  perspective: Record<string, unknown> | null;
}

// ─── Integration API functions ────────────────────────────────────

export async function synthesizeCrossSystems(
  data: ProfileSynthesisRequest,
): Promise<BridgeInsightResponse[]> {
  return request<BridgeInsightResponse[]>(`${BASE}/integration/synthesize`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ─── Profile API functions ────────────────────────────────────────

export async function getProfile(userId: string): Promise<ProfileResponse> {
  return request<ProfileResponse>(
    `${BASE}/profile/${encodeURIComponent(userId)}`,
  );
}

export async function saveIntake(
  userId: string,
  data: {
    full_name: string;
    birth_date: string;
    birth_time?: string | null;
    birth_city?: string | null;
    intention: string;
    intentions: string[];
  },
): Promise<ProfileResponse> {
  return request<ProfileResponse>(
    `${BASE}/profile/${encodeURIComponent(userId)}/intake`,
    {
      method: "PUT",
      body: JSON.stringify({ data }),
    },
  );
}

// ─── Admin types ──────────────────────────────────────────────────

export interface AdminUser {
  id: string;
  email: string | null;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  invite_code_used: string | null;
}

export interface AdminUserDetail extends AdminUser {
  version: string;
  updated_at: string;
  has_intake: boolean;
  has_identity: boolean;
  has_healing: boolean;
  has_wealth: boolean;
  has_creative: boolean;
  has_perspective: boolean;
}

export interface PaginatedUsers {
  users: AdminUser[];
  total: number;
  page: number;
  per_page: number;
}

export interface InviteCode {
  id: number;
  code: string;
  created_by: string | null;
  max_uses: number;
  uses_count: number;
  expires_at: string | null;
  is_active: boolean;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedInviteCodes {
  codes: InviteCode[];
  total: number;
  page: number;
  per_page: number;
}

export interface AnalyticsOverview {
  total_users: number;
  active_users: number;
  admin_users: number;
  new_users_today: number;
  new_users_week: number;
  new_users_month: number;
  total_invite_codes: number;
  active_invite_codes: number;
  total_reports: number;
  total_journal_entries: number;
}

export interface DailyUserCount {
  date: string;
  count: number;
}

export interface UserAnalytics {
  daily_counts: DailyUserCount[];
  period_days: number;
}

export interface InviteUserResult {
  email: string;
  invite_code: string;
  email_sent: boolean;
}

export interface InviteUsersResponse {
  results: InviteUserResult[];
  total_invited: number;
  total_emails_sent: number;
}

// ─── Admin API functions ──────────────────────────────────────────

export async function adminGetUsers(opts?: {
  page?: number;
  perPage?: number;
  search?: string;
  sortBy?: string;
  sortOrder?: string;
  activeOnly?: boolean;
}): Promise<PaginatedUsers> {
  const params = new URLSearchParams();
  if (opts?.page) params.set("page", String(opts.page));
  if (opts?.perPage) params.set("per_page", String(opts.perPage));
  if (opts?.search) params.set("search", opts.search);
  if (opts?.sortBy) params.set("sort_by", opts.sortBy);
  if (opts?.sortOrder) params.set("sort_order", opts.sortOrder);
  if (opts?.activeOnly) params.set("active_only", "true");
  const query = params.toString();
  return request<PaginatedUsers>(
    `${BASE}/admin/users${query ? `?${query}` : ""}`,
  );
}

export async function adminGetUser(userId: string): Promise<AdminUserDetail> {
  return request<AdminUserDetail>(`${BASE}/admin/users/${userId}`);
}

export async function adminUpdateUserStatus(
  userId: string,
  isActive: boolean,
): Promise<AdminUser> {
  return request<AdminUser>(`${BASE}/admin/users/${userId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ is_active: isActive }),
  });
}

export async function adminToggleAdmin(
  userId: string,
  isAdmin: boolean,
): Promise<AdminUser> {
  return request<AdminUser>(`${BASE}/admin/users/${userId}/admin`, {
    method: "PATCH",
    body: JSON.stringify({ is_admin: isAdmin }),
  });
}

export async function adminGetInviteCodes(opts?: {
  page?: number;
  perPage?: number;
  activeOnly?: boolean;
}): Promise<PaginatedInviteCodes> {
  const params = new URLSearchParams();
  if (opts?.page) params.set("page", String(opts.page));
  if (opts?.perPage) params.set("per_page", String(opts.perPage));
  if (opts?.activeOnly) params.set("active_only", "true");
  const query = params.toString();
  return request<PaginatedInviteCodes>(
    `${BASE}/admin/invite-codes${query ? `?${query}` : ""}`,
  );
}

export async function adminCreateInviteCode(data: {
  code?: string;
  max_uses?: number;
  expires_at?: string;
  note?: string;
}): Promise<InviteCode> {
  return request<InviteCode>(`${BASE}/admin/invite-codes`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminBulkCreateInviteCodes(data: {
  count: number;
  max_uses?: number;
  expires_at?: string;
  note?: string;
}): Promise<InviteCode[]> {
  return request<InviteCode[]>(`${BASE}/admin/invite-codes/bulk`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateInviteCode(
  codeId: number,
  data: {
    is_active?: boolean;
    max_uses?: number;
    expires_at?: string;
    note?: string;
  },
): Promise<InviteCode> {
  return request<InviteCode>(`${BASE}/admin/invite-codes/${codeId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteInviteCode(
  codeId: number,
): Promise<{ message: string }> {
  return request<{ message: string }>(`${BASE}/admin/invite-codes/${codeId}`, {
    method: "DELETE",
  });
}

export async function adminInviteUsers(data: {
  emails: string[];
  note?: string;
  expires_in_days?: number;
}): Promise<InviteUsersResponse> {
  return request<InviteUsersResponse>(`${BASE}/admin/invite`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminGetAnalyticsOverview(): Promise<AnalyticsOverview> {
  return request<AnalyticsOverview>(`${BASE}/admin/analytics/overview`);
}

export async function adminGetUserAnalytics(
  days?: number,
): Promise<UserAnalytics> {
  const params = days ? `?days=${days}` : "";
  return request<UserAnalytics>(`${BASE}/admin/analytics/users${params}`);
}

// ─── Waitlist types ───────────────────────────────────────────────

export interface WaitlistEntry {
  id: number;
  email: string;
  status: "pending" | "invited" | "registered";
  invite_code_id: number | null;
  notes: string | null;
  created_at: string;
}

export interface PaginatedWaitlist {
  entries: WaitlistEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface WaitlistInviteResult {
  email: string;
  success: boolean;
  code?: string;
  error?: string;
}

export interface WaitlistInviteResponse {
  results: WaitlistInviteResult[];
}

// ─── Waitlist API functions ───────────────────────────────────────

export async function joinWaitlist(
  email: string,
): Promise<{ message: string; already_registered: boolean }> {
  const res = await fetch(`${BASE}/auth/waitlist`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function adminGetWaitlist(opts?: {
  page?: number;
  perPage?: number;
  status?: string;
}): Promise<PaginatedWaitlist> {
  const params = new URLSearchParams();
  if (opts?.page) params.set("page", String(opts.page));
  if (opts?.perPage) params.set("per_page", String(opts.perPage));
  if (opts?.status) params.set("status", opts.status);
  const query = params.toString();
  return request<PaginatedWaitlist>(
    `${BASE}/admin/waitlist${query ? `?${query}` : ""}`,
  );
}

export async function adminInviteWaitlistEntries(data: {
  entry_ids: number[];
  expires_in_days?: number;
}): Promise<WaitlistInviteResponse> {
  return request<WaitlistInviteResponse>(`${BASE}/admin/waitlist/invite`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteWaitlistEntry(entryId: number): Promise<void> {
  await request<{ message: string }>(`${BASE}/admin/waitlist/${entryId}`, {
    method: "DELETE",
  });
}

export { ApiError };
