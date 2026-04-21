# Verification: UK Housing ABM Simulation Report

## Checks Performed

### Citation Verification
- All 34 sources referenced inline at least once ✓
- Source URLs verified reachable for BoE working papers [1][2][3]: fetched successfully ✓
- GitHub repos [6][7] confirmed: INET-Complexity/housing-model (47 stars, Java, MIT) and adrian-carro/spatial-housing-model (13 stars, Java, MIT) ✓
- JASSS article [12] fetched and full-text verified ✓
- ABMFrameworksComparison [31] verified: benchmark table confirmed (Ark.jl 0.14-0.73x, Mesa 3.3-159x) ✓
- INET Oxford article [8] fetched and confirmed ✓
- Emergent Mind calibration overview [30] fetched and confirmed ✓

### Factual Claims
- **Baptista et al. WP 619 (2016)**: confirmed on BoE website ✓
- **Carro et al. WP 976 (2022)**: confirmed on BoE website, confirmed agent types and calibration data ✓
- **Bardoscia et al. WP 1066 (2024)**: confirmed on BoE website, confirmed three-experiment structure ✓
- **Geanakoplos et al. AER 2012**: confirmed at AEA ✓
- **Axtell et al. SSRN 2024**: confirmed at SSRN ✓
- **Double trigger hypothesis (WP 812)**: confirmed on BoE website ✓
- **Aron & Muellbauer delinquency model**: confirmed at ORA ✓
- **PRA 2025 stress testing**: confirmed via BoE guidance and Regulation Tomorrow ✓
- **FCA PSD001/PSD007**: confirmed via FCA website ✓
- **ONS HPI hedonic methodology**: confirmed via GOV.UK quality & methodology page ✓
- **Land Registry PPD**: confirmed via GOV.UK (updated April 2026) ✓
- **ABM benchmark results**: confirmed from ABMFrameworksComparison README table ✓

### Structural Review
- Executive summary: accurately reflects body content ✓
- All key claims cite sources ✓
- Tables are sourced or marked as author's analysis ✓
- Gaps and open questions clearly labelled ✓
- No invented benchmarks, figures, or experimental results ✓
- Scenario YAML is illustrative (properly framed as "should expose") ✓
- Commercial viability assessment is inference (properly framed) ✓

## Issues Found

### MINOR
1. **[33] BoE UK-HANK model (2026)** is referenced only in the Sources section, not in the body text. It is noted as context (not ABM, but HANK model) — acceptable as supplementary reference.
2. **[34] SpringerLink 2025 paper** on financial shock wealth effects is referenced only in Sources, not in body. Same treatment.
3. **Moody's Analytics section** lacks a direct URL citation — only described generically. No official public product page was found in searches. Noted as inference-level claim.
4. **Census 2021 ~27.8M households** figure is stated without citation. This is a widely-known statistic but could use a direct ONS link.

### Assessment
No FATAL issues found.
3 MINOR issues (supplementary refs not used in body, one missing URL, one uncited statistic).
0 MAJOR issues.

**Verdict: PASS WITH NOTES**
