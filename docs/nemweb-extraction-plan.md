# NEMWEB Data Extraction Pipeline — Implementation Plan

**Status:** Planning phase  
**Target:** Extend agentic-energy framework to support multiple NEMWEB data sources  
**Scope:** DISPATCHIS, PREDISPATCHIS, ROOFTOP_PV, and future NEMWEB reports  
**Constraints:** Metadata-driven, deterministic fixtures, no hardcoded source logic

---

## Executive Summary

This plan outlines the design and implementation of a comprehensive NEMWEB data extraction pipeline integrated into the agentic-energy metadata-driven framework. The pipeline will support multiple NEMWEB report types through a single configurable acquisition adapter and metadata-driven parser registry.

**Key principles:**
- **Metadata-driven:** All source configuration in `sources.json`, not code
- **Deterministic:** Fixture mode for testing without network access
- **Governed:** Host validation, rate limiting, error recovery
- **Observable:** Quality checks, quarantine reasons, lineage tracking
- **Extensible:** Parser registry pattern for future NEMWEB reports

---

## Phase 1: Research & Requirements

### 1.1 NEMWEB Source Inventory

| Report | ID | Grain | Frequency | Format | Key Fields | Status |
|---|---|---|---|---|---|---|
| DISPATCHIS | aemo_dispatchis | Region × Interval | 5 min | ZIP/CSV | region, interval_datetime, demand_mw, price_per_mwh | ✓ Existing |
| PREDISPATCHIS | aemo_predispatchis | Region × Interval | 30 min | ZIP/CSV | region, interval_datetime, demand_mw, price_per_mwh | Planned |
| ROOFTOP_PV | aemo_rooftop_pv | Region × Interval | 30 min | ZIP/CSV | region, interval_datetime, generation_mw | Planned |
| DEMAND_SIDE_PROGRAMS | aemo_dsp | Region × Interval | 5 min | ZIP/CSV | region, interval_datetime, dsp_mw | Planned |
| INTERCONNECTOR_FLOWS | aemo_interconnector | Interconnector × Interval | 5 min | ZIP/CSV | interconnector, interval_datetime, flow_mw | Planned |

### 1.2 NEMWEB Contract

**URL Pattern:**
```
https://nemweb.com.au/Reports/Current/{ReportType}_Reports/
```

**Archive Pattern:**
```
PUBLIC_{ReportType}_{YYYYMMDD}_{HHMM}.zip
```

**Contents:**
- Single CSV file per archive
- Header row with field names
- Data rows with values
- No embedded metadata

**Constraints:**
- HTTPS only, no redirects allowed
- Max response: 50 MB
- Max archive member: 50 MB
- User-Agent required
- No authentication (public data)

### 1.3 Freshness & Latency

| Report | Latency | Availability | Retention |
|---|---|---|---|
| DISPATCHIS | 5–10 min | Real-time | 90 days |
| PREDISPATCHIS | 30–60 min | Real-time | 90 days |
| ROOFTOP_PV | 30–60 min | Real-time | 90 days |

**Watermark strategy:**
- Use `interval_datetime` (event time) as watermark
- Track `_ingested_at` separately for freshness metrics
- Support late-arriving data within 24-hour window

---

## Phase 2: Metadata Design

### 2.1 Metadata Schema Extensions

Add to each source definition in `sources.json`:

```json
{
  "source_id": "aemo_dispatchis",
  "source_version": "1.0",
  "provider": "AEMO",
  "dataset": "DISPATCHIS",
  "region": "NEM",
  
  // Acquisition
  "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/DispatchIS_Reports/",
  "allowed_hosts": ["nemweb.com.au"],
  "format": "ZIP_CSV",
  "compression": "zip",
  "extraction_mode": "live",
  "schedule": "*/5 * * * *",
  "file_name_regex": "PUBLIC_DISPATCHIS_.*\\.zip$",
  
  // Parsing
  "parser_type": "nemweb_csv",
  "csv_config": {
    "delimiter": ",",
    "encoding": "utf-8",
    "skip_rows": 0,
    "skip_footer": 0
  },
  "field_mapping": {
    "REGION": "region",
    "INTERVAL_DATETIME": "interval_datetime",
    "TOTALDEMAND": "demand_mw",
    "RRP": "price_per_mwh"
  },
  "field_types": {
    "region": "string",
    "interval_datetime": "string",
    "demand_mw": "float",
    "price_per_mwh": "float"
  },
  
  // Timestamps
  "event_timestamp_field": "interval_datetime",
  "ingestion_timestamp_field": "_ingested_at",
  "source_timezone": "Australia/Brisbane",
  
  // Keys & dedup
  "natural_key": ["region", "interval_datetime"],
  "watermark_field": "interval_datetime",
  "deduplication_rule": "last_by_ingestion_sequence",
  
  // Quality
  "quality_checks": [
    "demand_mw >= 0",
    "price_per_mwh is not null",
    "region is not null",
    "interval_datetime is not null"
  ],
  "quarantine_policy": "isolate_with_reason",
  
  // Lineage
  "schema_reference": "aemo_dispatchis_v1",
  "licensing_provenance": "AEMO NEMWEB public DISPATCHIS report"
}
```

### 2.2 Metadata Validation

Add validation in `pipeline.py`:

```python
def _validate_source_metadata(source: dict) -> list[str]:
    """Validate source metadata completeness and consistency."""
    errors = []
    
    # Required fields
    required = [
        "source_id", "provider", "dataset", "format",
        "event_timestamp_field", "natural_key", "quality_checks"
    ]
    for field in required:
        if field not in source:
            errors.append(f"Missing required field: {field}")
    
    # Live-specific fields
    if source.get("extraction_mode") == "live":
        live_required = ["url_or_fixture_path", "allowed_hosts", "file_name_regex"]
        for field in live_required:
            if field not in source:
                errors.append(f"Live source missing: {field}")
    
    # Parser-specific validation
    if "parser_type" in source:
        if source["parser_type"] == "nemweb_csv":
            if "field_mapping" not in source:
                errors.append("nemweb_csv parser requires field_mapping")
    
    return errors
```

---

## Phase 3: Acquisition Adapter

### 3.1 NEMWEB Archive Fetcher

Extend `acquisition.py` with NEMWEB-specific logic:

```python
def acquire_nemweb_archive(source: dict) -> tuple[str, bytes]:
    """Fetch latest NEMWEB archive matching source configuration.
    
    Returns: (archive_url, archive_bytes)
    Raises: RuntimeError if no matching archive found
    """
    listing_url = _validate_remote_url(source)
    allowed_host = urlparse(listing_url).hostname
    
    # Fetch HTML listing
    html = _request(listing_url, allowed_host=allowed_host).decode("latin-1")
    
    # Extract archive links matching regex
    pattern = re.compile(source.get("file_name_regex"), re.IGNORECASE)
    hrefs = re.findall(r'href=["\'']([^"\']+\.zip)', html, re.IGNORECASE)
    candidates = sorted({href for href in hrefs if pattern.search(href)})
    
    if not candidates:
        raise RuntimeError("NEMWEB_NO_MATCHING_ARCHIVE")
    
    # Use latest archive
    relative = candidates[-1]
    url = urljoin(listing_url, relative)
    
    # Validate URL
    parsed = urlparse(url)
    if parsed.hostname != allowed_host:
        raise ValueError("NEMWEB_ARCHIVE_HOST_NOT_ALLOWED")
    
    # Download archive
    archive_bytes = _request(url, allowed_host=allowed_host)
    return url, archive_bytes
```

### 3.2 Error Handling & Recovery

```python
class NemwebAcquisitionError(Exception):
    """Base exception for NEMWEB acquisition errors."""
    pass

class NemwebNetworkError(NemwebAcquisitionError):
    """Network-level errors (timeout, connection refused)."""
    pass

class NemwebValidationError(NemwebAcquisitionError):
    """Validation errors (host not allowed, URL mismatch)."""
    pass

class NemwebParseError(NemwebAcquisitionError):
    """Parse errors (malformed CSV, missing fields)."""
    pass

# Retry logic
def _acquire_with_retry(source: dict, max_retries: int = 3) -> tuple[str, bytes]:
    """Acquire archive with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return acquire_nemweb_archive(source)
        except NemwebNetworkError as exc:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning(f"Retry {attempt+1}/{max_retries} after {wait}s: {exc}")
            time.sleep(wait)
```

---

## Phase 4: Parser Implementation

### 4.1 CSV Parser Registry

```python
PARSER_REGISTRY = {
    "nemweb_csv": parse_nemweb_csv,
    "nemweb_json": parse_nemweb_json,
    # Future parsers
}

def _get_parser(source: dict):
    """Get parser function for source."""
    parser_type = source.get("parser_type", "nemweb_csv")
    if parser_type not in PARSER_REGISTRY:
        raise ValueError(f"Unknown parser type: {parser_type}")
    return PARSER_REGISTRY[parser_type]
```

### 4.2 NEMWEB CSV Parser

```python
def parse_nemweb_csv(archive_bytes: bytes, source: dict) -> list[dict]:
    """Parse NEMWEB ZIP archive containing CSV file.
    
    Returns list of row dicts with field mapping applied.
    """
    rows = []
    
    with ZipFile(BytesIO(archive_bytes)) as zf:
        # Expect single CSV file
        csv_files = [n for n in zf.namelist() if n.endswith('.csv')]
        if len(csv_files) != 1:
            raise NemwebParseError(f"Expected 1 CSV, found {len(csv_files)}")
        
        csv_name = csv_files[0]
        with zf.open(csv_name) as f:
            text = f.read().decode('utf-8')
        
        # Parse CSV
        csv_config = source.get("csv_config", {})
        reader = csv.DictReader(
            StringIO(text),
            delimiter=csv_config.get("delimiter", ",")
        )
        
        # Apply field mapping and type coercion
        field_mapping = source.get("field_mapping", {})
        field_types = source.get("field_types", {})
        
        for row_num, raw_row in enumerate(reader, 1):
            try:
                mapped = {}
                for raw_field, value in raw_row.items():
                    if raw_field in field_mapping:
                        mapped_field = field_mapping[raw_field]
                        mapped[mapped_field] = _coerce_type(
                            value,
                            field_types.get(mapped_field, "string")
                        )
                rows.append(mapped)
            except (ValueError, TypeError) as exc:
                raise NemwebParseError(f"Row {row_num}: {exc}")
    
    return rows

def _coerce_type(value: str | None, field_type: str) -> any:
    """Coerce string value to target type."""
    if value is None or value == "":
        return None
    
    if field_type == "string":
        return value
    elif field_type == "float":
        return float(value)
    elif field_type == "int":
        return int(value)
    elif field_type == "bool":
        return value.lower() in ("true", "1", "yes")
    else:
        return value
```

### 4.3 Field Mapping Examples

**DISPATCHIS:**
```json
{
  "field_mapping": {
    "REGION": "region",
    "INTERVAL_DATETIME": "interval_datetime",
    "TOTALDEMAND": "demand_mw",
    "RRP": "price_per_mwh"
  }
}
```

**PREDISPATCHIS:**
```json
{
  "field_mapping": {
    "REGION": "region",
    "INTERVAL_DATETIME": "interval_datetime",
    "TOTALDEMAND": "demand_mw",
    "RRP": "price_per_mwh"
  }
}
```

**ROOFTOP_PV:**
```json
{
  "field_mapping": {
    "REGION": "region",
    "INTERVAL_DATETIME": "interval_datetime",
    "TOTAL_ROOFTOP_PV": "generation_mw"
  }
}
```

---

## Phase 5: Quality Rules

### 5.1 Quality Check Definitions

Define in metadata for each source:

```json
{
  "quality_checks": [
    "demand_mw >= 0",
    "demand_mw <= 100000",
    "price_per_mwh is not null",
    "price_per_mwh >= -1000",
    "price_per_mwh <= 15000",
    "region is not null",
    "interval_datetime is not null"
  ]
}
```

### 5.2 Quality Check Mapping

Map quality check failures to reason codes:

```python
QUALITY_CHECK_REASON_MAP = {
    "demand_mw >= 0": "INVALID_DEMAND_NEGATIVE",
    "demand_mw <= 100000": "INVALID_DEMAND_EXCEEDS_MAX",
    "price_per_mwh is not null": "MISSING_PRICE",
    "price_per_mwh >= -1000": "INVALID_PRICE_BELOW_MIN",
    "price_per_mwh <= 15000": "INVALID_PRICE_EXCEEDS_MAX",
    "region is not null": "MISSING_REGION",
    "interval_datetime is not null": "MISSING_TIMESTAMP"
}
```

### 5.3 Business Rules

Additional checks beyond metadata:

```python
def _apply_business_rules(row: dict, source: dict) -> list[str]:
    """Apply source-specific business rules."""
    reasons = []
    
    if source["source_id"] == "aemo_dispatchis":
        # DISPATCHIS: demand should be reasonable for region
        region = row.get("region")
        demand = row.get("demand_mw")
        if region and demand:
            if region == "QLD1" and demand > 12000:
                reasons.append("DEMAND_EXCEEDS_REGIONAL_MAX")
    
    return reasons
```

---

## Phase 6: Integration Tests

### 6.1 Fixture Data Strategy

Create deterministic fixtures for each source:

```
agentic_energy/resources/fixtures/
├── nemweb_dispatchis.zip
├── nemweb_predispatchis.zip
├── nemweb_rooftop_pv.zip
└── nemweb_fixtures.json  # Metadata for fixture sources
```

**Fixture generation:**
```python
def _generate_nemweb_fixture(source_id: str, num_rows: int = 100) -> bytes:
    """Generate deterministic NEMWEB-shaped fixture."""
    rows = []
    regions = ["NSW1", "QLD1", "VIC1", "SA1", "TAS1"]
    
    base_time = datetime(2024, 4, 7, 0, 0, 0)
    for i in range(num_rows):
        row = {
            "REGION": regions[i % len(regions)],
            "INTERVAL_DATETIME": (base_time + timedelta(minutes=5*i)).isoformat(),
            "TOTALDEMAND": 5000 + (i * 100) % 3000,
            "RRP": 50 + (i * 10) % 200
        }
        rows.append(row)
    
    # Write to CSV in memory
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=["REGION", "INTERVAL_DATETIME", "TOTALDEMAND", "RRP"])
    writer.writeheader()
    writer.writerows(rows)
    
    # Zip it
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("PUBLIC_DISPATCHIS_20240407_0000.csv", csv_buffer.getvalue())
    
    return zip_buffer.getvalue()
```

### 6.2 Test Cases

```python
def test_nemweb_dispatchis_fixture_parsing():
    """Test DISPATCHIS fixture parsing."""
    source = load_metadata("aemo_dispatchis")
    archive = load_fixture("nemweb_dispatchis.zip")
    rows = parse_nemweb_csv(archive, source)
    
    assert len(rows) == 100
    assert all("region" in r for r in rows)
    assert all("interval_datetime" in r for r in rows)
    assert all("demand_mw" in r for r in rows)
    assert all("price_per_mwh" in r for r in rows)

def test_nemweb_quality_checks():
    """Test quality check application."""
    source = load_metadata("aemo_dispatchis")
    
    # Valid row
    valid = {"region": "NSW1", "demand_mw": 5000, "price_per_mwh": 100}
    assert _evaluate_quality_checks(valid, source) == []
    
    # Invalid rows
    invalid_demand = {"region": "NSW1", "demand_mw": -100, "price_per_mwh": 100}
    assert "INVALID_DEMAND" in _evaluate_quality_checks(invalid_demand, source)
    
    invalid_price = {"region": "NSW1", "demand_mw": 5000, "price_per_mwh": None}
    assert "MISSING_PRICE" in _evaluate_quality_checks(invalid_price, source)

def test_nemweb_deduplication():
    """Test deduplication by ingestion_sequence."""
    source = load_metadata("aemo_dispatchis")
    rows = [
        {"region": "NSW1", "interval_datetime": "2024-04-07T10:00", "demand_mw": 5000, "ingestion_sequence": 1},
        {"region": "NSW1", "interval_datetime": "2024-04-07T10:00", "demand_mw": 5100, "ingestion_sequence": 2},
    ]
    
    deduped = _deduplicate(rows, source)
    assert len(deduped) == 1
    assert deduped[0]["demand_mw"] == 5100  # Keep seq=2
```

---

## Phase 7: Live Mode Testing

### 7.1 Rate Limiting

```python
class RateLimiter:
    """Rate limiter for NEMWEB requests."""
    def __init__(self, max_requests_per_minute: int = 10):
        self.max_requests = max_requests_per_minute
        self.requests = deque()
    
    def wait_if_needed(self):
        now = time.time()
        # Remove requests older than 1 minute
        while self.requests and self.requests[0] < now - 60:
            self.requests.popleft()
        
        if len(self.requests) >= self.max_requests:
            wait_time = 60 - (now - self.requests[0])
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
        
        self.requests.append(now)

_rate_limiter = RateLimiter()

def acquire_nemweb_archive(source: dict) -> tuple[str, bytes]:
    _rate_limiter.wait_if_needed()
    # ... rest of acquisition logic
```

### 7.2 Monitoring & Observability

```python
def _log_acquisition(source_id: str, archive_url: str, archive_bytes: int, elapsed: float):
    """Log acquisition metrics."""
    logger.info(
        f"Acquired {source_id}",
        extra={
            "source_id": source_id,
            "archive_url": archive_url,
            "archive_size_bytes": archive_bytes,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat()
        }
    )
```

### 7.3 Integration Test

```python
@pytest.mark.integration
def test_nemweb_live_acquisition():
    """Test live NEMWEB acquisition (requires network)."""
    pytest.importorskip("live_nemweb")  # Skip if no network
    
    source = load_metadata("aemo_dispatchis")
    url, archive = acquire_nemweb_archive(source)
    
    assert url.startswith("https://nemweb.com.au")
    assert len(archive) > 0
    assert len(archive) < 50_000_000  # Max 50 MB
    
    # Verify archive structure
    with ZipFile(BytesIO(archive)) as zf:
        csv_files = [n for n in zf.namelist() if n.endswith('.csv')]
        assert len(csv_files) == 1
```

---

## Phase 8: Documentation

### 8.1 NEMWEB Contract Documentation

Create `docs/nemweb-contract.md`:

```markdown
# NEMWEB Data Contract

## Overview
NEMWEB is the National Electricity Market Web portal operated by AEMO. It provides
public access to market data including dispatch, predispatch, and renewable generation.

## Data Sources

### DISPATCHIS
- **URL:** https://nemweb.com.au/Reports/Current/DispatchIS_Reports/
- **Frequency:** 5-minute intervals
- **Latency:** 5–10 minutes
- **Retention:** 90 days
- **Key fields:** region, interval_datetime, demand_mw, price_per_mwh

### PREDISPATCHIS
- **URL:** https://nemweb.com.au/Reports/Current/PredispatchIS_Reports/
- **Frequency:** 30-minute intervals
- **Latency:** 30–60 minutes
- **Retention:** 90 days
- **Key fields:** region, interval_datetime, demand_mw, price_per_mwh

### ROOFTOP_PV
- **URL:** https://nemweb.com.au/Reports/Current/Rooftop_PV_Reports/
- **Frequency:** 30-minute intervals
- **Latency:** 30–60 minutes
- **Retention:** 90 days
- **Key fields:** region, interval_datetime, generation_mw

## Archive Format
- Format: ZIP containing single CSV file
- Naming: `PUBLIC_{ReportType}_{YYYYMMDD}_{HHMM}.zip`
- Encoding: UTF-8
- Delimiter: Comma

## Constraints
- HTTPS only, no redirects
- Max response: 50 MB
- Max archive member: 50 MB
- User-Agent required
- No authentication (public data)
- Rate limit: ~10 requests/minute recommended
```

### 8.2 Deployment Checklist

```markdown
## Deployment Checklist

- [ ] Metadata validated for all sources
- [ ] Fixtures created and committed
- [ ] All tests passing (unit + integration)
- [ ] Quality checks defined and tested
- [ ] Rate limiting configured
- [ ] Monitoring/logging in place
- [ ] Error handling documented
- [ ] Freshness SLA defined
- [ ] Quarantine policy tested
- [ ] Lineage tracking verified
```

---

## Implementation Roadmap

### Sprint 1: Foundation (Weeks 1–2)
- [ ] Metadata schema design and validation
- [ ] NEMWEB acquisition adapter (archive fetcher)
- [ ] CSV parser with field mapping
- [ ] Error handling and retry logic
- [ ] Unit tests for parser

### Sprint 2: Quality & Testing (Weeks 3–4)
- [ ] Quality check definitions
- [ ] Fixture generation and integration tests
- [ ] Deduplication and timezone normalization
- [ ] End-to-end fixture pipeline test

### Sprint 3: Live Mode (Weeks 5–6)
- [ ] Rate limiting implementation
- [ ] Live acquisition testing
- [ ] Monitoring and observability
- [ ] Documentation and deployment guide

### Sprint 4: Extension (Weeks 7–8)
- [ ] Support for additional NEMWEB sources (PREDISPATCHIS, ROOFTOP_PV)
- [ ] Performance optimization
- [ ] Operational runbook

---

## Success Criteria

✓ All NEMWEB sources configurable via metadata  
✓ Deterministic fixture mode for testing  
✓ Live acquisition with rate limiting and error recovery  
✓ Quality checks and quarantine tracking  
✓ 100% test coverage for parser and acquisition logic  
✓ Documentation complete and deployment-ready  
✓ Freshness SLA: <15 min latency for DISPATCHIS  
✓ No hardcoded source logic in pipeline.py  

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| NEMWEB API changes | Pipeline breaks | Version metadata, test with fixtures, monitor for changes |
| Network outages | Data gaps | Implement retry logic, alert on repeated failures |
| Large archives | Memory exhaustion | Stream CSV parsing, validate archive size before download |
| Ambiguous timestamps | DST issues | Use fold=0 canonical choice (already implemented) |
| Quality rule drift | Incorrect quarantine | Version quality_checks in metadata, test changes |

---

## References

- NEMWEB: https://nemweb.com.au
- AEMO: https://www.aemo.com.au
- agentic-energy framework: `docs/challenge-spec.md`
- Metadata contract: `agentic_energy/resources/metadata/sources.json`
