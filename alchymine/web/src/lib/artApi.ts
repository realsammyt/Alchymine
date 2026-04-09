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

/**
 * Fetch protected image bytes for a given image id and return a
 * browser-local object URL pointing at the blob.
 *
 * The backend image GET endpoint requires the same Bearer auth as
 * every other API call, so an `<img src="/api/v1/art/..">` tag will
 * 401. Callers should instead:
 *
 * 1. Call `fetchImageBlobUrl(imageId)`
 * 2. Assign the returned string to `<img src>`
 * 3. Call `URL.revokeObjectURL` on unmount or before re-fetching
 *
 * Returns `null` on any non-2xx so callers can render a placeholder
 * without having to catch.
 */
export async function fetchImageBlobUrl(
  imageId: string,
): Promise<string | null> {
  const url = artImageUrl(imageId);
  const res = await fetch(url, {
    headers: { ...authHeaders() },
    credentials: "include",
  });
  if (!res.ok) return null;
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export interface StylePreset {
  id: string;
  name: string;
  description: string;
}

/**
 * Fetch the catalogue of available style presets.
 *
 * Source-of-truth lives in `alchymine/llm/art_prompts.py::STYLE_PRESETS`
 * and is projected through `_PRESET_METADATA` in the generative art
 * router. Callers that need to render the picker before auth can
 * fall back to an empty array.
 */
export async function listStylePresets(): Promise<StylePreset[]> {
  const res = await fetch(`${API_BASE}/art/presets`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    throw new Error(`listStylePresets failed (${res.status})`);
  }
  return (await res.json()) as StylePreset[];
}

export interface GeneratedImageMetadata {
  id: string;
  prompt: string;
  style_preset: string | null;
  created_at: string;
  url: string;
}

export interface GeneratedImageListResponse {
  images: GeneratedImageMetadata[];
  limit: number;
  offset: number;
}

/**
 * Fetch a page of the authenticated user's previously generated images.
 *
 * Metadata only — the actual bytes must be streamed via
 * `fetchImageBlobUrl(imageId)` per-thumbnail.
 */
export async function listGeneratedImages(
  limit = 20,
  offset = 0,
): Promise<GeneratedImageListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const res = await fetch(`${API_BASE}/art/list?${params.toString()}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    throw new Error(`listGeneratedImages failed (${res.status})`);
  }
  return (await res.json()) as GeneratedImageListResponse;
}

/**
 * Delete a single previously generated image owned by the current user.
 *
 * Returns `true` on 204 success, `false` on 404 (already gone / not
 * owned). Any other non-2xx throws so the caller can surface it.
 */
export async function deleteGeneratedImage(imageId: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/art/${imageId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (res.status === 204) return true;
  if (res.status === 404) return false;
  throw new Error(`deleteGeneratedImage failed (${res.status})`);
}
