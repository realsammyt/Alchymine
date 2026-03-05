/**
 * EvidenceBadge — compact inline badge showing the evidence level for a result.
 *
 * Levels:
 *   strong      — green dot  + "Peer-Reviewed"       (peer-reviewed research)
 *   moderate    — yellow dot + "Emerging Research"    (consistent but limited studies)
 *   emerging    — orange dot + "Theoretical"          (preliminary / developing evidence)
 *   traditional — purple dot + "Cultural/Historical"  (valued for personal meaning)
 *   entertainment — gray dot + "Entertainment"        (for entertainment purposes only)
 */

export type { EvidenceLevel } from "./EvidenceRatingBadge";
export { default } from "./EvidenceRatingBadge";
