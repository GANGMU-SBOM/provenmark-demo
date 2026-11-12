# ProvenMark file formats and verification procedure

Status: **draft for the public package** (extracted from the source at commit dad1edb, 2026-11). Format identifiers
carry a version (`.../1`); a breaking change gets a new identifier, and verifiers must reject identifiers they do not
know. This document is normative for third-party verifiers; where it and the code of `provenmark-verify` disagree,
please report it (see SECURITY.md).

Conventions: hex = lowercase hexadecimal; integers in byte strings are little-endian; `‖` = concatenation;
`SHA256`, `BLAKE2b-n` (n-byte digest), `HKDF-SHA256`, `AES-256`, `Ed25519` as standardised.

## 1. Canonical JSON

Everything that is signed is signed as **canonical JSON**: `json.dumps(obj, sort_keys=True, separators=(",", ":"),
ensure_ascii=True)` encoded as ASCII. Floats are serialised by Python's `repr` (shortest round-trip form).

## 2. Keys

| Item | Definition |
|---|---|
| Public key file `provenmark.pub/1` | `{"format": "provenmark.pub/1", "key_id": ..., "public_key": <32-byte Ed25519 public key, hex>}` |
| `key_id` | first 16 hex characters of `SHA256(public_key)` |
| Subkey | `HKDF-SHA256(ikm = master secret, salt = none, info = "provenmark/v1/" ‖ purpose ‖ 0x00 ‖ recipient, L = 32)`. `purpose` is the method name (`ssw`, `csw`, `tone`, `gl`, `evt`, `cue`, `xc`, `xcue`) or `holdout`. The master secret is never revealed. |
| Commitment | `SHA256("provenmark/commit/v1" ‖ subkey)`, hex. Release records contain commitments only; a subkey is revealed only in a dispute, which burns it for that recipient. |

Secret key files (`provenmark.key/1`, `provenmark.key/1+enc`) are an owner-side format and never part of evidence.

## 3. Pseudo-random function

`domain_id(label) = uint64 from BLAKE2b-8(UTF-8 label)`.
`prf_u64(key, domain, i)`: AES-256-ECB encryption under `key` of the 16-byte block `uint64(i as two's complement) ‖
uint64(domain)`; output = first 8 bytes as uint64. `prf_sign = +1 if prf_u64 is odd else -1`;
`prf_unit = (prf_u64 >> 11) / 2^53`. Domain labels used: `ssw:<col>`, `csw:<col>`, `csw-grid`, `evt:<col>`,
`tone:<col>` or `tone:__shared__`, `tonephase:<col>`, `gl:<col>`, `holdout`, plus method-specific labels in `cue`/`xc`.

## 4. Dataset fingerprint and signed manifest `provenmark.manifest/1`

**Cell encoding** (format-independent: the same logical table as CSV or Parquet gives the same digest):
numbers and booleans → IEEE-754 float64 bits (`-0.0` → `0.0`, every NaN → the canonical NaN; integer columns without
missing values whose magnitude reaches 2^53 keep their int64 bits followed by a word `1`); datetimes → UTC int64
nanoseconds (missing → int64 min); everything else → BLAKE2b-16 of `0x01 ‖ UTF-8 text` (missing → of `0x00 "NULL"`),
as two uint64 words.

**Row hash** = BLAKE2b-32 of the concatenated words of the row (columns in file order).
**Chunk hash** (chunks of `chunk_rows` rows, default 1024) = `SHA256(0x00 ‖ row hashes)`.
**Merkle root** over chunk hashes: pairwise `SHA256(0x01 ‖ left ‖ right)`, an odd last node is paired with itself;
empty table → `SHA256("provenmark/empty")`.
**Column digest** = `SHA256(all words of the column)`.

```json
{"manifest": {"format": "provenmark.manifest/1", "tool": "...", "name": "...", "created": "<ISO-8601 UTC>",
              "dataset": {"rows": 43200, "columns": [{"name": "ts", "class": "datetime"}, ...],
                          "chunk_rows": 1024, "merkle_root": "<hex>", "chunk_hashes": ["<hex>", ...] | null,
                          "column_digests": {"<col>": "<hex>"}},
              "extra": {...}},
 "signature": {"alg": "ed25519", "public_key": "<hex>", "key_id": "<16 hex>",
               "sig": "<Ed25519 signature of canonical_json(manifest), hex>"}}
```

`chunk_hashes` is null above 65,536 chunks. A seal of the **original** data has `extra = {}` (or owner metadata).

## 5. Release record (a signed manifest of one delivery)

A release record is a `provenmark.manifest/1` of the **delivered** file with:

```json
"extra": {"kind": "release", "params": {<provenmark.params/1>}, "license": {<licence terms, free JSON>},
          "parent_merkle_root": "<Merkle root of the sealed original>" | null}
```

### `provenmark.params/1`

| Field | Meaning |
|---|---|
| `format`, `tool` | `"provenmark.params/1"`, producing tool and version |
| `recipient` | recipient (licensee) identifier used in subkey derivation. In public material, use pseudonyms. |
| `address` | `{"kind": "time" | "keys" | "position", "columns": [...], "tick": <float>, "time_kind": "datetime" | "numeric"}`. time: address = round(t / tick) (datetime in ns, rounded half up); keys: BLAKE2b-8 of the joined key columns (unit separator 0x1F) shifted right by 1; position: row number |
| `columns` | float columns carrying sample-level marks |
| `methods` | per-method detection parameters (below); only the methods listed are tested |
| `commitments` | `{purpose: commitment}` for every method and for `holdout` |
| `holdout` | optional, `provenmark.holdout/1` (below) |
| `constraints` | optional, the physical constraints the delivery was certified against (informational for verification) |

Per-method parameters: `ssw {columns, alpha}`; `csw {columns, alpha, chip}`; `evt {columns}`;
`tone {band: [f_lo, f_hi], columns: {col: {counters: [...]}}, shared, select: {...}}`; `gl {columns: {col: {delta}}}`;
`cue`, `xc`, `xcue`: method-specific dictionaries (experimental). Only detection-relevant values are needed by a
verifier; amplitudes are recorded for information.

### `provenmark.holdout/1`

`{"format", "block_len": rows per block, "q": withheld share, "start": first row, "n_blocks", "withheld_blocks",
"reference": recipe}`. Assignment: rank blocks by `prf_unit(holdout subkey, domain_id("holdout"), block index)` and
withhold the `max(1, round(q · n_blocks))` smallest. Reference recipe: `{"type": "ridge"}`,
`{"type": "learned", "arch": "mlp" | "dlinear" | "patchtst", "epochs", "stride", "context", "horizon"}`, or
`{"type": "best_of", "context", "horizon", "refs": [...]}` (smallest p of the components × number of components).

## 6. Copy evidence `provenmark.evidence/1`

| Field | Meaning |
|---|---|
| `claim`, `null_hypothesis` | text |
| `suspect_sha256`, `suspect_rows` | SHA-256 of the suspect file's bytes; rows read |
| `release_record` | the full signed release record of the accused recipient |
| `recipient` | accused recipient |
| `revealed_subkeys` | `{method: subkey hex}` for the accused recipient only (burnt) |
| `result.methods` | `{method: {"z", "p"}}` |
| `result.p_fisher` | Fisher combination of the p-values of the **decision methods** (methods use independent subkeys) |
| `result.decision_methods`, `result.info_only` | methods entering the decision, and methods reported for information only. `tone` is always information only: its parametric p-value is not valid on data with natural spectral lines (FORMAL.md N1). Bundles produced before this rule (no such fields, `tone` inside Fisher) fail `recomputed_p_fisher`. |
| `result.p_min_bonferroni` | min p × number of decision methods (information only) |
| `result.licensees_screened`, `result.familywise_p` | number of recipients screened N (**owner's declaration**); `min(1, p_fisher · N)` |
| `result.supported` | `familywise_p < alpha` |
| `screening` | owner's ranking of screened recipients (not verifiable by a third party: other recipients' keys are not revealed) |
| `alpha`, `max_shift` | significance level; offset search range used by the detectors (0 = off) |
| `timestamp_request` | digest of the release record to anchor with RFC 3161 / OpenTimestamps |

**Verification** (`provenmark-verify verify-evidence evidence.json suspect --pubkey owner.pub.json`; the full ProvenMark tool installs the same `provenmark-verify` command):
1. `release_signature`: Ed25519 signature of the release record valid, and (with `--pubkey`) made by the pinned key.
   `signer_pinned`: the owner's public key was given. Without it the signature can only be checked against the key
   embedded in the bundle — anyone can self-sign — so the bundle is **never VERIFIED without `--pubkey`**. Obtain the
   owner's key through an independent channel.
2. `commitment:<method>`: `commitment(revealed subkey) == params.commitments[method]` (the key was fixed at delivery).
3. `suspect_file_hash`: the file is byte-identical to the one the evidence refers to.
4. `recomputed_z:<method>`: running the detector with the revealed subkey reproduces z (relative tolerance 1e-6).

5. `methods_complete`: the methods of the signed record, the revealed subkeys and the reported results are the same set.
6. `recomputed_p:<method>`, `decision_methods` (if present), `recomputed_p_fisher` (over the decision methods only), `recomputed_familywise_p` (= min(1, p_fisher · N) with the declared N),
   `recomputed_conclusion` (`familywise_p < alpha`); `licensees_screened` must be an integer ≥ 1 (and match `screening`),
   `alpha` in (0, 1). The verifier's verdict (`claim_supported`) and the family-wise p it reports are its own
   recomputation, never the values written in the bundle.

## 7. Training evidence `provenmark.evidence-training/1`

| Field | Meaning |
|---|---|
| `release_record` | signed release record with `params.holdout` and `parent_merkle_root` |
| `revealed_holdout_key` | the accused recipient's holdout subkey (burnt) |
| `queries` | `{columns, context, horizon, per_block, seed}`: the query windows are a deterministic function of the original data, the holdout layout and these values (`holdout.make_queries`) |
| `predictions_sha256` | SHA-256 of the predictions array as contiguous little-endian float64 (shape not included; shape is checked separately against the regenerated queries) |
| `result` | `z`, `p` (exact permutation p, best-of references × number of references), `p_floor`, `n_decoys`, `reference`, `reference_fairness_p`, `components`, `p_conditional` (given other recipients), `familywise_p` = max(p, conditional ps) × N, `licensees_screened`, `supported` (`familywise_p ≤ alpha`) |
| `conditioning` | per conditioning recipient: revealed holdout key, its signed release record, conditional p |
| `requires_for_verification` | the original data (all blocks, disclosed confidentially to the arbiter) and the predictions file |

Decoy assignments: decoy key i = `SHA256("provenmark/holdout-decoy" ‖ uint64(seed) ‖ uint64(i))` with seed 0; the
fairness check uses seed 1.

**Verification** (`verify-evidence evidence_training.json --original original.csv --predictions predictions.npy --pubkey owner.pub.json`):
`release_signature`; `signer_pinned`; `commitment:holdout`; `original_matches_signed_root` (fingerprint of the original == the signed
`parent_merkle_root`); `predictions_sha256`; `predictions_shape`; for every conditioning recipient a valid signed
record whose commitment matches the revealed key and whose holdout layout and parent root match
(`conditioning_key:<r>`); `licensees_screened`, `alpha_valid`, `n_decoys_valid`; then the test is recomputed and the conclusion is the verifier's own. Ridge reference: `recomputed_p`, `recomputed_familywise_p`,
`recomputed_z` and `recomputed_conclusion` must match. Learned reference: the **verifier trains its own reference** from the committed recipe
(own seed, `--reference-seed`); results are statistically, not bit-for-bit, reproducible, so the check is that the
verifier's family-wise p leads to the same conclusion (`verifier_reference_supports_claim`) and that the verifier's
reference is not unusually good on the withheld blocks (`verifier_reference_fairness`, p ≥ 0.01).
`owner_reference_fairness` checks the owner's reported fairness p (≥ 0.01).
To rule out a falsified record of the model's answers, the arbiter can regenerate the query file
(`provenmark-verify holdout-queries original.csv --evidence evidence_training.json`) and query the model itself.

## 8. What a successful verification means

"VERIFIED" = the bundle is internally consistent, bound to keys fixed and signed at delivery, and the statistics are
reproducible from source code anyone can read and run. "claim supported" = additionally the family-wise p is below the stated α. It is
statistical evidence under the assumptions in docs/FORMAL.md, not proof; it is not a legal opinion.
