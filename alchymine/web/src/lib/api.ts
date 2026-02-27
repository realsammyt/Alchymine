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
    // For report polling, return the status info from the error detail
    const body = await res.json();
    throw new ApiError(202, body.detail || 'Still processing');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Create a new report (POST /api/v1/reports).
 * Returns a ReportStatus with the job ID.
 */
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

/**
 * Get report status or completed report (GET /api/v1/reports/{id}).
 * Throws ApiError with status 202 if still generating.
 */
export async function getReport(id: string): Promise<ReportResponse> {
  return request<ReportResponse>(`${BASE}/reports/${id}`);
}

/**
 * Calculate numerology for a name (GET /api/v1/numerology/{name}).
 */
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

/**
 * Calculate astrology chart (GET /api/v1/astrology/{birthDate}).
 */
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

export { ApiError };
