# FAQ

[中文](FAQ.zh-CN.md)

## Our data leaked. Can we find out who leaked it?

**Yes — this is ProvenMark's most mature capability.** Every customer's copy carries its own invisible fingerprint.
Given a suspect file, the key and the delivery record (no original needed) test each customer in turn and name the one
whose copy it is.

- **Disguised copies are still traced.** In the demo, the leaked copy was smoothed with a 9-point moving average,
  cropped to the middle 60 % and re-stamped by +7 s, and was still traced to the right customer with a family-wise
  p below 1e-90 — the probability that the file matches that customer's fingerprint by chance.
- **Common processing does not remove it.** On the SKAB water-pump data (10 customers, 6 runs per attack): noise,
  rounding, unit conversion, resampling, shuffling, crop + subsample combinations, dropping columns, timestamp shifts,
  averaging or splicing 2–3 customers' copies, and an AI denoiser — **the leaker was found every time, and no
  innocent customer was ever accused**.
- **The data stays usable.** The fingerprint is about 1/10 of the sensor noise and capped by each sensor's tolerance;
  ranges, rates, conservation laws and fault labels are preserved. On SKAB, 680/680 fidelity certificates passed and
  anomaly-detection F1 went from 0.7485 to 0.7483.

**Where it applies:** five or more customers who average their copies and add noise can push the fingerprint below
the evidence threshold (it still attributed 12 of 30 such cases).

## Can we prove that someone trained an AI model on our data?

**We can give statistical evidence that the other side can verify for themselves — and the better a model has learned
your data, the stronger it is.** Those are exactly the models worth worrying about.

- **How:** each delivery silently withholds about 20 % of time blocks, chosen by a key (no value in the data is
  changed; each customer misses different blocks). A model trained on the delivery predicts the delivered blocks
  clearly better than the withheld ones; a model that never saw the data treats them alike. An exact permutation test
  over 10,000 random splits says whether the gap could be chance.
- **API access is enough.** No weights, training data or cooperation are needed: the owner sends queries and records
  the answers, and an arbitrator can re-query the model independently instead of trusting the owner's record.
- **Measured:** for well-trained models, with the delivery making up only **16 %** of their training data, 6 of 6 were
  detected and attributed to the right customer (SKAB, z ≈ 11); at 10 %, 5 of 6 were detected (ETTm1). Validated on
  linear, MLP and Transformer-style forecasting models trained on the data.
- **Common evasions fail:** for such models, noise or quantisation on the API output, returning only the first steps,
  ensembling with another model, fine-tuning afterwards and distilling into a new model all left the evidence intact.
  Smoothing the data before training fools plain queries, but the owner recovers it by also sending smoothed queries (6/6).
- **It tells customers apart:** each customer misses different blocks, and a conditional test rules out an innocent
  customer inheriting the signal of an overlapping leaker — no false attribution in the experiments.
- **Demo:** evidence from API answers only, recomputed by the arbitrator from the original data, the recorded answers
  and the owner's public key, z ≈ 12.

**Where it applies:**
- linear models (e.g. DLinear) memorise little of the specific data and are not detected;
- for weakly-fitting models, deliberate evasion (larger output noise, returning only the first steps, ensembling) can
  remove the evidence, and more queries do not bring it back;
- p-values have a floor (about 1e-4 with 10,000 splits), so this evidence is less extreme than leak tracing;
- it does not apply if the other side legitimately obtained data from the same source elsewhere.

So the precise statement is: **for models that have really learned your data, it gives training-use evidence with a
controlled false-positive rate that the other side can verify** — not a universal test of whether any AI ever used it.

## How is the evidence used in a dispute?

ProvenMark produces technical evidence: an evidence bundle plus a readable report. Anyone can check it with the
source-available `provenmark-verify`: that the record was signed by the owner at delivery, that the keys were fixed
then, that the file is the one in dispute — and then recompute every statistic from scratch. Typical uses:

- **write it into the contract up front** — traceable fingerprints, keyed withheld blocks, an audit clause — so the
  cost and likelihood of being caught are visible, which by itself deters breaches;
- in a dispute, an evidence bundle the other side can check independently supports negotiation, a formal demand,
  an audit or a request for the other side's training records;
- in arbitration or litigation, an expert can give an opinion based on the bundle and its verification.

This is statistical evidence with a stated false-positive rate; how it is weighed legally depends on the jurisdiction
and rules of evidence. ProvenMark does not give legal advice.

## Can it falsely accuse an innocent customer?

The false-positive rate is **known in advance and checkable afterwards**:

- **Leak tracing:** for any data, whatever its autocorrelation, the false-positive rate has a proven bound exp(−z²/2)
  ([FORMAL.md](FORMAL.md) T1), with no calibration needed; screening several customers is corrected for their number.
  The default threshold is a family-wise p < 1e-6; in the experiments, innocent customers never exceeded z ≈ 1.9–3.4.
- **Training-use evidence:** the permutation p-value is exact when the model never saw the delivered data
  (FORMAL.md T2, T3). With 100 models that never saw the data: ETTm1 3.0 % at p ≤ 0.05 and 1.0 % at p ≤ 0.01; SKAB
  3.0 % and 0 % — within nominal rates.
- **We publish our own corrections:** we found that an auxiliary mark (`tone`, spectral lines) gives invalid p-values
  on data with periodic components of its own — before the fix it caused 7 false attributions in 150 tracing runs. It
  is now listed for information only and never part of a decision; after the fix, 0 of 150 (FORMAL.md N1).

## Can AI reverse-engineer or break it?

- **Learning the key or the mark from the data: infeasible under standard cryptographic assumptions.** Every mark sign,
  chip length and phase and the choice of withheld blocks is generated from the key with AES-256; predicting them
  without the key would break AES (FORMAL.md S1). The algorithms are public; security rests on the key.
- **Removing the mark without the key** is an empirical question, answered in the first section: common
  processing, 2–3-copy collusion and an AI denoiser did not remove it (the denoiser only displaced it; the offset search
  recovers it, median z 8–12). Collusion of five or more copies plus noise is the known weakness.
- **Reverse-engineering the verifier gains nothing:** it contains no keys; a bundle reveals only the accused
  customer's subkey, which is burnt on disclosure. The master key and other customers' keys never appear.

## Why should a third party trust that the owner did not cheat?

- Keys and parameters are committed in a **delivery record signed at delivery** and cannot be changed afterwards
  (add an external trusted timestamp);
- the verifier must use the owner's public key obtained independently, otherwise nothing verifies;
- every statistic and the conclusion are recomputed by the verifier — the numbers in the bundle are only compared; for
  training evidence the verifier trains its own reference model from the committed recipe, checks it is not biased
  towards the withheld blocks, and can re-query the model itself.
- The one thing the owner declares is how many customers were screened (for the multiple-testing correction); the
  verification output says so explicitly.

## What does revealing a subkey cost?

The accused customer's subkey is burnt (whoever holds it can strip that fingerprint), so later deliveries to that
customer should use a new recipient identifier. The master key and other customers' fingerprint keys are never
revealed. Training evidence also reveals the holdout keys of the customers used in the conditional test (also burnt)
so that a third party can recompute it.

## Where do the numbers come from?

Two public industrial datasets (ETTm1 transformer monitoring; SKAB water-pump test bench with 34 labelled fault
experiments), forecasting models of three kinds (linear, MLP, Transformer-style), 3–6 independent repetitions per
setting. The detailed experimental report — parameters, every attack, confidence intervals — is available on request
(64031875@qq.com); provable properties and their assumptions are in [FORMAL.md](FORMAL.md). Please quote numbers
together with their conditions.
