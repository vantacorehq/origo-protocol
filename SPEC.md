# Origo Protocol — Specification (draft v0.1)

> Blockchain stores **trust**, not **data**. Origo is a federation of signed event logs with one shared format and one shared anchoring system.

## 1. Layers

| Layer | Purpose | Lives in |
|-------|---------|----------|
| L0 Physical binding | Ties a digital ID to a physical object | Packaging, lot, material itself |
| L1 Identity | Participant DIDs, accreditations (VCs), product identifiers | Public DID registry + participant-held credentials |
| L2 Events | Signed events forming a provenance DAG | Participant storage, mirrors, content-addressed networks |
| L3 Anchoring | Merkle roots + timestamps | Public L1/L2 via regional aggregators |
| L4 Verification | Rules and proofs | Client (phone, ERP, customs system) |
| L5 Applications | Human and machine interfaces | Open ecosystem |

**Roles:** Actor (mine, factory, carrier, store) · Auditor (accredited actor issuing `Attestation`) · Aggregator (publishes super-roots) · Verifier (anyone) · Resolver (returns the event graph for an identifier; many can exist).

## 2. Identifiers

| Object | Format | Basis |
|--------|--------|-------|
| Participant | `did:origo:<hash>` | W3C DID |
| Raw material lot | `lot:<gln>:<id>` | GS1 LGTIN/GLN |
| Trade item | `sgtin:<gtin>.<serial>` | GS1 SGTIN, GS1 Digital Link on the pack |
| Container / pallet | `sscc:<…>` | GS1 SSCC |

Origo does not replace GS1/EPCIS — it adds cryptographic verifiability to them.

## 3. Event model

Schema: [`event.schema.json`](event.schema.json). Event types: `Extraction`, `Transformation` (N inputs → M outputs), `Transfer`, `Aggregation`, `Disaggregation`, `Attestation`, `Recall`.

- **ID** = `ev:` + SHA-256 of the RFC 8785 (JCS) canonical event body.
- **Signature** = Ed25519 over the bytes of `id`, using a key from the actor's DID document.
- **Provenance** = every input lot must be the output of another event → a DAG.
- **Granularity:** lots for raw/intermediate materials, serialized units (SGTIN) for consumer goods; the lot→unit step is a `Transformation` preserving mass balance.

### Invariants (checked by every verifier)

1. **Integrity:** `id == "ev:" + sha256(JCS(body))`.
2. **Authorship:** signature valid for the key that was active at `time`.
3. **Mass balance:** `Σ outputs ≤ Σ inputs × max_yield(process)` (values from the open process registry).
4. **No double spend:** total consumption of a lot ≤ total of its outputs.
5. **Causality:** an event is not earlier than any of its sources; its anchor is not earlier than the event.
6. **Authority:** events requiring accreditation carry a valid VC from a recognized issuer.

Invariants 3–4 are the main defense against laundering: certified material cannot be "multiplied" without breaking the balance.

## 4. Privacy

| Mode | What a verifier sees |
|------|----------------------|
| `public` | the full event |
| `committed` | event hash + ZK proofs of claims |
| `permissioned` | full event, only for key holders (regulator, auditor) |

Example ZK claim: "this lot contains ≥ 20 % recycled content" without revealing suppliers or volumes. Consumers scan without accounts and verify locally.

## 5. Cryptography and anchoring

| Task | Choice |
|------|--------|
| Hash | SHA-256 |
| Signatures | Ed25519; post-quantum fallback ML-DSA (FIPS 204) |
| Canonicalization | RFC 8785 JCS |
| Identity | W3C DID + Verifiable Credentials |
| Tree | Merkle with domain separation (`0x00‖leaf`, `0x01‖l‖r`) |
| Claims | Groth16 / PLONK-family; STARKs for post-quantum |

**Anchoring flow:** actors batch events every *T* minutes → publish a root to a regional aggregator → the aggregator builds a tree over actor roots and publishes a super-root on a public chain → actors receive an inclusion chain *event → actor root → super-root → transaction*.

**Back-of-the-envelope scale** (assumptions: ~10¹² events/day at peak, 300 B/event, 10⁶ active actors):

- ~300 TB/day of data — stays with participants, never on-chain.
- 10⁶ actors × 144 roots/day ≈ 1.4·10⁸ roots/day, absorbed by aggregators.
- 100 aggregators × 24 hourly super-roots ≈ **2,400 on-chain transactions/day**.
- Inclusion proof ≈ 30 hashes × 32 B ≈ 1 KB per event.

**Keys:** HSM/TPM for institutions, social-recovery wallets for small actors; rotation and revocation via the DID document; events judged by the key active at anchor time.

## 6. Threat model and honest limits

> A blockchain guarantees a record was not altered. It does not guarantee the record is true (the *oracle problem*).

| Threat | Mitigation | Residual risk |
|--------|------------|---------------|
| False input claim ("organic grain") | Accredited auditors, lab/isotopic/DNA sampling, sensor & satellite data, issuer reputation and stake | Auditor collusion or error |
| Tag swapped onto real goods | Cryptographic tags (signed NFC, PUF), tamper-evident packaging | Costly physical attack |
| Tag cloning | One-time "redeem" at sale, NFC counters, duplicate detection | Copy before first scan |
| Laundering / blending | Mass balance, no double spend, audits at blending nodes | Off-system extraction |
| History rewriting | Content-addressed IDs, Merkle anchors, independent mirrors | Low |
| Anchoring censorship | Multiple aggregators, direct L1 publishing | Delay |
| Trade-secret leakage | Committed mode, ZK, minimal event data | Graph metadata |
| Sybil reputation attacks | DID ↔ legal entity via VC, accreditation weighting | Medium |
| Quantum adversaries | Crypto-agility, ML-DSA, STARKs | Migration |

Origo does **not** promise that a product is ethical or good, that there are no lies inside the system, or total coverage on day one. It promises that every claim is **signed, attributable, immutable and cross-checkable**. Clients show a trust level (A/B/C) and the *share of traceable mass* — missing history is information too.

## 7. Governance and economics

- Spec: CC BY 4.0. Code: MIT. No single owner; run by an independent foundation/consortium of industry, regulators, NGOs and consumer groups.
- Anchoring is a plugin (multi-chain, cross-confirmed). **No native token** in the core.
- Community registries: process classes and max yields · accreditation issuers · industry profiles (metals, electronics, agri, pharma, textiles).
- Changes: RFC → ≥30 days discussion → reference implementation → working-group vote → versioned release.

## 8. Roadmap

| Stage | Goal |
|-------|------|
| 0 Draft (now) | Event format, threat model, reference core |
| 1 Spec v0.1 | RFCs for DID profile, process registry, proof formats, test vectors |
| 2 Pilot | One regulated high-value chain (e.g. critical minerals or batteries), 5–10 participants |
| 3 Tags & audit | Secure tags, industry auditors, ZK claims |
| 4 Federation | Multiple aggregators, multi-chain anchoring, independent resolvers |
| 5 Scale | Consumer apps, customs and marketplace integration |

**Regulatory context** (verify current texts and dates): EU DPP/ESPR, Battery Regulation, EUDR, CBAM, CSDDD; US UFLPA, DSCSA, FSMA 204; OECD minerals due-diligence guidance; Kimberley Process.

**Open questions:** physical binding for bulk materials (grain, ore) · minimum disclosure acceptable to regulators · auditor economics and conflicts of interest · corrections without breaking immutability (amendment events, not edits).
