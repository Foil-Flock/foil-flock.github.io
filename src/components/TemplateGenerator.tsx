import { useState, useMemo, useRef } from "preact/hooks";

/* ── Types ──────────────────────────────────────────────── */

interface UserField {
  id: string;
  label: string;
  type: string;
  required: boolean;
  placeholder?: string;
  default?: string | number;
}

interface Template {
  id: string;
  name: string;
  description: string;
  use_when: string;
  user_fields: UserField[];
  body: string;
}

interface Agency {
  id: string;
  name: string;
  contact: {
    records_access_officer: string | null;
    mailing_address: string | null;
    email: string | null;
    form_url: string | null;
  };
}

interface StateFragments {
  statute_invocation: string;
  response_reminder: string;
  fee_cap_notice: string;
  electronic_delivery_clause: string;
  appeal_deadline_warning: string;
}

interface StateData {
  statute_short_name: string;
  initial_response_days: number;
  appeal_body: string;
  advisory_body_name: string | null;
  advisory_body_address: string | null;
  fragments: StateFragments;
}

interface Props {
  templates: Template[];
  agency: Agency | null;
  stateData: StateData;
}

/* ── Component ──────────────────────────────────────────── */

export default function TemplateGenerator({ templates, agency, stateData }: Props) {
  const [activeTemplateId, setActiveTemplateId] = useState(templates[0]?.id ?? "");
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);

  const activeTemplate = useMemo(
    () => templates.find((t) => t.id === activeTemplateId) ?? templates[0],
    [activeTemplateId, templates]
  );

  function updateField(id: string, value: string) {
    setFormValues((prev) => ({ ...prev, [id]: value }));
    setCopied(false);
  }

  function getFieldValue(id: string): string {
    const field = activeTemplate?.user_fields.find((f) => f.id === id);
    return formValues[id] ?? (field?.default != null ? String(field.default) : "");
  }

  /* ── Interpolation ───────────────────────────────────── */

  const generatedLetter = useMemo(() => {
    if (!activeTemplate) return "";
    let body = activeTemplate.body;

    // Agency placeholders
    const rao = agency?.contact?.records_access_officer ?? "Records Access Officer";
    body = body.replace(/__AGENCY_RAO_OR_HEAD__/g, rao);
    body = body.replace(/__AGENCY_APPEALS_OFFICER__/g, stateData.appeal_body);
    body = body.replace(/__AGENCY_NAME__/g, agency?.name ?? "[Agency Name]");

    // State placeholders
    body = body.replace(/__STATE_SHORT_NAME__/g, stateData.statute_short_name);
    body = body.replace(/__STATE_STATUTE_INVOCATION__/g, stateData.fragments.statute_invocation);
    body = body.replace(/__STATE_RESPONSE_REMINDER__/g, stateData.fragments.response_reminder);
    body = body.replace(/__STATE_ELECTRONIC_DELIVERY__/g, stateData.fragments.electronic_delivery_clause);
    body = body.replace(/__STATE_APPEAL_DEADLINE_WARNING__/g, stateData.fragments.appeal_deadline_warning);
    body = body.replace(/__STATE_INITIAL_RESPONSE_DAYS__/g, String(stateData.initial_response_days));

    // Fee cap notice with user-specified cap
    const feeCap = getFieldValue("fee_cap") || "25";
    const feeNotice = stateData.fragments.fee_cap_notice.replace(/__FEE_CAP__/g, feeCap);
    body = body.replace(/__STATE_FEE_CAP_NOTICE__/g, feeNotice);

    // Advisory body conditional
    if (stateData.advisory_body_name) {
      body = body.replace(/__IF_ADVISORY_BODY__/g, "");
      body = body.replace(/__ENDIF__/g, "");
      body = body.replace(/__ADVISORY_BODY_NAME__/g, stateData.advisory_body_name);
      body = body.replace(/__ADVISORY_BODY_ADDRESS__/g, stateData.advisory_body_address ?? "");
    } else {
      body = body.replace(/__IF_ADVISORY_BODY__[\s\S]*?__ENDIF__\n?/g, "");
    }

    // User fields
    const today = new Date().toISOString().split("T")[0];
    body = body.replace(/__TODAY_DATE__/g, today);
    body = body.replace(/__USER_NAME__/g, getFieldValue("name") || "[Your Name]");
    body = body.replace(/__USER_ADDRESS__/g, getFieldValue("address") || "[Your Address]");
    body = body.replace(/__USER_EMAIL__/g, getFieldValue("email") || "[Your Email]");
    body = body.replace(/__USER_DATE__/g, getFieldValue("date") || "[Date]");
    body = body.replace(/__USER_TIME_START__/g, getFieldValue("time_start") || "[Start Time]");
    body = body.replace(/__USER_TIME_END__/g, getFieldValue("time_end") || "[End Time]");
    body = body.replace(/__USER_START_DATE__/g, getFieldValue("start_date") || "2020");
    body = body.replace(/__USER_AUDIT_DAYS__/g, getFieldValue("audit_days") || "90");
    body = body.replace(/__USER_ORIGINAL_DATE__/g, getFieldValue("original_date") || "[Date]");
    body = body.replace(/__USER_DENIAL_DATE__/g, getFieldValue("denial_date") || "[Date]");
    body = body.replace(/__USER_RECORDS_DESCRIPTION__/g, getFieldValue("records_description") || "[description of records]");
    body = body.replace(/__USER_EXEMPTION_CITED__/g, getFieldValue("exemption_cited") || "[exemption]");
    body = body.replace(/__USER_COUNTER_ARGUMENT__/g, getFieldValue("counter_argument") || "[your argument]");

    // FOIL ref conditional
    const foilRef = getFieldValue("foil_ref");
    if (foilRef) {
      body = body.replace(/__IF_FOIL_REF__/g, "");
      body = body.replace(/__ENDIF__/g, "");
      body = body.replace(/__USER_FOIL_REF__/g, foilRef);
    } else {
      body = body.replace(/__IF_FOIL_REF__[\s\S]*?__ENDIF__/g, "");
    }

    // Location conditional
    const location = getFieldValue("location");
    if (location) {
      body = body.replace(/__IF_LOCATION__/g, "");
      body = body.replace(/__ENDIF__/g, "");
      body = body.replace(/__USER_LOCATION__/g, location);
    } else {
      body = body.replace(/__IF_LOCATION__[\s\S]*?__ENDIF__\n?/g, "");
    }

    // Clean up any remaining conditionals
    body = body.replace(/__IF_\w+__[\s\S]*?__ENDIF__\n?/g, "");

    return body.trim();
  }, [activeTemplate, formValues, agency, stateData]);

  /* ── Copy to clipboard ───────────────────────────────── */

  async function copyLetter() {
    try {
      await navigator.clipboard.writeText(generatedLetter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback: select the text
      if (outputRef.current) {
        const range = document.createRange();
        range.selectNodeContents(outputRef.current);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
      }
    }
  }

  /* ── Render ───────────────────────────────────────────── */

  return (
    <div class="template-gen" id="generate">
      <h2>Generate a request letter</h2>

      {agency && (
        <p class="text-secondary" style={{ fontSize: "14px", marginBottom: "var(--gap-md)" }}>
          For <strong>{agency.name}</strong>
        </p>
      )}

      {/* template picker */}
      <div class="template-tabs" role="tablist">
        {templates.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={t.id === activeTemplateId}
            class={`template-tab ${t.id === activeTemplateId ? "active" : ""}`}
            onClick={() => {
              setActiveTemplateId(t.id);
              setFormValues({});
              setCopied(false);
            }}
          >
            {t.name}
          </button>
        ))}
      </div>

      {activeTemplate && (
        <>
          <div class="callout" style={{ marginTop: "var(--gap-md)" }}>
            <div class="callout-label">When to use</div>
            <p>{activeTemplate.use_when}</p>
          </div>

          {/* user fields */}
          <div class="gen-form" style={{ marginTop: "var(--gap-md)" }}>
            {/* Common fields first */}
            <div class="form-group">
              <label for="gen-name">Your name</label>
              <input
                id="gen-name"
                type="text"
                value={getFieldValue("name")}
                onInput={(e) => updateField("name", (e.target as HTMLInputElement).value)}
              />
            </div>
            <div class="form-group">
              <label for="gen-address">Your mailing address</label>
              <input
                id="gen-address"
                type="text"
                value={getFieldValue("address")}
                onInput={(e) => updateField("address", (e.target as HTMLInputElement).value)}
              />
            </div>
            <div class="form-group">
              <label for="gen-email">Your email</label>
              <input
                id="gen-email"
                type="email"
                value={getFieldValue("email")}
                onInput={(e) => updateField("email", (e.target as HTMLInputElement).value)}
              />
            </div>

            <hr />

            {/* Template-specific fields */}
            {activeTemplate.user_fields.map((field) => {
              // Skip fee_cap since it's handled in the common section feel
              const inputId = `gen-${field.id}`;
              return (
                <div class="form-group" key={field.id}>
                  <label for={inputId}>
                    {field.label}
                    {!field.required && <span class="hint"> (optional)</span>}
                  </label>
                  {field.type === "textarea" ? (
                    <textarea
                      id={inputId}
                      value={getFieldValue(field.id)}
                      placeholder={field.placeholder}
                      onInput={(e) => updateField(field.id, (e.target as HTMLTextAreaElement).value)}
                    />
                  ) : (
                    <input
                      id={inputId}
                      type={field.type === "number" ? "number" : field.type}
                      value={getFieldValue(field.id)}
                      placeholder={field.placeholder}
                      onInput={(e) => updateField(field.id, (e.target as HTMLInputElement).value)}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* output */}
          <div class="gen-output" style={{ marginTop: "var(--gap-lg)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--gap-sm)" }}>
              <span class="eyebrow">Generated letter</span>
              <button class="copy-btn" onClick={copyLetter}>
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div class="letter-output" ref={outputRef}>{generatedLetter}</div>
          </div>

          {/* next steps */}
          <div class="next-steps">
            <h3>Now file it</h3>
            <p class="next-steps-intro">
              Copy your letter above, then choose how to send it:
            </p>
            <div class="next-steps-options">
              <div class="next-step-card">
                <div class="next-step-label">Option 1</div>
                <div class="next-step-title">Send it yourself</div>
                <p>
                  Submit the letter directly — through the agency's records
                  portal, by email, or by mail. You keep full control and
                  avoid third-party accounts.
                </p>
                {agency?.contact?.form_url ? (
                  <a
                    class="next-step-action"
                    href={agency.contact.form_url}
                    target="_blank"
                    rel="noopener"
                  >
                    Agency records portal
                  </a>
                ) : agency?.contact?.email ? (
                  <a
                    class="next-step-action"
                    href={`mailto:${agency.contact.email}?subject=${encodeURIComponent(stateData.statute_short_name + " Request")}&body=${encodeURIComponent(generatedLetter)}`}
                  >
                    Open in email client
                  </a>
                ) : agency?.contact?.mailing_address ? (
                  <span class="next-step-note">
                    Mail to: {agency.contact.mailing_address}
                  </span>
                ) : (
                  <span class="next-step-note">
                    Look up the agency's records officer on their website and
                    submit by email, web form, or mail.
                  </span>
                )}
              </div>
              <div class="next-step-card">
                <div class="next-step-label">Option 2</div>
                <div class="next-step-title">File through MuckRock</div>
                <p>
                  MuckRock handles submission, tracks deadlines, sends
                  follow-ups, and publicly archives the response. Free
                  accounts available.
                </p>
                <a
                  class="next-step-action"
                  href="https://www.muckrock.com/foi/create/"
                  target="_blank"
                  rel="noopener"
                >
                  Start a request on MuckRock
                </a>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
