# Jurisdictions — Coverage and Data Sources

## United States (US)

**Data source:** [Open States API v3](https://docs.openstates.org/api-v3/)
**Status:** Implemented — `backend/src/monitor.py` `OpenStatesMonitor`
**Coverage:** All 50 states + federal Congress
**API key required:** Yes (free tier at openstates.org/api/)

### Jurisdiction slugs

Open States uses the following slug format:
- Federal: `us`
- States: `us/ca`, `us/ny`, `us/tx`, etc.

Default monitored jurisdictions (configurable via `DEFAULT_US_JURISDICTIONS` in `monitor.py`):
```
us, us/ca, us/ny, us/tx, us/fl, us/il, us/wa, us/co, us/or, us/mn, us/ma, us/nj, us/md
```

### Data returned per bill

- Title, bill ID, jurisdiction
- Status (last action description)
- Sponsor names and IDs
- Committee assignment
- Abstracts/summaries
- Timestamps (introduced, last updated)
- OpenStates URL for full text

### Adding a new US state

Add the state slug to `DEFAULT_US_JURISDICTIONS` in `backend/src/monitor.py`. No other changes needed.

---

## India

**Data source:** [PRS Legislative Research](https://prsindia.org/) — structured data pending
**Status:** Stub implemented — `IndiaMonitor` in `backend/src/monitor.py`
**Coverage:** Central government (Lok Sabha, Rajya Sabha); state assembly bills not yet supported
**Open issue:** [#2 — Add India PRS Legislative Research API integration](https://github.com/Open-Paws/open-paws-policy-watch/issues/2)

### Priority ministry coverage

Based on `animalparliament` analysis of India policy landscape:

| Ministry | Animal welfare relevance |
|----------|--------------------------|
| Ministry of Environment, Forest and Climate Change (MoEF&CC) | Wildlife protection, Prevention of Cruelty to Animals Act |
| Ministry of Fisheries, Animal Husbandry and Dairying (MFAHD) | Farmed animal welfare, dairy industry regulation |
| Ministry of Commerce (APEDA) | Live export and slaughter export standards |
| Ministry of Health | Animal testing regulations |

### Implementation plan

1. Scrape PRS Legislative Research bill listings (prsindia.org/billtrack)
2. Filter by ministry relevance tags
3. Run through `classifier.py` — India-specific keywords needed (see below)
4. Alert via Telegram to India coalition partners

### India-specific keywords to add to `classifier.py`

```
HELPS: "prevention of cruelty", "animal welfare board", "wildlife protection",
       "transport of animals rules", "ban live export"
HARMS: "slaughter house rules exemption", "gaushalas exemption",
       "animal sacrifice", "jallikattu", "kambala"
```

---

## European Union

**Data source:** [Eur-Lex](https://eur-lex.europa.eu/) — SPARQL endpoint and RSS feeds
**Status:** Stub implemented — `EUMonitor` in `backend/src/monitor.py`
**Coverage:** EU regulations and directives with animal welfare impact
**Open issue:** [#3 — Add EU Eur-Lex monitoring for animal transport and welfare regulations](https://github.com/Open-Paws/open-paws-policy-watch/issues/3)

### Priority EU legislation areas

| Category | Key legislation |
|----------|----------------|
| Farmed animal welfare | Council Directive 98/58/EC (general) — currently under revision |
| Slaughter | Council Regulation 1099/2009 — animal welfare at time of killing |
| Transport | Council Regulation 1/2005 — live animal transport |
| Wildlife trade | Regulation 338/97 (CITES implementation) |
| Animal testing | Directive 2010/63/EU |

### Implementation plan

1. Poll Eur-Lex RSS feed: `https://eur-lex.europa.eu/oj/direct-access.html`
2. Filter by EuroVoc descriptor codes for animal welfare (descriptor: `5530 animal welfare`)
3. Use SPARQL endpoint for structured metadata
4. Translate from EUR-Lex multilingual to classification pipeline

### EU SPARQL example

```sparql
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?work ?title WHERE {
  ?work cdm:work_has_resource-type <http://publications.europa.eu/resource/authority/resource-type/REG> .
  ?work cdm:work_is_about_concept_eurovoc <http://eurovoc.europa.eu/5530> .
}
LIMIT 20
```

---

## Adding a New Jurisdiction

1. Create a new monitor class in `backend/src/monitor.py` following the pattern of `OpenStatesMonitor`
2. The class must implement `async def fetch_bills(self) -> list[Bill]`
3. Register the monitor in `BillMonitor.fetch_and_classify()`
4. Add jurisdiction-specific keywords to `HELPS_KEYWORDS` / `HARMS_KEYWORDS` in `classifier.py`
5. Update this file with coverage details, data source, and implementation notes
6. Add the jurisdiction to `frontend/src/components/ContactRep.tsx` if representative lookup is available
