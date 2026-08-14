"use client";

import { useCallback, useState } from "react";
import PracticeCard, { type PracticeCardState } from "./PracticeCard";
import SelfCheckPrompt from "./SelfCheckPrompt";
import IntegrationPrompt, { type IntegrationState } from "./IntegrationPrompt";
import type {
  IntegrationCreate,
  PracticeDefinition,
  PracticeLogCreate,
  PracticeLogEntry,
  ProtocolItem,
  TodayResponse,
} from "@/lib/api";

type Slot = "morning" | "day" | "evening";

/**
 * The three slots in order, with the heading each one gets.
 *
 * They line up positionally with `daily_prompts`, so slot assignment is
 * a schema fact rather than a per-practice editorial call.
 */
const SLOTS: { key: Slot; heading: string }[] = [
  { key: "morning", heading: "Morning" },
  { key: "day", heading: "During the day" },
  { key: "evening", heading: "Evening" },
];

/** Everything one card is currently doing, keyed by slot and practice. */
interface CardStatus {
  state: PracticeCardState;
  error: string | null;
  logId: string | null;
  selfCheckDismissed: boolean;
  selfCheckSaving: boolean;
  selfCheckError: string | null;
  integration: IntegrationState;
  integrationError: string | null;
  integrationDismissed: boolean;
}

const FRESH: CardStatus = {
  state: "idle",
  error: null,
  logId: null,
  selfCheckDismissed: false,
  selfCheckSaving: false,
  selfCheckError: null,
  integration: "idle",
  integrationError: null,
  integrationDismissed: false,
};

/**
 * A card's identity. The slot is part of it: the same practice appears
 * three times a day, and completing it in the morning must not mark the
 * evening card done.
 */
function cardKey(slot: Slot, packId: string, slug: string): string {
  return `${slot}:${packId}/${slug}`;
}

interface DailyProtocolProps {
  today: TodayResponse;
  /** The full definition, for the self-check question. May not be loaded yet. */
  lookup: (packId: string, slug: string) => PracticeDefinition | undefined;
  onLog: (entry: PracticeLogCreate) => Promise<PracticeLogEntry>;
  onIntegrate: (entry: IntegrationCreate) => Promise<unknown>;
  /** Fires after a write lands, so the page can refresh the rhythm. */
  onLogged?: () => void;
}

/**
 * Today's protocol: N practices rendered three times, once per slot.
 *
 * Completion is optimistic. The card says "Done today." the moment it is
 * tapped and rolls back if the write fails, because the common case is
 * that it succeeds and a spinner between tap and confirmation makes a
 * one-second interaction feel like a transaction.
 */
export default function DailyProtocol({
  today,
  lookup,
  onLog,
  onIntegrate,
  onLogged,
}: DailyProtocolProps) {
  const [cards, setCards] = useState<Record<string, CardStatus>>({});

  const statusFor = useCallback(
    (key: string): CardStatus => cards[key] ?? FRESH,
    [cards],
  );

  const patch = useCallback((key: string, changes: Partial<CardStatus>) => {
    setCards((current) => ({
      ...current,
      [key]: { ...(current[key] ?? FRESH), ...changes },
    }));
  }, []);

  const write = useCallback(
    async (
      key: string,
      item: ProtocolItem,
      slot: Slot,
      status: "completed" | "skipped",
    ) => {
      // Optimistic: show the outcome first, undo it only if the write
      // is refused.
      patch(key, { state: status, error: null });
      try {
        const created = await onLog({
          pack_id: item.pack_id,
          practice_slug: item.slug,
          day_key: today.day_key,
          status,
          protocol_slot: slot,
        });
        patch(key, { logId: created.id });
        onLogged?.();
      } catch {
        patch(key, {
          state: "idle",
          error: "That didn't save. Have another go in a moment.",
        });
      }
    },
    [onLog, onLogged, patch, today.day_key],
  );

  const saveSelfCheck = useCallback(
    async (key: string, logId: string, response: string) => {
      patch(key, { selfCheckSaving: true, selfCheckError: null });
      try {
        await onIntegrate({ practice_log_id: logId, note: response });
        patch(key, { selfCheckSaving: false, selfCheckDismissed: true });
      } catch {
        patch(key, {
          selfCheckSaving: false,
          selfCheckError: "That didn't save. Have another go in a moment.",
        });
      }
    },
    [onIntegrate, patch],
  );

  const saveIntegration = useCallback(
    async (
      key: string,
      logId: string,
      input: { capacityDelta: number | null; note: string },
    ) => {
      patch(key, { integration: "saving", integrationError: null });
      try {
        await onIntegrate({
          practice_log_id: logId,
          capacity_delta: input.capacityDelta,
          note: input.note || null,
        });
        patch(key, { integration: "saved" });
      } catch {
        patch(key, {
          integration: "error",
          integrationError: "That didn't save. Have another go in a moment.",
        });
      }
    },
    [onIntegrate, patch],
  );

  if (today.items.length === 0) {
    return (
      <div className="card-surface p-8 text-center">
        <p className="text-sm font-body text-text/50 max-w-md mx-auto">
          Nothing scheduled today. Browse the library and pick something that
          fits.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {SLOTS.map(({ key: slot, heading }) => {
        const entries = today.slots[slot] ?? [];
        const headingId = `protocol-slot-${slot}`;
        return (
          <section key={slot} aria-labelledby={headingId}>
            <h2
              id={headingId}
              className="font-display text-lg font-medium text-text/80 mb-3"
            >
              {heading}
            </h2>
            <div className="flex flex-col gap-3">
              {entries.map((entry) => {
                const item = today.items.find(
                  (candidate) =>
                    candidate.pack_id === entry.pack_id &&
                    candidate.slug === entry.slug,
                );
                if (!item) return null;

                const key = cardKey(slot, entry.pack_id, entry.slug);
                const status = statusFor(key);
                const definition = lookup(entry.pack_id, entry.slug);
                const completed = status.state === "completed";
                const question = definition?.self_check?.question;

                return (
                  <PracticeCard
                    key={key}
                    item={item}
                    prompt={entry.prompt}
                    state={status.state}
                    error={status.error}
                    onComplete={() => void write(key, item, slot, "completed")}
                    onSkip={() => void write(key, item, slot, "skipped")}
                  >
                    {completed && question && !status.selfCheckDismissed && (
                      <SelfCheckPrompt
                        question={question}
                        saving={status.selfCheckSaving}
                        error={status.selfCheckError}
                        onSave={(response) => {
                          if (status.logId) {
                            void saveSelfCheck(key, status.logId, response);
                          }
                        }}
                        onDismiss={() => patch(key, { selfCheckDismissed: true })}
                      />
                    )}
                    {completed && !status.integrationDismissed && (
                      <IntegrationPrompt
                        practiceTitle={item.title}
                        state={status.integration}
                        error={status.integrationError}
                        onSubmit={(input) => {
                          if (status.logId) {
                            void saveIntegration(key, status.logId, input);
                          }
                        }}
                        onDismiss={() =>
                          patch(key, { integrationDismissed: true })
                        }
                      />
                    )}
                  </PracticeCard>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
