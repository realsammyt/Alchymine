/**
 * Typed fetch wrappers for the generative art endpoints.
 *
 * The backend returns 204 No Content when GEMINI_API_KEY is not
 * configured (graceful degradation). All wrappers translate that into a
 * `null` return value so callers can render placeholder UI without
 * having to inspect HTTP status codes.
 */

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface ArtGenerateRequest {
  style_preset?: string | null;
  user_prompt_extension?: string | null;
}

export interface ArtGenerateResponse {
  image_id: string;
  url: string;
  prompt: string;
}

/**
 * Request a freshly generated personalized image for the current user.
 *
 * Returns:
 * - `ArtGenerateResponse` on 201 success
 * - `null` on 204 (Gemini disabled — caller should render placeholder)
 *
 * Throws on 4xx/5xx other than 204.
 */
export async function generateArt(
  body: ArtGenerateRequest = {},
): Promise<ArtGenerateResponse | null> {
  const res = await fetch(`${API_BASE}/art/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });

  if (res.status === 204) return null;
  if (!res.ok) {
    const message = await res.text().catch(() => "");
    throw new Error(`generateArt failed (${res.status}): ${message}`);
  }
  return (await res.json()) as ArtGenerateResponse;
}

/**
 * Build the absolute URL for fetching a previously generated image.
 *
 * Useful when wiring an `<img src=...>` tag — the image GET endpoint
 * returns raw bytes so it can be used directly as an image source. The
 * Authorization header still applies if the deployment uses cookie auth
 * the browser will automatically include credentials.
 */
export function artImageUrl(imageId: string): string {
  return `${API_BASE}/art/${imageId}`;
}
