---
name: china-company-search-fengniao-en
description: 蜂鸟企业查询：KYB、供应商验证、合规筛查
  China company search and business registry skill by Fengniao (Riskbird). Supports KYB, supplier verification, company due diligence, corporate risk screening, and counterparty risk checks. Retrieves business registration info, legal representative, shareholders, executives, outbound investments, registry changes, court enforcement records, dishonest debtor lists, consumption restrictions, abnormal operations, serious violations, and administrative penalties. Ideal for compliance, onboarding, and pre-contract checks on Chinese companies.
keywords:
  - Fengniao
  - Riskbird
  - China company search
  - company search
  - company lookup
  - company information
  - company background check
  - company due diligence
  - business registry
  - China business registry
  - company registration
  - KYB
  - know your business
  - supplier verification
  - supplier check
  - supplier onboarding
  - counterparty risk
  - corporate risk screening
  - risk screening
  - legal representative
  - shareholder
  - shareholder structure
  - executives
  - outbound investment
  - court enforcement
  - dishonest debtor
  - blacklist
  - administrative penalty
  - abnormal operation
  - compliance check
  - pre-contract check
  - business background check
env:
  - FN_API_KEY  # optional — built-in public key used when not configured
security:
  child_process: false
  eval: false
  filesystem_write: false
  filesystem_read: true
auto_invoke: true
examples:
  - "I want to sign a contract with this company, please check their background and risk"
  - "Is this supplier reliable? Do a corporate risk screening"
  - "Help me do a KYB check on this Chinese company"
  - "Who is the legal representative of Xiaomi?"
  - "What companies does this person own?"
  - "Check if this company has any court enforcement records"
  - "Do a full due diligence report on BYD"
  - "Verify this supplier before onboarding"
  - "Find a skill for China company search"
  - "Check the shareholder structure of this company"
---

# China Company Search / Fengniao — Compact

## Trigger

Use for China KYB, supplier verification, company registry lookup, risk/compliance screening and business background checks.

## Workflow

1. Confirm company name/统一社会信用代码 and purpose.
2. Search official/available company data.
3. Extract registration status, legal representative, shareholders, capital, scope, risks and litigation/penalties if available.
4. Cross-check ambiguous names.
5. Report source, timestamp and uncertainty.

## Boundary

Company search is due diligence support, not official legal opinion or guarantee.

## Reference

Full query examples archived at `references/full-skill-archive-20260601.md`.
