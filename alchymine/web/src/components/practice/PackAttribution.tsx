"use client";

import type { PackManifest } from "@/lib/api";

interface PackAttributionProps {
  manifest: PackManifest;
}

/**
 * Who wrote a pack and under what license.
 *
 * This is not decoration. Packs can be mounted from outside the repo
 * under licenses Alchymine does not own, and the terms of most of those
 * licenses require the attribution to travel with the content. Showing
 * it next to the practices is how that obligation is met, so this
 * component renders even when every field is Alchymine's own.
 *
 * `source_url` is rendered as a plain anchor. The schema already
 * guarantees it is http or https, so there is nothing here to sanitise
 * a second time.
 */
export default function PackAttribution({ manifest }: PackAttributionProps) {
  return (
    <p className="text-xs font-body text-text/60 leading-relaxed">
      <span>{manifest.attribution}</span>
      <span aria-hidden="true"> · </span>
      <span>{manifest.license}</span>
      {manifest.source_url && (
        <>
          <span aria-hidden="true"> · </span>
          <a
            href={manifest.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="touch-target inline-flex items-center underline underline-offset-2 transition-colors duration-200 hover:text-text/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded"
          >
            Source
            {/* Says where the link goes before it is followed. A new tab
                that arrives unannounced leaves a screen-reader user in a
                document they did not ask for, with no back button. */}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </>
      )}
    </p>
  );
}
