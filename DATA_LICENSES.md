# AEMO / NEMWEB data attribution

## Source and permitted use

This project retrieves public National Electricity Market reports from the
Australian Energy Market Operator (AEMO) NEMWEB portal:

- <https://www.nemweb.com.au/REPORTS/CURRENT/>
- <https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions>
- <https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/market-management-system-data>

NEMWEB data is **© Australian Energy Market Operator Limited (AEMO)**. AEMO is
the source and must be attributed wherever its data is displayed or
redistributed. Use is subject to AEMO's current copyright permissions and any
conditions attached to the relevant Market Management System publication. The
linked AEMO terms, rather than this summary, are authoritative. These links and
the permissions summary were reviewed on 11 August 2026.

Do not label NEMWEB material as Creative Commons unless AEMO applies that
licence to the specific material. This repository's software licence does not
license AEMO data.

## Disclaimer

AEMO material and the derived workshop analysis are provided on an “as is”
basis. Verify operational, trading, investment or commercial decisions against
official AEMO publications. This project is not an AEMO product, and AEMO does
not endorse its transformations, metrics, Genie responses or dashboards.

## Report families in scope

| Report family | Sections used | Source cadence represented |
|---|---|---|
| `DispatchIS_Reports` | `PRICE`, `REGIONSUM`, `CONSTRAINT`, `INTERCONNECTORRES` | Current, approximately five-minute publication |
| `Dispatch_SCADA` | `UNIT_SCADA` | Current, approximately five-minute publication |
| `Next_Day_Dispatch` | `UNIT_SOLUTION` | Daily T+1 authoritative dispatch/availability context |
| Participant registration | DUID, generating-unit, station, region and interconnector dimensions after contract validation | Source-appropriate slower context |
| Bids, trading/settlement and market notices | Only sections whose contracts are proven and recorded in the migration manifest | Source-appropriate slower context |

A five-minute orchestration schedule does not imply that AEMO has published a
new source row. Evidence must report source publication lag independently from
landing-to-Gold processing lag. `UNIT_SCADA` measures actual unit output; it is
not a five-minute dispatch target or availability report.

## Checked-in snapshot requirements

Any checked-in AEMO sample must have an adjacent versioned manifest recording:

- exact public source URL and retrieval date;
- original archive/member names, report family, section and version;
- SHA-256 checksum;
- whether the sample is unmodified or a clearly labelled synthetic mutation;
- the AEMO attribution above; and
- the reason the minimum necessary rows are retained.

Synthetic malformed, duplicate, correction or schema-drift cases must never be
presented as live AEMO evidence. No snapshot data has been added in the bundle
foundation slice; the snapshot slice must satisfy these requirements before
adding any sample.
