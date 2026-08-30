# Foil Flock Roadmap

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
- [x] ~~Cross-reference with MuckRock API~~ — shelved: v2 API only provides `muckrock_id` and `agency_types` (no contact fields), and Cloudflare now blocks programmatic access with JS challenges. 10 agencies already matched. Revisit if MuckRock offers token-based API auth.
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
- [ ] Print-friendly stylesheet for generated letters
- [ ] "Download as .txt" or "Download as .pdf" option
- [ ] Save user info (name, address) in localStorage to pre-fill across visits
- [ ] Add template: Data Retention Policy request
- [ ] Add template: Data Sharing Agreement request

### State page enhancements

### UI / UX
- [ ] Add state map visualization on /states index page
- [ ] Color-code states by ALPR exemption status on map/grid
- [ ] Add "How to use this site" walkthrough or FAQ section
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
