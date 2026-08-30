import { useState, useMemo, useRef } from "preact/hooks";
import Fuse from "fuse.js";

interface Agency {
  id: string;
  name: string;
  type: string;
  jurisdiction: string;
  jurisdiction_type: string;
  state: string;
  contact: {
    records_access_officer: string | null;
    email: string | null;
    phone: string | null;
    form_url: string | null;
    mailing_address: string | null;
    submission_methods: string[];
  };
  alpr: {
    vendor: string | null;
    camera_count: number | null;
    retention_period: string | null;
    contract_status: string;
    transparency_portal_url: string | null;
  };
  sources: string[];
  last_verified: string;
  notes?: string;
}

interface StateInfo {
  slug: string;
  name: string;
  abbreviation: string;
  statute_short_name: string;
}

interface Props {
  agencies: Agency[];
  states: StateInfo[];
}

export default function Search({ agencies, states }: Props) {
  const [query, setQuery] = useState("");
  const [selectedAgency, setSelectedAgency] = useState<Agency | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const fuse = useMemo(
    () =>
      new Fuse(agencies, {
        keys: [
          { name: "name", weight: 0.4 },
          { name: "jurisdiction", weight: 0.35 },
          { name: "state", weight: 0.15 },
          { name: "notes", weight: 0.1 },
        ],
        threshold: 0.35,
        includeScore: true,
      }),
    [agencies]
  );

  const results = useMemo(() => {
    if (!query.trim()) return [];
    return fuse.search(query).slice(0, 12);
  }, [query, fuse]);

  const stateMap = useMemo(() => {
    const m = new Map<string, StateInfo>();
    for (const s of states) m.set(s.abbreviation, s);
    return m;
  }, [states]);

  function statusLabel(status: string) {
    const map: Record<string, string> = {
      active: "Active",
      cancelled: "Cancelled",
      unknown: "Unknown",
      pending: "Pending",
    };
    return map[status] ?? status;
  }

  return (
    <div class="search-section">
      <div class="search-wrap">
        <svg class="search-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="6.5" cy="6.5" r="5" />
          <line x1="10" y1="10" x2="15" y2="15" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          placeholder="Search by city, county, or agency name..."
          value={query}
          onInput={(e) => {
            setQuery((e.target as HTMLInputElement).value);
            setSelectedAgency(null);
          }}
          aria-label="Search agencies"
        />
      </div>

      {query.trim() && results.length === 0 && (
        <div class="search-empty">
          <p>No agencies found matching "{query}".</p>
          <p class="search-empty-hint">
            Know of an ALPR deployment here?{" "}
            <a href="https://github.com/Foil-Flock/foil-flock.github.io/issues/new" target="_blank" rel="noopener">
              Report it
            </a>{" "}
            so we can add it.
          </p>
        </div>
      )}

      {results.length > 0 && !selectedAgency && (
        <div class="search-results" role="list">
          {results.map(({ item }) => {
            const stateInfo = stateMap.get(item.state);
            return (
              <button
                key={item.id}
                class="agency-card agency-card--interactive"
                role="listitem"
                onClick={() => setSelectedAgency(item)}
              >
                <div class="agency-name">{item.name}</div>
                <div class="agency-meta">
                  <span class="agency-tag">{item.jurisdiction}, {item.state}</span>
                  <span class={`agency-tag ${item.alpr.contract_status}`}>
                    {statusLabel(item.alpr.contract_status)}
                  </span>
                  {item.alpr.camera_count && (
                    <span class="agency-tag">{item.alpr.camera_count} cameras</span>
                  )}
                  {item.alpr.vendor && item.alpr.vendor !== "unknown" && (
                    <span class="agency-tag">{item.alpr.vendor}</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {selectedAgency && (
        <AgencyDetail
          agency={selectedAgency}
          stateInfo={stateMap.get(selectedAgency.state) ?? null}
          onBack={() => setSelectedAgency(null)}
        />
      )}
    </div>
  );
}

/* ── Agency detail panel ────────────────────────────────── */

interface AgencyDetailProps {
  agency: Agency;
  stateInfo: StateInfo | null;
  onBack: () => void;
}

function AgencyDetail({ agency, stateInfo, onBack }: AgencyDetailProps) {
  const a = agency;
  const methods = a.contact.submission_methods
    .map((m) => m.replace("_", " "))
    .join(", ");

  return (
    <div class="agency-detail">
      <button class="btn btn-secondary back-btn" onClick={onBack}>
        <span aria-hidden="true">&larr;</span> Back to results
      </button>

      <h2>{a.name}</h2>
      <p class="text-secondary" style={{ marginTop: "-0.25rem" }}>
        {a.jurisdiction} ({a.state}) &middot; {a.jurisdiction_type}
      </p>

      {/* stat grid */}
      <div class="stat-grid">
        <div class="stat-block">
          <div class="stat-label">Contract</div>
          <div class={`stat-value ${a.alpr.contract_status === "cancelled" ? "good" : a.alpr.contract_status === "active" ? "warn" : ""}`}>
            {a.alpr.contract_status === "active"
              ? "Active"
              : a.alpr.contract_status === "cancelled"
                ? "Cancelled"
                : "Unknown"}
          </div>
        </div>
        {a.alpr.camera_count && (
          <div class="stat-block">
            <div class="stat-label">Cameras</div>
            <div class="stat-value">{a.alpr.camera_count}</div>
          </div>
        )}
        {a.alpr.retention_period && (
          <div class="stat-block">
            <div class="stat-label">Retention</div>
            <div class="stat-value">{a.alpr.retention_period}</div>
          </div>
        )}
        {a.alpr.vendor && a.alpr.vendor !== "unknown" && (
          <div class="stat-block">
            <div class="stat-label">Vendor</div>
            <div class="stat-value">{a.alpr.vendor}</div>
          </div>
        )}
      </div>

      {/* contact */}
      <div class="card" style={{ marginTop: "var(--gap-md)" }}>
        <h3>How to submit a request</h3>
        <dl class="detail-list">
          {a.contact.form_url && (
            <>
              <dt>Online form</dt>
              <dd><a href={a.contact.form_url} target="_blank" rel="noopener">{a.contact.form_url.replace(/^https?:\/\//, "").split("/")[0]}</a></dd>
            </>
          )}
          {a.contact.mailing_address && (
            <>
              <dt>Mailing address</dt>
              <dd>{a.contact.mailing_address}</dd>
            </>
          )}
          {a.contact.email && (
            <>
              <dt>Email</dt>
              <dd><a href={`mailto:${a.contact.email}`}>{a.contact.email}</a></dd>
            </>
          )}
          {a.contact.phone && (
            <>
              <dt>Phone</dt>
              <dd>{a.contact.phone}</dd>
            </>
          )}
          <dt>Accepted methods</dt>
          <dd>{methods}</dd>
        </dl>
      </div>

      {/* notes */}
      {a.notes && (
        <div class="callout" style={{ marginTop: "var(--gap-md)" }}>
          <div class="callout-label">Note</div>
          <p>{a.notes}</p>
        </div>
      )}

      {/* state law link */}
      {stateInfo && (
        <div style={{ marginTop: "var(--gap-md)", display: "flex", gap: "var(--gap-sm)", flexWrap: "wrap" }}>
          <a href={`/states/${stateInfo.slug}`} class="btn btn-primary">
            {stateInfo.abbreviation} {stateInfo.statute_short_name} guide
          </a>
          <a href={`/states/${stateInfo.slug}#generate`} class="btn btn-secondary">
            Generate a request letter
          </a>
        </div>
      )}

      {/* sources */}
      {a.sources.length > 0 && (
        <div class="source-links">
          <span class="eyebrow">Sources</span>
          {a.sources.map((url) => (
            <a key={url} href={url} target="_blank" rel="noopener" class="source-link">
              {new URL(url).hostname.replace(/^www\./, "")}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
