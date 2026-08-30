# Foil Flock Roadmap

Current: 25 states verified, 29 agencies, 4 letter templates, deployed to GitHub Pages.


## Phase 1 — Complete state coverage

Add the remaining 25 states + DC. Each state needs a YAML file in
`src/content/states/` following the schema in `config.ts`, verified
against the actual statute text.

### Batch A — High ALPR deployment states ✓
- [x] Tennessee
- [x] North Carolina
- [x] South Carolina
- [x] Indiana
- [x] Missouri
- [x] Alabama
- [x] Louisiana
- [x] Oklahoma
- [x] Maryland
- [x] Minnesota

### Batch B — States with known ALPR programs ✓
- [x] Oregon
- [x] Connecticut
- [x] Wisconsin
- [x] Iowa
- [x] Kentucky
- [x] Kansas
- [x] Arkansas
- [x] Mississippi
- [x] Nebraska
- [x] Nevada
- [x] New Hampshire
- [x] New Mexico
- [x] Utah
- [x] West Virginia
- [x] Hawaii

### Batch C — Low ALPR deployment / remaining
- [ ] Alaska
- [ ] Delaware
- [ ] Idaho
- [ ] Maine
- [ ] Montana
- [ ] North Dakota
- [ ] Rhode Island
- [ ] South Dakota
- [ ] Vermont
- [ ] Wyoming
- [ ] District of Columbia


## Phase 2 — Scale the agency directory

29 agencies is thin. FlockRadar alone has thousands of entries.

- [ ] Run `fetch_agencies.py` against FlockRadar's full dataset
- [ ] Cross-reference with MuckRock API for contact info (email, FOIA officer, address)
- [ ] Add agency-level metadata: FOIA portal URL, online submission supported (bool)
- [ ] Add per-agency "last verified" date field
- [ ] Paginate or lazy-load the agency list on state pages (some states will have 100+)
- [ ] Add agency search/filter on state pages (by jurisdiction, camera count, status)


## Phase 3 — App polish

### SEO & discoverability
- [ ] Add Open Graph and Twitter Card meta tags to Base.astro
- [ ] Add `@astrojs/sitemap` integration
- [ ] Add structured data (JSON-LD) for state law pages (LegalDocument schema)
- [ ] Wire up Pagefind (already a devDep) for full-site search

### Template generator improvements
- [ ] Copy-to-clipboard button on generated letters
- [ ] Print-friendly stylesheet for generated letters
- [ ] "Download as .txt" or "Download as .pdf" option
- [ ] Let user select from multiple agencies per state (currently auto-picks first)
- [ ] Save user info (name, address) in localStorage to pre-fill across visits
- [ ] Add template: Data Retention Policy request
- [ ] Add template: Data Sharing Agreement request

### State page enhancements
- [ ] Add total camera count per state in stat-grid (aggregate from agencies.json)

### UI / UX
- [ ] Mobile responsiveness audit (especially stat-grid, template tabs)
- [ ] Accessibility audit (color contrast, focus states, screen reader flow)
- [ ] Add state map visualization on /states index page
- [ ] Color-code states by ALPR exemption status on map/grid
- [ ] Add "How to use this site" walkthrough or FAQ section
- [ ] Dark mode toggle (CSS supports it; add a visible switch)
- [ ] Add favicon


## Phase 4 — Community & contributor infrastructure

- [ ] Add CONTRIBUTING.md with step-by-step guide for adding a state
- [ ] Add GitHub issue templates (new state, agency correction, camera report)
- [ ] Add "last verified" date field to state YAML schema
- [ ] Add a data freshness badge or indicator per state
- [ ] Set up a GitHub Discussion board for community Q&A
- [ ] Add "Report an error" link on each state page (links to pre-filled GitHub issue)


## Phase 5 — Stretch goals

- [ ] Automated statute change monitoring (scrape state legislature RSS/APIs)
- [ ] Email delivery: let users send generated letters directly from the site
- [ ] Track request outcomes: community-reported success/denial rates by agency
- [ ] Integration with MuckRock filing (deep-link to pre-filled MuckRock form)
- [ ] Blog/updates section for ALPR news and successful records requests
- [ ] API endpoint for programmatic access to state law data (JSON)


## Done

- [x] Core site architecture (Astro + Preact + Fuse.js)
- [x] 25 state YAML files created (Batches A + B)
- [x] All 25 states verified against primary statutory sources
- [x] 29 agencies across 15 states
- [x] 4 letter templates (detection data, contracts/policies, appeal denial, appeal non-response)
- [x] Fuzzy search on landing page
- [x] Resources page with external links
- [x] GitHub Pages deployment with nightly rebuild
- [x] Agency enrichment script (`fetch_agencies.py`)
