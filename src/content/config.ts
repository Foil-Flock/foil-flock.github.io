import { defineCollection, z } from "astro:content";

/**
 * State public records law schema.
 *
 * Each YAML file in src/content/states/ describes one state's
 * legal framework for records requests. The schema is deliberately
 * flat where possible so contributors can edit YAML without
 * navigating deep nesting.
 */
const states = defineCollection({
  type: "data",
  schema: z.object({
    // ── Identity ──────────────────────────────────────────────
    name: z.string(),
    abbreviation: z.string().length(2),
    slug: z.string(), // URL-safe, e.g. "new-york"

    // ── Statute ───────────────────────────────────────────────
    statute: z.object({
      name: z.string(), // e.g. "Freedom of Information Law (FOIL)"
      short_name: z.string(), // e.g. "FOIL"
      citation: z.string(), // e.g. "Public Officers Law §§ 84-90"
      url: z.string().url(),
    }),

    // ── Access presumption ────────────────────────────────────
    presumption: z.enum(["open", "closed", "mixed"]),

    // ── Response timelines (business days unless noted) ───────
    response: z.object({
      initial_days: z.number(),
      final_days: z.number().nullable(),
      day_type: z.enum(["business", "calendar"]),
      notes: z.string().nullable().optional(),
    }),

    // ── Administrative appeal ─────────────────────────────────
    appeal: z.object({
      required_before_court: z.boolean(),
      deadline_days: z.number().nullable(),
      response_days: z.number().nullable(),
      body: z.string(), // who hears the appeal
      advisory_body: z
        .object({
          name: z.string(),
          url: z.string().url().nullable(),
          phone: z.string().nullable(),
          email: z.string().nullable(),
          address: z.string().nullable(),
        })
        .nullable()
        .optional(),
    }),

    // ── Enforcement & penalties ───────────────────────────────
    enforcement: z.object({
      penalty_type: z.enum(["per_day", "fee_shifting", "both", "none"]),
      per_day_cap: z.number().nullable(), // dollars, null if N/A
      attorney_fees: z.enum(["mandatory", "discretionary", "none"]),
      fee_trigger: z.string().nullable(), // condition for fee award
      court_action: z.string(), // e.g. "Article 78 proceeding"
      court_name: z.string(), // e.g. "Supreme Court"
      filing_fee_approx: z.number().nullable(), // dollars
      filing_deadline_days: z.number().nullable(), // from final denial; null if no specific deadline
      burden_of_proof: z.enum(["agency", "requester"]),
    }),

    // ── Fees charged to requesters ────────────────────────────
    fees: z.object({
      copy_per_page: z.number().nullable(), // dollars
      copy_max_size: z.string().nullable(),
      search_fee_allowed: z.boolean(),
      review_fee_allowed: z.boolean(),
      redaction_fee_allowed: z.boolean(),
      electronic_delivery_required: z.boolean(),
      notes: z.string().nullable().optional(),
    }),

    // ── ALPR-specific provisions ──────────────────────────────
    alpr: z.object({
      specific_exemption: z.boolean(),
      exemption_citation: z.string().nullable(),
      notes: z.string().nullable(),
    }),

    // ── Common exemptions invoked for surveillance records ────
    exemptions: z.array(
      z.object({
        text: z.string(),
        citation: z.string().optional(),
        url: z.string().url().optional(),
      })
    ),

    // ── Template fragments for letter generation ──────────────
    // These are state-specific phrases interpolated into request
    // and appeal letters. Stored here so templates stay generic.
    template_fragments: z.object({
      statute_invocation: z.string(),
      // e.g. "Pursuant to New York's Freedom of Information Law
      //        (Public Officers Law §§ 84-90)"
      response_reminder: z.string(),
      // e.g. "I expect a response within five business days as
      //        required by law."
      fee_cap_notice: z.string(),
      // e.g. "If fulfilling this request will cost more than
      //        $25.00, please provide an estimate before proceeding."
      electronic_delivery_clause: z.string(),
      // e.g. "I request that records be provided in electronic
      //        format pursuant to § 87(1)(b)."
      appeal_deadline_warning: z.string(),
      // e.g. "Under § 89(4)(a), you are required to respond to
      //        this appeal within ten business days."
    }),
  }),
});

export const collections = { states };
