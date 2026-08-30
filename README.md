# flock-foil

A static site that helps people file public records requests for surveillance technology (ALPR/Flock cameras) in their jurisdiction.

**Search** for your municipality → **learn** your state's public records law → **generate** a ready-to-send request letter.

## How it works

The site combines three data layers:

1. **State law database** (`src/content/states/*.yaml`) — 50 states + DC. Each file describes one state's public records law: statute citation, response deadlines, penalty structure, fee rules, appeal procedures, and ALPR-specific provisions. Updated manually; changes rarely.

2. **Agency directory** (`src/data/agencies.json`) — Government agencies with known ALPR deployments. Seeded from [FlockRadar](https://flockradar.com) and enriched with contact info from [MuckRock](https://www.muckrock.com/api/). Community contributions via PR.

3. **Request templates** (`src/templates/request-templates.json`) — Parameterized letter templates for detection data requests, contract/policy requests, and administrative appeals. The site interpolates state-specific legal language and agency contact info to generate a complete, ready-to-send letter.

No AI or server-side logic at runtime. Template generation happens in the browser. The whole site is static HTML deployed to GitHub Pages.

## Contributing

### Add or correct an agency

Edit `src/data/agencies.json` and submit a PR. Include a source URL for any factual claim (a news article, council minutes, or official page).

### Add a state

Create a new YAML file in `src/content/states/` following the schema in `src/content/config.ts`. The [RCFP Open Government Guide](https://www.rcfp.org/open-government-guide/) is the best starting reference for most states — verify key fields against the actual statute text.

### Report a camera

If you know of an ALPR deployment not in the directory, either:
- Open an issue with the agency name, location, and source
- Submit a PR to `agencies.json`
- Report it to [FlockRadar](https://flockradar.com) (we'll pick it up on the next sync)

## Development

```bash
npm install
npm run dev        # local dev server at localhost:4321
npm run build      # production build to dist/
```

### Fetching upstream data

```bash
# Enrich agency contact info from MuckRock (optional)
export MUCKROCK_TOKEN=your_token_here
python3 scripts/fetch_agencies.py
```

## Data sources

- [FlockRadar](https://flockradar.com) — open-source ALPR deployment map ([GitHub](https://github.com/rxsklife/flockradar))
- [MuckRock API](https://www.muckrock.com/api/) — agency contact database and FOIA filing platform
- [RCFP Open Government Guide](https://www.rcfp.org/open-government-guide/) — state-by-state public records law reference
- [Eyes On Flock](https://eyesonflock.com) — Flock transparency portal aggregator
- [UnFlocked](https://unflocked.org) — crowdsourced ALPR camera locations
- [Atlas of Surveillance](https://atlasofsurveillance.org) — EFF surveillance technology database

## License

Data files (YAML, JSON) are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Code is released under [MIT](https://opensource.org/licenses/MIT).
