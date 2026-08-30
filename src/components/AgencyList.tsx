import { useState, useMemo } from "preact/hooks";

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

interface Props {
  agencies: Agency[];
}

const PAGE_SIZE = 20;

type SortField = "name" | "cameras" | "jurisdiction";

export default function AgencyList({ agencies }: Props) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortField>("cameras");
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);

  const statuses = useMemo(() => {
    const s = new Set(agencies.map((a) => a.alpr.contract_status));
    return Array.from(s).sort();
  }, [agencies]);

  const filtered = useMemo(() => {
    let result = agencies;

    // Text search
    if (query.trim()) {
      const q = query.toLowerCase();
      result = result.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          a.jurisdiction.toLowerCase().includes(q)
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      result = result.filter((a) => a.alpr.contract_status === statusFilter);
    }

    // Sort
    result = [...result].sort((a, b) => {
      if (sortBy === "cameras") {
        return (b.alpr.camera_count ?? 0) - (a.alpr.camera_count ?? 0);
      }
      if (sortBy === "jurisdiction") {
        return a.jurisdiction.localeCompare(b.jurisdiction);
      }
      return a.name.localeCompare(b.name);
    });

    return result;
  }, [agencies, query, statusFilter, sortBy]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // Reset page when filters change
  const handleQuery = (v: string) => {
    setQuery(v);
    setPage(0);
  };
  const handleStatus = (v: string) => {
    setStatusFilter(v);
    setPage(0);
  };
  const handleSort = (v: SortField) => {
    setSortBy(v);
    setPage(0);
  };

  return (
    <div class="agency-list-wrap">
      {/* Controls */}
      <div class="agency-controls">
        <input
          type="text"
          class="agency-search"
          placeholder="Search agencies…"
          value={query}
          onInput={(e) => handleQuery((e.target as HTMLInputElement).value)}
        />
        <div class="agency-filters">
          <select
            class="agency-select"
            value={statusFilter}
            onChange={(e) =>
              handleStatus((e.target as HTMLSelectElement).value)
            }
          >
            <option value="all">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            class="agency-select"
            value={sortBy}
            onChange={(e) =>
              handleSort((e.target as HTMLSelectElement).value as SortField)
            }
          >
            <option value="cameras">Most cameras</option>
            <option value="name">Name A–Z</option>
            <option value="jurisdiction">Jurisdiction A–Z</option>
          </select>
        </div>
      </div>

      {/* Count */}
      <div class="agency-count">
        {filtered.length} of {agencies.length}{" "}
        {agencies.length === 1 ? "agency" : "agencies"}
        {totalPages > 1 &&
          ` · page ${page + 1} of ${totalPages}`}
      </div>

      {/* List */}
      <div class="agency-cards">
        {paginated.map((a) => (
          <div
            key={a.id}
            class={`agency-card${expanded === a.id ? " expanded" : ""}`}
            onClick={() => setExpanded(expanded === a.id ? null : a.id)}
          >
            <div class="agency-card-row">
              <div class="agency-name">{a.name}</div>
              <div class="agency-meta">
                <span class="agency-tag">{a.jurisdiction}</span>
                <span class={`agency-tag ${a.alpr.contract_status}`}>
                  {a.alpr.contract_status}
                </span>
                {a.alpr.camera_count != null && a.alpr.camera_count > 0 && (
                  <span class="agency-tag cameras">
                    {a.alpr.camera_count} cameras
                  </span>
                )}
              </div>
            </div>

            {expanded === a.id && (
              <div class="agency-detail">
                <dl>
                  {a.alpr.vendor && (
                    <>
                      <dt>Vendor</dt>
                      <dd>{a.alpr.vendor}</dd>
                    </>
                  )}
                  {a.alpr.retention_period && (
                    <>
                      <dt>Retention</dt>
                      <dd>{a.alpr.retention_period}</dd>
                    </>
                  )}
                  {a.contact.mailing_address && (
                    <>
                      <dt>Address</dt>
                      <dd>{a.contact.mailing_address}</dd>
                    </>
                  )}
                  {a.contact.email && (
                    <>
                      <dt>Email</dt>
                      <dd>
                        <a href={`mailto:${a.contact.email}`}>{a.contact.email}</a>
                      </dd>
                    </>
                  )}
                  {a.contact.form_url && (
                    <>
                      <dt>FOIA portal</dt>
                      <dd>
                        <a href={a.contact.form_url} target="_blank" rel="noopener">
                          Online form
                        </a>
                      </dd>
                    </>
                  )}
                  {a.contact.submission_methods.length > 0 && (
                    <>
                      <dt>Submit via</dt>
                      <dd>{a.contact.submission_methods.join(", ")}</dd>
                    </>
                  )}
                  {a.notes && (
                    <>
                      <dt>Notes</dt>
                      <dd>{a.notes}</dd>
                    </>
                  )}
                </dl>
                {a.sources.length > 0 && (
                  <div class="agency-sources">
                    {a.sources.map((src, i) => (
                      <a
                        key={i}
                        href={src}
                        target="_blank"
                        rel="noopener"
                        class="source-link"
                      >
                        Source {i + 1}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div class="agency-pagination">
          <button
            class="page-btn"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            ← Prev
          </button>
          <span class="page-info">
            {page + 1} / {totalPages}
          </span>
          <button
            class="page-btn"
            disabled={page >= totalPages - 1}
            onClick={() => setPage(page + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
