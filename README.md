# NovaDrive CRO Dashboard

### Supplier Network Intelligence • Risk Prioritisation • Event Monitoring • Alternate Supplier Discovery

## Overview

The NovaDrive CRO Dashboard is a decision-support platform designed to provide visibility into NovaDrive Technologies' multi-tier supplier network and help management identify, prioritise and respond to supply-chain risks.

The dashboard integrates supplier network reconstruction, supplier risk assessment, external event monitoring and alternate supplier discovery into a single interactive platform.

## Key Capabilities

### 1. Supplier Network Reconstruction

The dashboard reconstructs the confirmed NovaDrive supplier network across Tier 1, Tier 2 and Tier 3 suppliers.

Key capabilities include:

- Interactive multi-tier supplier network visualisation
- Supplier-to-supplier relationship mapping
- Component and facility-level relationship context
- Downstream dependency analysis
- Separation of confirmed relationships from uncertain relationships
- Evidence-backed network reconstruction

### 2. Supplier Risk Assessment

Suppliers are prioritised using an explainable composite risk score.

The risk framework combines:

| Risk Dimension | Weight |
|---|---:|
| Network Exposure | 30% |
| Financial Risk | 25% |
| Operational Risk | 25% |
| Geographic Risk | 20% |

Risk categories are defined as:

- **Critical:** ≥ 70
- **High:** 55–69.99
- **Medium:** 45–54.99
- **Low:** < 45

Evidence confidence is reported separately from supplier risk so that uncertainty in available information is not automatically treated as low risk.

### 3. Event Risk Intelligence

The platform converts external risk signals into actionable management alerts.

The event intelligence workflow:

```text
External Event
      ↓
Entity / Facility / Geography Matching
      ↓
Validation & Relevance Assessment
      ↓
Duplicate / Stale Event Filtering
      ↓
Network Impact Analysis
      ↓
Management Alert
      ↓
Recommended Management Action
