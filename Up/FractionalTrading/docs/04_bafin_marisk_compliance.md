# BaFin Regulatory Compliance — Upvest Wertpapierinstitut

> **Source verification note:** This document has been cross-checked against the primary sources in `docs/regulation/`:
> - IFR (EU) 2019/2033, consolidated text as of 09.01.2024
> - MaRisk Rundschreiben 06/2024 (BA), 29.05.2024
> - MaRisk Novelle — Konsultation 02/2026 (BA), draft
> Where earlier versions of this document cited secondary/third-party sources, those have been corrected against the primary texts.

---

## Applicable Framework

> **Important clarification on "MaRisk":**
> BaFin MaRisk **Rundschreiben 06/2024 (BA)** (the current version, dated 29.05.2024) is addressed *"an alle Kreditinstitute und Finanzdienstleistungsinstitute in der Bundesrepublik Deutschland"* — it directly applies to KWG-regulated institutions, **not** to small or medium WpIG Wertpapierinstitute.
>
> **Exception — Large Wertpapierfirmen:** MaRisk AT 2.1 para 2 explicitly states that **große Wertpapierfirmen (§ 2 Abs. 18 WpIG)** — those required by § 4 WpIG to apply §§ 25a and 25b KWG — must observe MaRisk (BA) to the extent required by the nature, scale, complexity and risk of their activities. If Upvest ever grows to the § 2 Abs. 18 WpIG threshold, MaRisk (BA) applies directly.
>
> For small/medium WpIG firms, the operative framework is:

| Rule Layer | Source | Status |
|---|---|---|
| Primary law — organisational requirements | WpIG §§ 38–46 | In force since 26.06.2021 |
| EU directly applicable — prudential | IFR (EU) 2019/2033 (consolidated 09.01.2024) | In force since 26.06.2021 |
| Governance guidance | BaFin Merkblatt 01/2024 (WA) — two-manager rule | In force since September 2024 |
| Risk management circular — WpIG firms | **WpI MaRisk** — BaFin Konsultation 15/2025 | Under consultation; MaRisk **06/2024 (BA)** applied **analogously** in interim |
| Bank MaRisk (reference / large firms) | MaRisk Rundschreiben **06/2024 (BA)** | Current; Novelle under consultation (Konsultation **02/2026**) |
| MaRisk Novelle — upcoming bank MaRisk update | Konsultation 02/2026 (BA) — Rundschreiben xx/2026 | Draft; date TBD — monitor for finalisation |
| Digital resilience | DORA — Regulation (EU) 2022/2554 | Applicable from 17.01.2025 |

> All compliance requirements below are grounded in WpIG + IFR as primary sources, with MaRisk 06/2024 (BA) applied analogously as best practice.

---

## License: Eigenhandel § 2 Abs. 2 Nr. 10c WpIG

### Statutory Definition

> *"Anschaffen oder Veräußern von Finanzinstrumenten für eigene Rechnung als Dienstleistung für andere"*
> Acquiring or disposing of financial instruments for **own account** as a **service for others**.

This is the direct transposition of **MiFID II Annex I, Section A, point 3** (dealing on own account) and **MiFID II Art. 4(1)(6)**, confirmed by IFR Art. 4(9) which defines 'dealing on own account' by cross-reference to MiFID II Art. 4(1)(6).

The firm acts as **principal** in every transaction — it takes on market risk with its own capital, not as agent for the client. The service character (Dienstleistungscharakter) distinguishes it from pure proprietary Eigengeschäft (which requires no BaFin licence): Upvest provides market access or execution to B2B counterparties who could not access the same terms independently.

See also: **BaFin Merkblatt March 2022** — "Hinweise zu den Tatbeständen des Eigenhandels und des Eigengeschäfts."

### The Four Sub-Types of Eigenhandel (§ 2 Abs. 2 Nr. 10a–10d WpIG)

| Sub-type | Definition | Upvest relevance |
|----------|-----------|-----------------|
| **10a** | Market-making — continuous bid/offer quotes on own capital | Not the primary model |
| **10b** | Systematic internalisation — frequent, organised, systematic dealing outside regulated markets | May apply as flow increases |
| **10c** | **General proprietary dealing as a service** — acquiring/disposing for own account as a service to others | **Upvest's licensed activity** |
| **10d** | High-frequency trading — algorithmic dealing with latency-minimising infrastructure | Not applicable |

---

## What Upvest MUST Do (Obligations)

### 1. Governance

**Vier-Augen-Prinzip / Two-Manager Rule**

- At least **two Geschäftsleiter (managing directors)** are required because Upvest holds custody (Depotgeschäft) and client money (§ 20, § 41 WpIG; BaFin Merkblatt 01/2024 (WA)).
- Managers must collectively possess the knowledge, skills, and experience necessary to understand all of the firm's activities — including Eigenhandel and fractional trading mechanics.
- Neither manager may simultaneously sit on the administrative or supervisory board of the same entity (§ 20 Abs. 1 WpIG).

**Supervisory Body / Beirat**

- Medium-sized institutions (§ 2 Abs. 17 WpIG) must establish (§ 44 WpIG):
  - **Risk Committee** — advises on overall risk strategy
  - **Vergütungskontrollausschuss** — reviews remuneration incentives for conflict-of-interest risks
- Waivable if total assets < €100m (or < €300m under specific conditions).
- **MaRisk Novelle (02/2026) watch:** the draft introduces an explicit **AT 3.2 — Verantwortung des Aufsichtsorgans und seiner Ausschüsse**, formalising supervisory body responsibilities that are currently implied. When finalised, expect this to be reflected in WpI MaRisk too.

---

### 2. Risk Strategy and Risk Management Framework

**(§§ 39, 43, 45 WpIG; WpI MaRisk Konsultation 15/2025; MaRisk 06/2024 (BA) analogously)**

- The management board must adopt and regularly review a documented **business strategy** and a consistent **risk strategy** derived from it (§ 45 Abs. 1 WpIG; MaRisk AT 4.2).
- Under MaRisk AT 2.2, at minimum the following risk types must be considered material: Adressenausfallrisiken, Marktpreisrisiken, Liquiditätsrisiken, operationelle Risiken.
- The risk strategy must address four IFR risk categories:
  1. **Risks to Customers (RtC)** — conduct, product, execution quality
  2. **Risks to the Market (RtM)** — market price risk, liquidity, orderly functioning of markets
  3. **Risks to the Firm (RtF)** — own capital adequacy, operational, counterparty, concentration
  4. **Liquidity risk** — ability to meet obligations as they fall due
- For fractional trading specifically, the risk strategy must explicitly cover:
  - Residual position management (market risk from unsettled fractional aggregation)
  - Reconciliation controls (fractional ledger vs. custody positions)
  - FX exposure policy (non-EUR instruments)
  - Instrument eligibility criteria

**ICARA Process (§ 39 WpIG / IFD Art. 24)**

The investment firm equivalent of ICAAP + ILAAP is the **ICARA (Internal Capital Adequacy and Risk Assessment)**:
- Continuous self-assessment of all material risks and whether capital and liquidity are adequate to cover them (§ 39 WpIG transposes IFD Art. 24)
- Stress testing scenarios including proprietary position shocks and liquidity stress (MaRisk AT 4.3.3)
- Business model sustainability assessment
- **Wind-down plan**: sufficient capital and liquid assets must be reserved to allow an orderly exit from the business (§ 45 Abs. 4 WpIG)
- Results feed into BaFin's **SREP** (§ 47 WpIG / IFD Art. 36), which may impose Pillar 2 capital add-ons

---

### 3. Internal Control Functions (Three Lines of Defence)

**(MaRisk AT 4.4 analogously; § 41 WpIG)**

| Function | Requirement | Notes |
|----------|------------|-------|
| **Risk Controlling** | Independent function; escalation procedures documented (MaRisk AT 4.4.1) | Mandatory for all Wertpapierinstitute |
| **Compliance** | Independent from business lines; BaFin MaComp (Rundschreiben 05/2018 (WA)) applies for conduct/WpHG obligations (MaRisk AT 4.4.2) | May be combined with other control units in small firms only if conflicts of interest are excluded |
| **Internal Audit (Interne Revision)** | Full functional separation for medium-sized firms; may be outsourced by small firms (MaRisk AT 4.4.3 / BT 2) | Firms ≤ 10 employees may be fully exempt |

**MaRisk Novelle (02/2026) — Key changes to internal controls:**
- AT 4.3.4 shifts from "Datenmanagement, Datenqualität und Aggregation von Risikodaten" to **"Verwendung von Modellen"** (model risk) — relevant for Upvest's K-NPR calculation models and aggregation pricing logic
- AT 4.3.3 (Stresstests) significantly expanded
- AT 9 Auslagerung (outsourcing) substantially expanded — monitor for impact on Upvest's execution venue and custody arrangements

---

### 4. Capital Requirements Under IFR (EU) 2019/2033

**Upvest is NOT a small and non-interconnected investment firm** under IFR Art. 12(1). A firm qualifies as small/non-interconnected only if ALL conditions in Art. 12(1) are met, including (f) NPR or CMG = zero and (c) ASA = zero. Since Upvest does Eigenhandel (NPR ≠ 0) and holds custody under its Depotgeschäft licence (ASA ≠ 0), it does **not** qualify. All three pillars of Art. 11(1) apply.

Own funds must equal the **highest** of (IFR Art. 11):

| Pillar | Calculation | Source |
|--------|------------|--------|
| **Fixed Overhead Requirement (FOR)** | 1/4 of prior year fixed overheads (net of variable items) | IFR Art. 13 |
| **Permanent minimum capital** | Levels specified in **IFD Art. 9** — **€750,000** for firms dealing on own account | IFR Art. 14 |
| **K-factor Requirement** | Sum of RtC + RtM + RtF K-factors | IFR Art. 15 |

**K-factors applicable to Upvest (Eigenhandel + Depotgeschäft):**

| K-factor | IFR Article | Coefficient | Trigger | Notes for Upvest |
|----------|------------|------------|---------|-----------------|
| **K-NPR** | Art. 22 | CRR standardised approach | All proprietary trading book positions | **Primary market risk charge**; applies to residual fractional positions and intraday inventory; three calculation approaches: standardised (CRR Chs. 2–4 Title IV), alternative standardised, or alternative internal model |
| **K-CMG** | Art. 23 | 1.3 × 3rd-highest daily margin over prior 3 months | Alternative to K-NPR, positions cleared via clearing member at a QCCP | **Requires explicit BaFin assessment and permission** (Art. 23(1)); firm must NOT be part of a group containing a credit institution; trading must essentially be clearing-based; most likely K-NPR is the applicable approach for equity fractional trading |
| **K-ASA** | Art. 19 | 0.04% | Assets safeguarded and administered for clients (Depotgeschäft) | **Applicable** — Upvest holds Depotgeschäft licence; ASA ≠ 0; rolling 9-month average of daily values, excluding 3 most recent months |
| **K-TCD** | Art. 25–26 | Formula: α (1.2) × Exposure × Risk Factor | OTC derivative contracts (Annex II CRR), repos, SFTs, long settlement transactions | Applies if Upvest hedges via OTC derivatives or enters repos; likely low/zero for pure cash equity Eigenhandel |
| **K-DTF** | Art. 33 | 0.1% (cash) / 0.01% (derivatives) | Total daily notional trading flow (own account + client executions in own name) | Directly triggered by Eigenhandel volume; rolling average per Art. 33 |
| **K-CON** | Art. 35–39 | Progressive add-on on excess | Single client/group of connected clients exposure in trading book exceeding Art. 37(1) limits (25% of own funds) | Applies to execution counterparties (brokers, venues) in the trading book; not to underlying security issuers |

**K-factors NOT applicable** (RtC factors requiring AUM or brokerage activities):

| K-factor | Reason not applicable |
|---------|----------------------|
| K-AUM | Only for portfolio managers managing client assets discretionarily |
| K-CMH | Only if Upvest holds client cash money — verify with Finance/Ops whether any client cash passes through Upvest's own accounts |
| K-COH | Only for reception/transmission and execution of client orders in agent capacity — Eigenhandel means Upvest always acts as principal |

> **Action required:** Confirm with Finance whether Upvest ever holds client cash money (CMH). If yes, K-CMH applies at 0.4% (segregated accounts) or 0.5% (non-segregated accounts) per IFR Art. 15(2) Table 1.

**Own funds composition (IFR Art. 9):**
- CET1 ≥ 56% of D
- CET1 + AT1 ≥ 75% of D
- CET1 + AT1 + T2 ≥ 100% of D
(where D = the Art. 11 own funds requirement)

---

### 5. Outsourcing — § 40 WpIG

- Implement proportionate safeguards for all **material outsourcing** (wesentliche Auslagerungen), defined by reference to EU Delegated Regulation 2017/565 Art. 30(1).
- Maintain an **Auslagerungsregister** (outsourcing register) covering all material and non-material arrangements.
- **Notify BaFin** of material outsourcing via WpI-AnzV (Wertpapierinstituts-Anzeigenverordnung).
- Third-country providers must contractually designate a domestic representative (§ 40 Abs. 2 WpIG).
- BaFin retains the right to issue orders directly to outsourcing partners (§ 40 Abs. 3 WpIG).
- **No empty-shell structures**: core risk management, compliance, and internal audit functions cannot be fully outsourced — Upvest must retain substantive oversight.
- **MaRisk Novelle watch:** AT 9 Auslagerung in the 02/2026 draft is substantially expanded (pp. 63+ vs. pp. 26+ in 06/2024) — likely covers cloud outsourcing, sub-outsourcing chains, and exit strategy requirements in more detail.

---

### 6. DORA — Digital Operational Resilience (from 17.01.2025)

- **ICT risk management framework**: documented policies, procedures, and tools
- **Incident reporting**: material ICT-related incidents must be reported to BaFin within defined timeframes
- **Digital operational resilience testing**: advanced firms must conduct **TLPT (Threat-Led Penetration Testing)**
- **ICT third-party risk**: mandatory contractual provisions and a register of all critical ICT providers
- **Exit strategies** for dependency on a single critical ICT provider (relevant for cloud infrastructure, execution venues, custody platforms)

---

### 7. Conduct / MiFID II Obligations Specific to Eigenhandel

- **Best execution (§ 82 WpHG / MiFID II Art. 27)**: Even as a principal, Upvest must maintain and apply an **order execution policy** covering price, cost, speed, likelihood of execution/settlement, size, and nature of orders. The policy must be reviewed annually and whenever a material change affects execution quality.
- **Conflicts of interest**: Principal dealer acting as counterparty to B2B clients — conflicts policy must explicitly address the principal/agent dynamic.
- **Transaction reporting (§ 26 WpHG / MiFID II Art. 26)**: All trades in financial instruments admitted to trading on a regulated venue must be reported to BaFin via an ARM. For fractional trading, each whole-share execution is the reportable event.
- **MiFID II product governance (WpHG §§ 80 ff.)**: As manufacturer/distributor of fractional trading services for B2B clients, target market obligations apply.

---

## What Upvest CANNOT Do (Restrictions)

### With ONLY Eigenhandel (§ 2 Abs. 2 Nr. 10c WpIG)

A WpIG licence is activity-specific. These activities require **separate, explicitly licensed authorisation**:

| Activity | Legal basis | Notes |
|----------|------------|-------|
| **Custody / Depotgeschäft** | § 2 Abs. 3 Nr. 1 WpIG | Safekeeping and administration of client financial instruments. Upvest holds this separately — must be operated with full functional separation from Eigenhandel book |
| **Portfolio management** | § 2 Abs. 2 Nr. 9 WpIG | Discretionary management of individual client portfolios — entirely separate licence |
| **Acting as agent/broker** | § 2 Abs. 2 Nr. 1 WpIG (Finanzkommissionsgeschäft) | Buying/selling in own name for client account. Eigenhandel = always principal. Cannot execute as pure agent |
| **Investment advice** | § 2 Abs. 2 Nr. 4 WpIG | Personalised investment recommendations — separate licence |
| **Accepting deposits** | KWG § 32 | **Strictly prohibited** for any WpIG firm. § 15 Abs. 5 WpIG: WpIG and KWG licences cannot be combined |
| **Underwriting / Emissionsgeschäft** | § 2 Abs. 2 Nr. 2 WpIG | Firm commitment or best-efforts placement — separate licence |
| **Operating a trading venue (MTF/OTF)** | § 2 Abs. 2 Nr. 6–7 WpIG | Running a multilateral or organised trading facility — separate licence |
| **Payment services / e-money** | ZAG / EMD2 | Cannot combine WpIG with ZAG/EMD2 payment institution registration |
| **Fund management (AIFM/UCITS)** | KAGB | Cannot combine WpIG with KAGB fund management licence |

### Structural Constraints Specific to Fractional Trading

| Constraint | Detail |
|-----------|--------|
| **No acting as settlement agent** | Upvest cannot settle trades on behalf of third parties — must go through licensed CSDs or custodians |
| **No credit extension to clients** | Cannot provide margin lending or extend credit without a KWG banking licence |
| **No client money pooling beyond custody** | Fractional buy orders must not pool client cash in a way that constitutes deposit-taking; pre-funding or T+1 debit model required |
| **No direct CSD membership without clearing licence** | Access to settlement infrastructure requires a clearing/settlement arrangement via a licensed intermediary |
| **Residual positions require K-NPR capital at all times** | Cannot hold proprietary positions without adequate own funds; no grace period under IFR |
| **K-CON limit on execution counterparties** | Single execution counterparty (broker/venue) trading book exposure must stay below 25% of own funds; excess triggers capital surcharge (IFR Art. 39) and BaFin notification (IFR Art. 38) |

---

## Fractional Trading Specific Compliance Requirements

### Fractional Shares = Real Co-ownership (Bruchteilseigentum)

Under German law, fractional shares are treated as genuine fractional co-ownership interests in the underlying whole share — not as derivative instruments. Key implications:
- **DepotG (Depotgesetz)** applies to fractional positions identically to whole shares → K-ASA applies
- Corporate actions (dividends, splits, mergers) must be attributed pro-rata to fractional holders
- Transaction reporting under § 26 WpHG covers the whole-share execution, not individual fractional allocations
- No derivative classification → no additional EMIR obligations on the fractional positions themselves

### Aggregation Model: Compliance Checklist

| Requirement | Regulatory basis | Implementation |
|-------------|-----------------|----------------|
| Execution policy covering aggregated orders | § 82 WpHG / MiFID II Art. 27 | Best execution policy must address aggregation window, batch sizing, and price determination |
| K-NPR capital against all open positions | IFR Art. 22 | Intraday position monitoring; capital model updated each batch |
| K-ASA calculated monthly | IFR Art. 19 | Rolling 9-month average of daily values (ex 3 most recent months) |
| K-DTF calculated monthly | IFR Art. 33 | Rolling average of daily trading flow |
| Reconciliation fractional ledger vs. custody | § 45 WpIG; WpI MaRisk | Daily automated reconciliation; break escalation within 24h |
| Corporate action attribution | DepotG | Automated CA processing with fraction-aware calculation |
| Transaction reporting per whole-share execution | § 26 WpHG / MiFID II Art. 26 | ARM reporting of executed whole-share trades |
| K-CON monitoring vs. execution counterparties | IFR Art. 35–39 | Monitor trading book exposure per counterparty vs. own funds; notify BaFin if limit approached |
| Wind-down plan includes fractional position unwind | § 45 Abs. 4 WpIG | Model time-to-unwind under stress; include in ICARA |

---

## Open Compliance Actions

- [ ] **Confirm full licence set** — verify Depotgeschäft and any other WpIG licences with Legal
- [ ] **Confirm K-CMH applicability** — does Upvest ever hold client cash money? If yes, K-CMH applies
- [ ] **BaFin engagement** — proactive discussion on fractional share aggregation model and Eigenhandel characterisation
- [ ] **ICARA update** — include fractional residual position scenarios in stress testing and wind-down planning
- [ ] **Best execution policy** — update to explicitly cover aggregated fractional order batches
- [ ] **Capital model** — confirm K-NPR methodology (standardised vs. alternative standardised approach from CRR)
- [ ] **K-ASA calculation** — set up rolling 9-month data capture for daily custody assets
- [ ] **K-DTF calculation** — set up rolling daily trading flow measurement
- [ ] **DORA gap assessment** — map ICT providers in fractional trading engine; update third-party risk register
- [ ] **WpI MaRisk monitoring** — track finalisation of Konsultation 15/2025; assess compliance gap
- [ ] **MaRisk Novelle monitoring** — track Konsultation 02/2026 (BA); assess impact on model risk (AT 4.3.4) and outsourcing (AT 9) requirements
- [ ] **§ 2 Abs. 18 WpIG threshold monitoring** — track whether Upvest approaches the large Wertpapierfirma threshold (if so, MaRisk 06/2024 (BA) applies directly)
- [ ] **Outsourcing register** — ensure execution venue and custody arrangements are classified correctly and notified to BaFin

---

## Key Legal References

| Topic | Reference |
|-------|-----------|
| Eigenhandel — definition | § 2 Abs. 2 Nr. 10a–10d WpIG |
| MiFID II equivalence | MiFID II Annex I Section A pt. 3; Art. 4(1)(6) MiFID II; IFR Art. 4(9) |
| Eigenhandel vs. Eigengeschäft | BaFin Merkblatt March 2022 |
| Licence requirement | § 15 Abs. 1 WpIG |
| Custody (Depotgeschäft) | § 2 Abs. 3 Nr. 1 WpIG |
| No banking licence combination | § 15 Abs. 5 WpIG |
| Two-manager rule | § 20, § 41 WpIG; BaFin Merkblatt 01/2024 (WA) |
| Risk committees | § 44 WpIG |
| ICARA / risk-bearing capacity | § 39 WpIG; IFD Art. 24 |
| Risk strategy | §§ 43, 45 WpIG |
| Internal controls | § 41 WpIG; MaRisk AT 4.4 (analogously) |
| Outsourcing | § 40 WpIG; EU Delegated Regulation 2017/565 Art. 30 |
| SREP | § 47 WpIG; IFD Art. 36 |
| Own funds requirements | IFR Art. 11 (highest of Art. 13 FOR, Art. 14 minimum, Art. 15 K-factor) |
| K-factor framework | IFR Art. 15 Table 1; RtC: Art. 16–20; RtM: Art. 21–23; RtF: Art. 24–39 |
| Minimum capital — Eigenhandel | **IFD Art. 9 / IFR Art. 14**: €750,000 |
| Small/non-interconnected criteria | IFR Art. 12(1) — Upvest does NOT qualify (NPR ≠ 0, ASA ≠ 0) |
| K-NPR | IFR Art. 22 (three CRR approaches) |
| K-CMG | IFR Art. 23 (BaFin assessment required; group with credit institution excluded) |
| K-ASA | IFR Art. 19; coefficient 0.04% |
| K-TCD scope | IFR Art. 25 (Annex II CRR derivatives, repos, SFTs) |
| K-DTF | IFR Art. 33; coefficients: 0.1% cash / 0.01% derivatives |
| K-CON | IFR Art. 35–39; 25% own funds limit (Art. 37(1)) |
| Wind-down planning | § 45 Abs. 4 WpIG |
| Best execution | § 82 WpHG; MiFID II Art. 27 |
| Transaction reporting | § 26 WpHG; MiFID II Art. 26 |
| DORA | Regulation (EU) 2022/2554 |
| MaRisk — current bank version | **Rundschreiben 06/2024 (BA)**, 29.05.2024 |
| MaRisk — large WpIG firms | MaRisk AT 2.1 para 2 (große Wertpapierfirmen per § 2 Abs. 18 WpIG via § 4 WpIG) |
| MaRisk Novelle — upcoming | Konsultation 02/2026 (BA) — Rundschreiben xx/2026, draft |
| WpI MaRisk — WpIG firms | BaFin Konsultation 15/2025 (August 2025) |
| Fractional shares — legal classification | BaFin practice; DepotG; no derivative classification confirmed |

---

*Last updated: 2026-05-30. Cross-checked against IFR (EU) 2019/2033 (consolidated 09.01.2024) and MaRisk Rundschreiben 06/2024 (BA). Review again when WpI MaRisk (Konsultation 15/2025) and MaRisk Novelle (Konsultation 02/2026) are finalised.*
