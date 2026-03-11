/**
 * Typed fetch wrappers for the generative art API endpoints.
 */

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1";

// ─── Types ────────────────────────────────────────────────────────────────

export interface ArtProfile {
  archetype?: string;
  zodiac_sign?: string;
  system?: string;
  big_five?: {
    openness?: number;
    conscientiousness?: number;
    extraversion?: number;
  };
}

export interface GenerateArtRequest {
  prompt?: string;
  profile?: ArtProfile;
}

export interface GenerateArtResponse {
  image_id: string;
  data_b64: string;
  mime_type: string;
  prompt_used: string;
}

export interface RetrieveArtResponse {
  image_id: string;
  data_b64: string;
  mime_type: string;
  prompt_used: string;
}

// ─── Fetch wrappers ───────────────────────────────────────────────────────

/**
 * Generate a personalized image via Gemini.
 *
 * Returns null when Gemini is unavailable (204 response) or on any error.
 * The caller should display a placeholder instead.
 */
export async function generateArt(
  body: GenerateArtRequest,
  token?: string,
): Promise<GenerateArtResponse | null> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE}/art/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (response.status === 204) {
    return null;
  }

  if (!response.ok) {
    return null;
  }

  return response.json() as Promise<GenerateArtResponse>;
}

/**
 * Retrieve a previously generated image by its UUID.
 *
 * Returns null when not found (404) or on any error.
 */
export async function retrieveArt(
  imageId: string,
  token?: string,
): Promise<RetrieveArtResponse | null> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE}/art/${imageId}`, { headers });

  if (!response.ok) {
    return null;
  }

  return response.json() as Promise<RetrieveArtResponse>;
}
