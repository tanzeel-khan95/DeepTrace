# Evaluation Personas

Ground-truth personas used for CLI (`--eval`), Streamlit eval dashboard, and LangSmith evals. Each persona defines expected facts, risk flags, and scoring targets.

---

## Table of Contents

- [Satya Nadella](#satya-nadella)
- [Elizabeth Holmes](#elizabeth-holmes)
- [Sam Bankman-Fried](#sam-bankman-fried)
- [Timothy Overturf](#timothy-overturf)

---

## Satya Nadella

| Field | Value |
|-------|--------|
| **Name** | Satya Nadella |
| **Context** | Chairman and CEO of Microsoft |
| **Risk level** | LOW |
| **Expected risk score** | 5 |
| **Expected flag count** | 0 |

### Due diligence

| Key | Value |
|-----|--------|
| Name | Satya Nadella |
| Nationality | American |
| Birth year | 1967 |
| Role | Chairman and CEO of Microsoft |
| Industry | Technology / Cloud Computing |
| Education | B.E. Electrical Engineering – Manipal Institute of Technology; M.S. Computer Science – University of Wisconsin–Milwaukee; MBA – University of Chicago Booth School of Business |
| Notable positions | CEO of Microsoft (2014–present); Executive Vice President, Microsoft Cloud and Enterprise Group |
| Awards | Financial Times Person of the Year 2019; TIME 100 Most Influential People |

### Risk flags ground truth

- **Risk flags:** None
- **Negative media:** None significant related to fraud, sanctions, or regulatory violations identified in major sources as of 2024.
- **Litigation:** None personally
- **Sanctions:** No
- **PEP:** No

### Expected facts

- Chairman and CEO of Microsoft
- American technology executive born in 1967
- Holds engineering, computer science, and MBA degrees
- CEO of Microsoft since 2014

### Expected risk levels

- *(none)*

---

## Elizabeth Holmes

| Field | Value |
|-------|--------|
| **Name** | Elizabeth Holmes |
| **Context** | Founder and former CEO of Theranos |
| **Risk level** | MEDIUM |
| **Expected risk score** | 55 |
| **Expected flag count** | 3 |

### Due diligence

| Key | Value |
|-----|--------|
| Name | Elizabeth Holmes |
| Nationality | American |
| Birth year | 1984 |
| Role | Founder and former CEO of Theranos |
| Industry | Biotechnology |
| Education | Stanford University (Chemical Engineering – did not complete) |
| Company | Theranos |
| Founded year | 2003 |
| Business activity | Blood-testing technology startup |

### Risk flags ground truth

- **Risk flags:** Fraud charges related to misleading investors; SEC civil charges in 2018; Criminal conviction in 2022 for investor fraud
- **Litigation:** SEC vs Elizabeth Holmes (2018); United States v. Holmes (2021 trial)
- **Regulatory action:** Theranos banned from operating labs by CMS (2016)
- **Sanctions:** No
- **PEP:** No

### Expected facts

- Founded Theranos in 2003
- American entrepreneur in biotechnology
- Attended Stanford University but did not complete degree
- Subject of SEC civil charges in 2018
- Criminal conviction in 2022 for investor fraud

### Expected risk levels

- CRITICAL, CRITICAL, HIGH

---

## Sam Bankman-Fried

| Field | Value |
|-------|--------|
| **Name** | Sam Bankman-Fried |
| **Context** | Founder and former CEO of FTX cryptocurrency exchange |
| **Risk level** | HIGH |
| **Expected risk score** | 70 |
| **Expected flag count** | 4 |

### Due diligence

| Key | Value |
|-----|--------|
| Name | Sam Bankman-Fried |
| Nationality | American |
| Birth year | 1992 |
| Role | Founder and former CEO of FTX cryptocurrency exchange |
| Industry | Cryptocurrency / Financial trading |
| Education | MIT – Physics |
| Companies | FTX; Alameda Research |

### Risk flags ground truth

- **Risk flags:** Convicted of fraud and conspiracy related to FTX collapse; Misappropriation of customer funds; Securities and wire fraud charges; Major financial misconduct affecting billions of dollars
- **Regulatory actions:** SEC charges (2022); CFTC charges; U.S. Department of Justice criminal indictment
- **Financial impact:** FTX collapse caused billions in customer losses
- **Sanctions:** No
- **PEP:** No

### Expected facts

- Founded FTX cryptocurrency exchange
- Founded or led Alameda Research
- American entrepreneur born in 1992 with MIT Physics background
- Convicted of fraud and conspiracy related to FTX collapse
- Misappropriation of customer funds and securities/wire fraud charges

### Expected risk levels

- CRITICAL, CRITICAL, CRITICAL, HIGH

---

## Timothy Overturf

| Field | Value |
|-------|--------|
| **Name** | Timothy Silas Prugh Overturf |
| **Context** | CEO of Sisu Capital, LLC, an SEC-registered investment adviser |
| **Risk level** | HIGH |
| **Expected risk score** | 70 |
| **Expected flag count** | 2 |

### Due diligence

| Key | Value |
|-----|--------|
| Name | Timothy Silas Prugh Overturf |
| Role | CEO of Sisu Capital, LLC |
| Industry | Investment advisory |
| Firm | Sisu Capital, LLC |
| Firm status | SEC-registered investment adviser |
| Key relationship | Authorized his father, Hansueli Overturf, to provide investment advice to firm clients |
| Regulatory concerns | Hansueli Overturf provided advice despite two California suspensions: Nov 2011–Nov 2014 and Dec 2017–Dec 2019; At least one suspension period overlapped with active client advisory activity |
| Fee activity | Sisu Capital withdrew over $2 million in portfolio management fees, performance-based fees, and commissions from client accounts (2017–2021) |
| Conflict of interest | Undisclosed family relationship between CEO and advisory personnel; potential conflicts regarding fee allocation and investment recommendations |

### Risk flags ground truth

- **Risk flags:** Suspended Investment Adviser Providing Client Advice (Hansueli Overturf advised Sisu clients despite California suspensions 2011–2014 and 2017–2019); Undisclosed Family Conflict of Interest in Investment Management (CEO–father relationship; fee and recommendation oversight concerns)
- **Regulatory action:** California suspension of Hansueli Overturf (Nov 2011–Nov 2014); California suspension of Hansueli Overturf (Dec 2017–Dec 2019)
- **Litigation:** SEC and related enforcement attention regarding Sisu Capital, Timothy Overturf, and Hansueli Overturf
- **Sanctions:** No
- **PEP:** No

### Expected facts

- Timothy Overturf is CEO of Sisu Capital, LLC
- Sisu Capital, LLC is an SEC-registered investment adviser
- Hansueli Overturf (father) provided investment advice to Sisu clients with Timothy Overturf's authorization
- Hansueli Overturf was suspended by California (Nov 2011–Nov 2014 and Dec 2017–Dec 2019) from acting as an investment adviser
- Sisu Capital withdrew over $2 million in fees from client accounts during 2017–2021
- Undisclosed family relationship between CEO and advisory personnel created conflict of interest concerns

### Expected risk levels

- CRITICAL, MEDIUM

---

## Summary

| Persona | Risk level | Expected score | Expected flags | Eval focus |
|---------|------------|----------------|----------------|------------|
| Satya Nadella | LOW | 5 | 0 | Baseline extraction; low false-positive risk |
| Elizabeth Holmes | MEDIUM | 55 | 3 | Risk flag precision; contradictory sources |
| Sam Bankman-Fried | HIGH | 70 | 4 | Entity graph depth; complex financial network |
| Timothy Overturf | HIGH | 70 | 2 | Sparse footprint; regulatory/family conflict |
