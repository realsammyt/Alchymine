"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchImageBlobUrl } from "@/lib/artApi";

export interface GalleryImage {
  id: string;
  prompt: string;
  stylePreset: string | null;
  createdAt: string;
}

interface ArtGalleryProps {
  images: GalleryImage[];
  onDelete?: (id: string) => void;
}

/**
 * Load the auth-protected image bytes for a single gallery entry and
 * return a blob URL. Wrapped in a component-level hook so the whole
 * grid can render skeletons while individual thumbnails stream in.
 */
function useBlobUrl(imageId: string): {
  url: string | null;
  loading: boolean;
  failed: boolean;
} {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let blobUrl: string | null = null;

    setLoading(true);
    setFailed(false);
    setUrl(null);

    void fetchImageBlobUrl(imageId)
      .then((resolvedUrl) => {
        if (cancelled) {
          if (resolvedUrl) URL.revokeObjectURL(resolvedUrl);
          return;
        }
        if (resolvedUrl === null) {
          setFailed(true);
          setLoading(false);
          return;
        }
        blobUrl = resolvedUrl;
        setUrl(resolvedUrl);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [imageId]);

  return { url, loading, failed };
}

// ── Single thumbnail card ─────────────────────────────────────────────
interface ThumbnailProps {
  image: GalleryImage;
  onOpen: (image: GalleryImage) => void;
  onDelete?: (id: string) => void;
}

function GalleryThumbnail({ image, onOpen, onDelete }: ThumbnailProps) {
  const { url, loading, failed } = useBlobUrl(image.id);

  return (
    <figure className="relative rounded-xl overflow-hidden border border-white/[0.06] bg-surface group">
      <button
        type="button"
        onClick={() => onOpen(image)}
        className="block w-full focus:outline-none focus:ring-2 focus:ring-primary/60"
        aria-label={`Open image: ${image.prompt.slice(0, 80)}`}
      >
        {loading && (
          <div
            className="w-full aspect-video bg-gradient-to-br from-secondary/20 via-primary/15 to-accent/20 animate-pulse"
            role="status"
            aria-label="Loading image"
          />
        )}
        {!loading && failed && (
          <div
            className="w-full aspect-video flex items-center justify-center text-text/30 text-xs font-body"
            role="img"
            aria-label="Image failed to load"
          >
            Image unavailable
          </div>
        )}
        {url && !loading && !failed && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={url}
            alt={`Generated art: ${image.prompt.slice(0, 120)}`}
            className="w-full aspect-video object-cover"
          />
        )}
      </button>

      <figcaption className="px-3 py-2 text-xs font-body text-text/40 truncate bg-surface/80">
        {image.prompt.slice(0, 72)}
        {image.prompt.length > 72 ? "…" : ""}
      </figcaption>

      {onDelete && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onDelete(image.id);
          }}
          aria-label={`Delete image generated from prompt: ${image.prompt.slice(0, 80)}`}
          className="absolute top-2 right-2 px-2 py-1 text-[10px] font-body uppercase tracking-wider rounded-full bg-bg/70 backdrop-blur border border-white/[0.08] text-text/70 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity hover:text-red-300 hover:border-red-400/40"
        >
          Delete
        </button>
      )}
    </figure>
  );
}

// ── Lightbox modal ────────────────────────────────────────────────────
interface LightboxProps {
  image: GalleryImage;
  onClose: () => void;
}

function Lightbox({ image, onClose }: LightboxProps) {
  const { url, loading, failed } = useBlobUrl(image.id);
  const [promptExpanded, setPromptExpanded] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const promptIsLong = image.prompt.length > 240;

  // Focus the close button when the lightbox opens. We keep focus
  // inside the dialog via a small keydown handler rather than pulling
  // in a focus-trap library — the dialog has only a handful of
  // interactive elements.
  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key === "Tab") {
        const dialog = dialogRef.current;
        if (!dialog) return;
        const focusable = dialog.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const formattedDate = (() => {
    if (!image.createdAt) return "";
    const d = new Date(image.createdAt);
    if (Number.isNaN(d.getTime())) return image.createdAt;
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  })();

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Generated art detail"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      data-testid="art-lightbox"
    >
      <div
        ref={dialogRef}
        className="relative w-full max-w-3xl max-h-[90vh] bg-surface rounded-2xl overflow-hidden border border-white/[0.08] shadow-2xl flex flex-col"
      >
        <div className="relative flex-1 bg-black/40 flex items-center justify-center min-h-[240px]">
          {loading && (
            <div
              className="w-full h-full aspect-video bg-gradient-to-br from-secondary/20 via-primary/15 to-accent/20 animate-pulse"
              role="status"
              aria-label="Loading image"
            />
          )}
          {!loading && failed && (
            <p className="text-text/50 text-sm font-body">
              Image unavailable.
            </p>
          )}
          {url && !loading && !failed && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={url}
              alt={`Generated art: ${image.prompt.slice(0, 120)}`}
              className="w-full max-h-[60vh] object-contain"
            />
          )}

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close image detail"
            className="absolute top-3 right-3 w-9 h-9 rounded-full bg-bg/70 backdrop-blur border border-white/[0.08] text-text/80 hover:text-primary hover:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/60 flex items-center justify-center"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>

        <div className="px-5 py-4 space-y-3 border-t border-white/[0.06]">
          <div className="flex items-center gap-3 flex-wrap">
            {image.stylePreset && (
              <span
                className="px-2 py-0.5 rounded-full bg-secondary/15 text-secondary text-xs font-body uppercase tracking-wider"
                data-testid="lightbox-style-badge"
              >
                {image.stylePreset}
              </span>
            )}
            {formattedDate && (
              <span className="text-xs font-body text-text/40">
                {formattedDate}
              </span>
            )}
          </div>
          <p
            className="text-sm font-body text-text/70 leading-relaxed whitespace-pre-wrap break-words"
            data-testid="lightbox-prompt"
          >
            {promptExpanded || !promptIsLong
              ? image.prompt
              : `${image.prompt.slice(0, 240)}…`}
          </p>
          {promptIsLong && (
            <button
              type="button"
              onClick={() => setPromptExpanded((v) => !v)}
              className="text-xs font-body text-primary hover:underline focus:outline-none focus:underline"
            >
              {promptExpanded ? "Show less" : "Show full prompt"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────

/**
 * Grid of a user's generated images with a click-to-expand lightbox.
 *
 * Each thumbnail streams its bytes via `fetchImageBlobUrl` so the
 * protected GET endpoint is never bypassed with an unauthenticated
 * `<img src="/api/..">` tag. The optional `onDelete` prop wires a
 * trash affordance onto each card.
 */
export default function ArtGallery({ images, onDelete }: ArtGalleryProps) {
  const [activeImage, setActiveImage] = useState<GalleryImage | null>(null);

  const handleOpen = useCallback((image: GalleryImage) => {
    setActiveImage(image);
  }, []);

  const handleClose = useCallback(() => {
    setActiveImage(null);
  }, []);

  if (images.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center py-16 text-text/40"
        data-testid="gallery-empty"
      >
        <p className="font-body text-sm">
          No generated art yet. Create your first piece above.
        </p>
      </div>
    );
  }

  return (
    <>
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
        data-testid="gallery-grid"
      >
        {images.map((image) => (
          <GalleryThumbnail
            key={image.id}
            image={image}
            onOpen={handleOpen}
            onDelete={onDelete}
          />
        ))}
      </div>

      {activeImage && <Lightbox image={activeImage} onClose={handleClose} />}
    </>
  );
}
