# NovaDrive CRO Dashboard

### Supplier Network Intelligence • Risk Prioritisation • Event Monitoring • Alternate Supplier Discovery

## Overview

The NovaDrive CRO Dashboard is a decision-support platform developed for Project Lighthouse | Consularium. It brings together supplier network visibility, risk prioritisation, event monitoring and alternate supplier discovery to help the CRO identify and respond to material supply-chain vulnerabilities.

## Part 1 — Supplier Network Reconstruction

The supplier network was reconstructed using the case workbook's **Relationship Evidence**, rather than assuming that every organisation in the Supplier Universe is an active NovaDrive supplier.

The final confirmed network contains:

- **23 confirmed supplier entities**
- **8 Tier 1 suppliers**
- **10 Tier 2 suppliers**
- **5 Tier 3 suppliers**
- **31 confirmed supplier relationships**

The analysis captures supplier-to-supplier relationships, relevant components, facilities and supporting evidence. Confirmed relationships are kept separate from reasonable inferences and unresolved hypotheses.

**Key principle:** The Supplier Universe is a candidate list, not a verified supplier master. Relationships are accepted based on the available relationship evidence, with uncertainty explicitly preserved.

## Part 2 — Supplier Risk Assessment

The supplier risk scorecard prioritises the **23 confirmed suppliers** using an explainable composite risk score.

| Risk Dimension | Weight |
|---|---:|
| Network Exposure | 30% |
| Financial Risk | 25% |
| Operational Risk | 25% |
| Geographic Risk | 20% |

Risk categories are:

- **Critical:** ≥ 70
- **High:** 55–69.99
- **Medium:** 45–54.99
- **Low:** < 45

The dashboard allows users to rank suppliers, inspect component risk scores and compare suppliers across tiers. Evidence confidence is reported separately from supplier risk.

**Key principle:** Missing information is not automatically treated as low risk, and evidence confidence is not conflated with the supplier's actual risk level.

## Part 3 — Event Risk Intelligence

External event signals are matched against the confirmed supplier network to determine whether they represent a meaningful NovaDrive exposure.

The process includes:

- Supplier, facility and geography matching
- Entity validation
- Duplicate and source-family checks
- Historical/stale event filtering
- Network impact analysis
- Management alert generation
- Recommended next actions

The dashboard also supports analysis of new events entered in natural language and can highlight the affected supplier and downstream network.

**Key principle:** An event is not treated as a supplier risk until the correct entity, facility or geography has been validated. Duplicate, stale and unrelated signals are filtered out.

## Part 4 — Alternate Supplier Discovery

When a material supplier or upstream node is flagged, the platform identifies potential alternate suppliers using current public sources.

The search and initial assessment consider:

- Affected component
- Application context
- Technical capability
- Application relevance
- Manufacturing footprint
- Scale and industry presence
- Public-source evidence
- Qualification requirements

Supplier risk is kept separate from alternate-supplier fitment.

**Key principle:** Alternatives are shortlisted based on the affected component and application rather than generic industry similarity. Shortlisted candidates still require commercial, technical and engineering validation before qualification.

## Data & Files

### `event_alerts.csv`
Contains the processed event-risk outputs used for management alerts. It records the `Event ID`, `Title`, `Affected Supplier`, `Severity`, `Risk Level`, `Evidence Confidence`, `Geography`, `Facility`, `Why It Matters`, `Network Context` and `Next Action`. Multiple rows may represent different supplier impacts from the same event.

### `novadrive_supplier_risk_scorecard.csv`
Contains the Part 2 supplier risk assessment for confirmed suppliers. It includes `Entity ID`, `Legal Name`, `Tier`, `Composite_Risk_Score`, `Risk_Category`, `Financial_Risk_Score`, `Operational_Risk_Score`, `Geo_Risk_Score`, `Network_Exposure_Score` and `Evidence_Confidence (%)`.

### `supplier_entities.csv`
Contains the confirmed supplier reference table with `Entity`, `Tier` and `Match Key`. It supports supplier identification, tier mapping and event matching.

### `supplier_network.csv`
Contains the confirmed supplier relationships used to construct the network. Columns include `Evidence ID`, `From`, `To`, `Evidence Role`, `NovaDrive Component`, `Program`, `Supplied Input`, `Facility` and `From Tier`.

### `consularium.ipynb`
The Google Colab notebook contains the complete analytical workflow behind the dashboard. It covers supplier network reconstruction and tiering, uncertainty analysis, supplier risk scoring, event matching and validation, network impact analysis, management alert generation, and alternate supplier discovery. It serves as the analytical record from which the dashboard outputs are generated.

## How to Run

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit application:

```bash
streamlit run app.py
```
