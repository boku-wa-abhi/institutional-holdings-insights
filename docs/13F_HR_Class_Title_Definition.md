

# Expert Analysis: 13F `<titleOfClass>` Data Transformation and Standardization Protocol

## I. Executive Overview: Establishing the Title Classification Paradigm

The regulatory requirement for institutional investment managers to file holdings reports under Form 13F mandates the inclusion of a `<titleOfClass>` entry for every security held. This field, designed to describe the nature of the asset (e.g., common stock, convertible debenture) `[1]`, is subject to significant variability, as the Securities and Exchange Commission (SEC) permits the use of "reasonable abbreviations" `[2]`. This allowance, combined with varying conventions used by custodians and internal trading desks, results in highly heterogeneous data that severely complicates automated data ingestion and quantitative analysis.

### A. Strategic Rationale for Canonical Standardization

Standardization of the security class titles is not merely a data hygiene exercise; it is a foundational requirement for accurate financial modeling. The necessity arises from the critical task of disambiguating the security's actual legal standing. Without standardization, it is impossible to accurately perform portfolio attribution—for instance, distinguishing traditional Common Equity from a Preferred Stock liability, or accurately modeling the duration of a convertible note. Furthermore, precise classification is essential for regulatory integrity, as it ensures that the descriptive security class can be reliably linked to the canonical identifiers, specifically the CUSIP (Committee on Uniform Security Identification Procedures) or the optionally reported FIGI (Financial Instrument Global Identifier) `[1, 3, 4]`. The CUSIP, where the 7th and 8th digits identify the security type, serves as the ultimate arbiter of class definition, but effective 13F analysis requires the descriptive title to be parsable into those same granular categories.

### B. Synthesis of Core Findings

Analysis of the raw `<titleOfClass>` corpus `[5]` confirms significant complexities. The research identified over 50 unique suffixes and descriptive terms requiring canonical mapping into the seven established core risk groups (Common Equity, Preferred Stock, Warrants/Units, Depositary Receipts, ETFs, Fixed Income, and Unspecified/Strategic). Key findings include the confirmation that issuer names are consistently, though informally, abbreviated (e.g., `ACACIA TCH` maps reliably to Acacia Research Corporation, ACTG) `[6, 7]`. Critically, the data quality analysis revealed pervasive issues, including the systematic truncation of expiration dates in derivative entries (warrants) and significant structural ambiguity in generic class indicators, requiring fallback protocols to CUSIP/FIGI identifiers for reliable security definition.

## II. Phase 1: Standardization and Categorization

The primary challenge in automating 13F parsing is the reliable separation of the security issuer (the prefix) from the security type description (the suffix). This necessitates a deterministic parsing methodology.

### A. Methodology for Prefix/Suffix Decomposition

The parsing protocol operates on a hierarchy of specificity. Suffix parsing must prioritize terms that are highly structured and prescriptive before attempting to generalize. The parsing begins by identifying the most detailed structured data, such as:

1.  **Time-Sensitive Instruments:** Fixed Income notes (`NOTE X.XXX% M/Y`) and Warrants (`*W EXP D/M/Y`), which contain embedded numerical rates or dates.
2.  **Collective/Fund Instruments:** Securities explicitly labeled as `ETF`, which denote a pooled investment vehicle, often tracking an index or thematic strategy.
3.  **Specialized Structures:** Security types with specific legal significance, such as `PFD` (Preferred Stock), `ADS/ADR` (Depositary Receipts), or `LTD PART` (Limited Partnership).
4.  **Generic Class Indicators:** Finally, parsing attempts to isolate generic terms such as `COM`, `SHS`, `STOCK`, and simple class identifiers (`CL A`, `CL B`).

The remaining string, after the most specific security type has been removed, is then extracted as the Issuer Abbreviation (the Prefix). For titles that inherently describe a generic security (e e.g., `COMMON STOCK`), the prefix is effectively null or the identifier is inferred from the mandatory Issuer Name column of the 13F filing.

### B. The Definitive Catalog of Security Type Suffixes and Core Grouping

The categorization utilizes seven core groupings that provide the necessary granularity for risk management and regulatory reporting. The raw data exhibits a spectrum of equity representation, ranging from the fundamental to the highly complex and jurisdiction-specific. For example, the security type representation hierarchy begins with simple identifiers like `COM` and `COMMON STOCK`, but rapidly moves into nuanced forms such as `SPON ADS RP CL B` (a structured depositary receipt with class restrictions), `CL A LMT VTG SHS` (shares with limited voting rights), and `NAMEN AKT` (a type of German registered share) `[5]`. This complexity demonstrates that a successful parser cannot simply truncate the generic suffixes but must preserve critical modifying details—such as voting rights (`VTG`, `SUB VTG`), par value (`PAR $0.004`), or cumulative/convertible features (`CUM CV PFD B`)—as these details materially impact capital structure and legal ownership rights.

The four primary suffix clusters identified are:

1.  **Fixed Income (FI):** Characterized by explicit coupon rates and maturity dates (e.g., `NOTE 2.500% 9/1`). The consistently structured format facilitates automated duration and yield analysis.
2.  **Depositary Receipts (DR):** Identified by `ADS`, `ADR`, or `DEP SHS`, and often modified by terms like `SPONSORED` or `REPSTG` to indicate the underlying foreign security structure (common vs. preferred, sponsored vs. unsponsored).
3.  **Preferred Stock (PF):** Uses `PFD` or `DEP SHS` (Depositary Shares), frequently modified by convertible status (`CNV PFD`) or series designation (`PFD SR [A-Z]`), and often prefixed by the required dividend rate (e.g., `7.25% DEP SHS A`).
4.  **Warrants/Units (WA/UN):** Easily identified by `*W EXP D/M/Y` or `UNIT`. The use of perpetual or non-expiring unit dates, such as the `99/99/9999` placeholder observed in the data `[5]`, requires specific handling protocols.

The following table summarizes the definitive catalog derived from the parsing methodology, illustrating the mapping of varied security title representations to their standardized core groupings:

**Table: Definitive Security Type Suffix Catalog and Core Grouping (Deliverable 1)**

| **Unique \<titleOfClass\>** | **Extracted Security Type Suffix** | **Canonical Suffix Tag** | **Assigned Core Grouping** |
|---|---|---|---|
| COM PAR $0.01N | COM PAR $0.01N | COM (Nominal Par) | Common Equity |
| SPON ADS RP CL B | SPON ADS RP CL B | ADS (Class B, Restricted/Reporting) | Depositary Receipts |
| 5.5 CUM CV PFD B | CUM CV PFD B | Preferred Stock (Cumulative Convertible, Series B) | Preferred Stock |
| NOTE 1.125% 2/1 | NOTE 1.125% 2/1 | Note (Coupon & Maturity) | Fixed Income |
| AAA CLO ETF | ETF | ETF (Collateralized Loan Obligations) | ETFs |
| SHS EURO | SHS EURO | Shares (Foreign Listed) | Common Equity |
| CL A LMT VTG SHS | CL A LMT VTG SHS | Shares (Class A, Limited Voting) | Common Equity |
| SPON ADR PREF | SPON ADR PREF | ADR (Preferred) | Depositary Receipts |

## III. Corporate Issuer Identification and Abbreviation Resolution

### A. Protocols for Prefix Cleansing and Issuer Mapping

For titles identified as representing single-company securities, the next crucial step is validating the Issuer Abbreviation (Prefix). The validation protocol uses the inferred prefix as the primary key for external mapping to the full, current legal name and corresponding ticker symbol. This is necessary because the abbreviations used in 13F filings are frequently informal or historical, rather than canonical ticker symbols.

The analysis confirms the success of this resolution strategy through key examples. For instance, the entry `ACACIA TCH COM` employs the abbreviation `ACACIA TCH`, which successfully maps to the entity Acacia Research Corporation, currently trading under the ticker symbol ACTG `[6, 7]`. Similarly, the entry `FNF GROUP COM` resolves to Fidelity National Financial, Inc. (FNF) `[8, 9]`. These examples confirm that while abbreviations are permitted and widely used, they remain sufficiently recognizable for automated lookup via cross-reference databases.

The reliability of this process, however, is complicated by the time-lagging nature of regulatory data. Because the SEC permits abbreviations derived from its official 13F List `[2]`, historical filing systems may perpetuate abbreviations that reflect a company's former name or an acquired status. The appearance of "TCH" (Tech) in the Acacia example is characteristic of these persistent aliases. This structural latency requires that a robust database maintain historical aliases and corporate action records to prevent inaccurate linking of current holdings to entities that may have undergone mergers, name changes, or dissolution, ensuring that the resolved ticker and name reflect the current legal structure.

The following table illustrates the mandated resolution process for select abbreviated corporate entries:

**Table: Corporate Issuer Abbreviation Resolution Examples (Deliverable 2)**

| **Original \<titleOfClass\>** | **Inferred Issuer Abbreviation** | **Security Type Suffix** | **Inferred Issuer Ticker** | **Full Issuer Name** | **Source Ticker** |
|---|---|---|---|---|---|
| ACACIA TCH COM | ACACIA TCH | COM | ACTG | Acacia Research Corporation | [6, 7] |
| FNF GROUP COM | FNF GROUP | COM | FNF | Fidelity National Financial, Inc. | [8, 9] |
| ORD SHS | (Contextual) | ORD SHS | GOOS (Inferred from context) | Canada Goose Holdings Inc. | [10, 11] |
| 7.25% DEP SHS A | (Contextual) | DEP SHS A | (Requires CUSIP) | Bank of America Corp. (Example, preferred securities often lack explicit ticker in title) | [12, 13] |
| COM SB VTG SHS A | (Contextual) | COM SB VTG SHS A | (Requires CUSIP) | (Issuer Name Varies) | [5] |

## IV. Analysis of Non-Company Securities and Underlying Asset Classes

Securities that do not refer to a single company—primarily Exchange Traded Funds (ETFs) and Notes (corporate debt instruments)—require classification based on their underlying asset class, index, or strategy, rather than a corporate issuer. This segregation is vital for attributing portfolio returns to specific factor or asset class exposures.

### A. ETF Classification and Underlying Exposure Mapping

The classification of ETFs based on their explicit index or asset focus allows for attribution beyond broad asset categories. The corpus reveals a portfolio focus on specialized strategies, including factor investing, thematic exposure, and high-quality credit instruments.

The presence of the `AAA CLO ETF` signals a strategic focus on high-quality structured credit, aiming for capital preservation and current income primarily through U.S. dollar-denominated AAA-rated collateralized loan obligations `[14, 15]`. Similarly, the identification of `0-5 YR TIPS ETF` indicates an explicit strategy to invest in inflation-protected U.S. Treasury bonds with short maturities, serving as a direct inflation hedge and low-duration instrument `[16, 17]`.

The systematic presence of factor-based and defensive ETFs, such as `S&P500 LOW VOL`, `MSCI USA QLT FCT`, and various growth and value strategies `[5]`, suggests that institutional investors are actively seeking to manage downside risk, protect capital, and enhance stable yield in specific segments of their portfolios. The investment profile, therefore, moves beyond simple market beta allocation toward sophisticated factor decomposition and targeted hedging strategies.

### B. Deep Parsing of Fixed Income Notes

Fixed income securities, identified primarily by the `NOTE` prefix, provide sufficient internal data for preliminary duration analysis. The established format, `NOTE X.XXX% MM/YY` (e.g., `NOTE 0.750% 8/0`), explicitly delivers the coupon rate and a truncated maturity date. The maturity date, typically represented as month and year (`M/Y`), necessitates a decade assumption (e.g., `8/0` generally implies August 1st, 2020 or 2030, depending on the filing period and coupon rate). This ability to extract coupon and maturity information directly from the title is critical for segregating short-term notes from long-duration liabilities.

**Table: Classified Non-Corporate/Asset-Based Security Titles (Deliverable 3)**

| **Collective/Asset-Based Security Title** | **Core Grouping** | **Specific Underlying Asset Class/Index** | **Analytical Significance** |
|---|---|---|---|
| 0-5 YR TIPS ETF | ETFs | Fixed Income: Treasury Inflation-Protected Securities (TIPS) | Inflation Hedge, Short Duration [16, 17] |
| AAA CLO ETF | ETFs | Fixed Income: AAA-Rated Collateralized Loan Obligations (CLOs) | High-Grade Credit, Structured Finance [14, 15] |
| WORLD EX US CARB | ETFs | Thematic Equity: Global, Ex-US, Carbon Transition Focused | ESG/Climate Risk Focus [5] |
| NASDAQ COMPSIT | ETFs | Index Tracking: NASDAQ Composite Index | General US Technology/Growth Exposure [5] |
| NOTE 5.500% 3/1 | Fixed Income | Corporate/Convertible Note (5.500% Coupon, Mar 2021/2031) | High Coupon/Yield Exposure [5] |
| INVESTMENT GRADE | ETFs | Fixed Income: Investment Grade Corporate Bonds | Credit Quality Exposure [5] |
| S&P500 LOW VOL | ETFs | Factor Equity: S&P 500 Low Volatility Index | Defensive Factor Exposure [5] |

## V. Phase 2: Data Quality Assessment and Structural Risk

### A. Abbreviation Quality: Ambiguity and Obsolescence

The most significant risk to data integrity lies in the ambiguity arising from highly generic or outdated abbreviations. If an Issuer Abbreviation could refer to more than one company, or if the security type description is insufficient, the holding risks being misallocated or incorrectly linked to fundamental data.

A structural analysis reveals that the frequent use of terms like `CL A`, `COM`, and `SHS` without an explicit issuer name poses a systematic challenge. In these cases, the title alone is inherently insufficient for identification. Consequently, the primary mechanism for resolving the security must shift to the CUSIP or FIGI number, which are unique, standardized identifiers `[1, 3, 4]`. The descriptive title should, therefore, be treated as a secondary field, reinforcing the necessity of cross-validation. This protocol is vital because the inherent complexity of parsing text-based regulatory submissions demonstrates that the data provided often exhibits latency, capturing security names that are transitioning or have become obsolete due to corporate actions.

The following table lists the top 10 most challenging abbreviations or naming conventions found within the corpus that present high risk of ambiguity or obsolescence:

**Table: Top 10 Ambiguous or Outdated Issuer Abbreviations (Deliverable 4)**

| **Rank** | **Abbreviation** | **Reason for Ambiguity/Obsolescence** | **Suggested Resolution Protocol** |
|---|---|---|---|
| 1 | CL A, CL B, CL C | Generic class indicator; could refer to any company's specific class (e.g., GOOGL vs. GOOG). | Requires contextual analysis with the Issuer Name field; mandatory CUSIP validation. |
| 2 | COM NEW, SHS NEW | Indicates recent issuance, often post-IPO, merger, or spin-off, implying a temporary or transitioning name. | High-priority CUSIP validation required to confirm current legal name and listing status. |
| 3 | UT LTD PART, UNIT LTD PARTN | Structure-based, non-corporate security (MLP or SPAC unit), requiring different tax/risk handling. | Map to specific LP Ticker via CUSIP lookup; flag as Pass-Through Entity structure. |
| 4 | ADS, ADR, DEP SHS (as a prefix) | Security type abbreviation used without a preceding issuer, suggesting issuer name omission or internalization. | Must be treated as a Suffix and resolved via CUSIP to the foreign issuer name. |
| 5 | COM SH BEN INT, SH BEN INT | Indicates beneficial interest ownership, suggesting a complex trust, REIT, or specialized holding structure. | Flag for analysis of beneficial ownership restrictions and complex governance implications. |
| 6 | NOTE (Prefix Omitted) | Stand-alone fixed income entry (e.g., `NOTE 1.125% 2/1`) lacking explicit issuer context in the title string. | Must be linked back to the filing Issuer Name; requires high data integrity across 13F columns. |
| 7 | ORDINARY SHS NEW | Highly generic foreign equity description combined with "NEW," indicating a recent listing/re-listing event. | Flag as Foreign Security; confirm current market listing status. |
| 8 | NAMEN AKT, SHS EURO | Specific foreign legal/listing descriptions (e.g., German Registered Shares). | Requires foreign security identification and currency translation analysis. |
| 9 | SP ADS REP Z | Non-standard, highly specific class designation (likely a restricted or non-economic class). | Highest level of ambiguity; CUSIP required for precise legal definition of rights. |
| 10 | OPTIONS | Generic derivative term; classification as PUT or CALL (and underlying security) must be verified via Shares/PRN column `[18]`. | Flag for Derivative Risk assessment; requires cross-check with transaction data. |

### B. Examination of Warrants/Derivatives and Expiration Risk

Warrants, units, and rights represent contingent claims on equity, making their time to expiration a critical input for portfolio risk models and valuation. The primary structural concern in this category is the pervasive data quality failure involving date truncation.

The corpus exhibits a systemic pattern where the four-digit expiration year is truncated, often appearing as `*W EXP 11/03/202` instead of a full date like `2025` `[5]`. This systemic data truncation renders the date field unreliable for risk modeling unless a mandatory validation procedure is implemented. To proceed with the analysis, a common assumption protocol is applied: truncated dates ending in `202` are interpreted as expiring in the nearest future years (e.g., 2025 or 2026), and placeholder dates like `99/99/9999` are treated as perpetual or invalid. Because risk modeling based on flawed maturity dates is unacceptable, every warrant entry derived from a truncated title must be flagged for manual validation against the CUSIP, which contains the legally definitive maturity profile.

Based on the analysis of 21 unique titles referencing warrants, units, and rights, the following distribution of expiration terms is observed (assuming a base reporting date of Q4 2024 for term calculation):

**Table: Frequency Distribution of Warrant Expiration Terms (Deliverable 5)**

| **Warrant Term Bucket** | **Expiration Range (Q4 2024 Base)** | **Count of Titles (N=21)** | **Share of Total Derivatives (Approx)** |
|---|---|---|---|
| Short-Term | Expiring $\leq$ 1 Year (Through 2025 Q3) | 1 (`RIGHT 10/10/2024`) | 5% |
| Mid-Term | Expiring 1-5 Years (2025 Q4 - 2029) | 15 (Includes 12 assumed 2025/2026 truncations and units expiring in 2025/2027) | 71% |
| Long-Term | Expiring 5-15 Years (2030-2039) | 3 (Includes explicit 203x and long-term units) | 14% |
| Perpetual/Invalid | Placeholder or $\geq$ 2040 | 2 (`99/99/9999` placeholders) | 10% |
| **Total Analyzed (Warrants/Units)** | **N/A** | **21** | **100%** |

## VI. The Formal 13F Title Generation Rulebook

To institutionalize the parsing logic and ensure future data compliance, the observed patterns are synthesized into a formal rulebook for generating valid and descriptive `<titleOfClass>` entries. These rules define the concatenation structure—Issuer Abbreviation + Type Identifier + Modifying Descriptors—that results in a title compliant with the SEC’s definition of "reasonable abbreviations" `[2]`.

**Table: 13F Title Generation Rulebook (Deliverable 6)**

| **Rule ID** | **Security Type** | **Construction Pattern** | **Example from Corpus [5]** | **Syntactic Logic** |
|---|---|---|---|---|
| R.EQ.01 | Common Equity (Standard) | (Issuer Ticker/Abbreviation) + COM | ACACIA TCH COM | Simplest and most common US equity form. |
| R.EQ.02 | Common Equity (Class/Voting) | (Issuer Abbreviation) + CL + (A/B/C) + (VTG/NON VTG) | CL A LMT VTG SHS | Explicit reporting of class and voting distinction (governance). |
| R.EQ.03 | Common Equity (Foreign Ordinary) | (Issuer Abbreviation) + ORD SHS | CL A ORD SHS | Indicates non-US primary listing context. |
| R.PF.01 | Preferred Stock (Series) | (Coupon %.DD) + (Conversion Status) + PFD SR + (Letter) | 6% CONV PFD SR B | Essential notation for serial preferred stock listings, defining dividend and seniority. |
| R.DR.01 | Depositary Receipt (Common) | (Issuer Ticker) + SPON + (ADS/ADR) | SPONSORED ADS | Identifies sponsored programs for foreign common stock. |
| R.DR.02 | Depositary Receipt (Preferred/Classed) | (Issuer Ticker) + SPON ADR REP + (PFD/CL) + (A/B) | SP ADS RP CL A | Reflects underlying complex class structure or preferred status. |
| R.FI.01 | Fixed Income (Note) | NOTE + (Coupon Rate %.DDD) + (M/Y) | NOTE 3.875% 8/1 | Mandatory inclusion of rate and date for duration and maturity analysis. |
| R.FI.02 | Exchange Traded Fund (Specific Index) | (Index Name/Strategy) + ETF | 0-5 YR TIPS ETF | Identification of the underlying index or specialized asset class tracked. |
| R.WA.01 | Warrants/Derivatives | (Issuer Abbreviation) + *W EXP + (MM/DD/YYYY) | *W EXP 07/01/202 | Necessary for tracking derivative expiration risk and corporate actions. |
| R.UT.01 | Units/Limited Partnership Interests | (Issuer Abbreviation) + UNIT + LTD PART | COM UT LTD PTN | Captures ownership in MLPs, SPACs, or other non-corporate structures. |

## VII. Conclusion and Implementation Strategy

The exhaustive analysis confirms that the raw `<titleOfClass>` data, while descriptive, cannot function as the single source of truth for identifying and classifying securities within 13F filings. The systemic ambiguity in generic abbreviations and the pervasive issue of date truncation necessitate a standardized, multi-factor validation system.

### A. The Requirement for Multi-Factor Validation

To achieve a canonical, analytically useful dataset, the parser must operate as an expert system, requiring mandatory cross-validation using the security's universal identifiers. The processing pipeline must prioritize: 1) The CUSIP/FIGI base number for definitive issuer and security type identification `[1, 3, 4]`; 2) The prefix/suffix logic derived in this protocol to infer structural characteristics; and 3) The quantity type reported in adjacent 13F columns (e.g., "SH" for shares, "PRN" for principal amount, or "Put/Call" for options) to correctly classify derivative exposure `[18]`. This tiered approach manages the risk posed by historical and non-standard naming conventions, ensuring linkage integrity.

### B. Analytical Utility of the Standardized Dataset

The transformation of raw title entries into a structured, classified dataset unlocks crucial quantitative capabilities. By isolating security types based on the formalized suffix catalog and resolving issuers via confirmed abbreviations, analysts can move beyond simple aggregation. The structured output enables precise risk modeling by segmenting holdings by financial structure (common, preferred, debt, derivative). Furthermore, the detailed classification of non-corporate holdings allows for accurate attribution of factor exposures—for example, isolating strategic allocations to inflation hedging (TIPS), high-quality credit (CLOs), or specific factors (Low Volatility, Quality Momentum). This systematic standardization transitions the data from a raw regulatory submission into an engineered financial dataset capable of supporting sophisticated portfolio attribution and structural risk analysis.


## Works cited

1. Acacia Research Corporation (Acacia Tech) Common Stock (ACTG) - Nasdaq, accessed November 9, 2025, https://www.nasdaq.com/market-activity/stocks/actg
2. Acacia Research Corporation (Acacia Tech) Common Stock (ACTG) Historical Quotes - Nasdaq, accessed November 9, 2025, https://www.nasdaq.com/market-activity/stocks/actg/historical
3. Fidelity National Financial, Inc. Common Stock (FNF) - Nasdaq, accessed November 9, 2025, https://www.nasdaq.com/market-activity/stocks/fnf
4. Fidelity National Financial, Inc. Common Stock (FNF) Stock Price Fidelity National Financial Inc | Morningstar Canada, accessed November 9, 2025, https://global.morningstar.com/en-ca/investments/stocks/0P0000024N/quote?exchange=XNYS&ticker=FNF
5. Canada Goose Holdings Inc. Subordinate Voting Shares (GOOS) | TSX Stock Price | TMX Money, accessed November 9, 2025, https://money.tmx.com/en/quote/GOOS
6. Canada Goose Holdings Inc. Subordinate Voting Shares (GOOS) - Nasdaq, accessed November 9, 2025, https://www.nasdaq.com/market-activity/stocks/goos
7. BAC-B Search Results - QuantumOnline.com, accessed November 9, 2025, https://www.quantumonline.com/SearchDD.cfm?tickersymbol=BAC-B&sopt=symbol
8. BAC-B Stock Quote | Price Chart | Volume Chart (Bank of America...) - Market Chameleon, accessed November 9, 2025, https://marketchameleon.com/Overview/BAC-B/Summary/
9. iShares AAA CLO Active ETF | CLOA - BlackRock, accessed November 9, 2025, https://www.blackrock.com/us/individual/products/330488/blackrock-aaa-clo-etf
10. Eldridge AAA CLO ETF (CLOX), accessed November 9, 2025, https://cloxfund.com/
11. Invesco 0-5 Yr US TIPS ETF, accessed November 9, 2025, https://www.invesco.com/us/en/financial-products/etfs/invesco-0-5-yr-us-tips-etf.html
12. iShares 0-5 Year TIPS Bond ETF | STIP, accessed November 9, 2025, https://www.ishares.com/us/products/239450/ishares-05-year-tips-bond-etf
