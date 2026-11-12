# FAQ

Every answer is based on the project's experimental report (published as the white paper) and on
[FORMAL.md](FORMAL.md). Numbers come from two datasets (ETTm1 transformer monitoring, SKAB water-pump test bench),
CPU-scale models and **3–6 seeds per cell, so confidence intervals are wide**. Quote them with their conditions.
中文版：[FAQ.zh-CN.md](FAQ.zh-CN.md).

## Can AI reverse-engineer or break the watermark?

**Learning the key or the mark sequence from data: infeasible under standard cryptographic assumptions.** Every
key-dependent quantity (per-sample / per-chip signs, chip lengths and phases, the holdout split) is an output of
AES-256 used as a pseudo-random function. An algorithm — any ML model included — that predicts unseen signs from marked
data with non-negligible advantage would distinguish AES from a random permutation (FORMAL.md, S1). This is a
reduction to AES, not an unconditional proof. The algorithms are public; security rests on the key (Kerckhoffs).

**Removing the mark without the key: possible to try, answerable only experimentally.** Tested (SKAB, 10 recipients,
6 seeds per cell): noise, rounding, unit conversion, linear resampling, shuffling, crop + subsample combinations,
dropping columns, timestamp shifts (with the ±30-sample offset search), 2–3-copy averaging or splicing — the leaker was
identified every time, with **zero false attributions**. A self-supervised AI denoiser did not delete the chip mark
`csw` but displaced it; the offset search recovers it (median z 8–12). A 9-point moving average erases the
per-sample mark `ssw` (0/6) but not `csw`. **Known weakness:** averaging ≥ 5 recipients' copies plus noise
(`ssw` 7/30, `ssw+csw` Fisher 12/30). **Not tested:** notch filtering / spectral whitening, estimate-and-subtract
attacks with many copies, 100+ recipients.

## What is the false-positive rate?

* **Copy / leak detection:** under "the data is independent of this key", the false-positive rate is at most
  exp(−z²/2) for **any** data, whatever its autocorrelation (Hoeffding, FORMAL.md T1); no calibration is needed.
  Screening N recipients is Bonferroni-corrected. This holds for `ssw` and `csw` (`evt` is an exact binomial test). **`tone` (spectral
  lines) is an exception:** when the data has periodic components of its own, its parametric p-value is not valid
  (innocent keys reached p ≤ 1e-6 in 2.4 % of trials). `tone` is therefore listed for information only and never enters
  a decision (FORMAL.md N1); before this rule, ssw + tone tracing falsely attributed an innocent licensee in 7/150 runs,
  after it 0/150. In all attack experiments, innocent recipients reached at most
  z ≈ 1.9–3.4; the default decision threshold is a family-wise p < 1e-6. **Not tested:** family-wise error at
  1,000 recipients.
* **Training-use evidence (keyed delivery holdout):** the permutation p-value is exact under "the model never saw the
  delivered data" (T2; conditional attribution T3). Independent null models: ETTm1, 100 nulls, default best-of-two
  rule: 3.0 % at p ≤ 0.05 and 1.0 % at p ≤ 0.01; SKAB, 100 nulls: 3.0 % and 0 %. **Limit:** the p-value floor is
  about 1e-4 with 10,000 decoys, so training evidence does not reach the 1e-6 level typical of copy evidence.
* **Assumption:** if the suspect model was *legitimately* trained on data from the same source, the null hypothesis
  of the training test does not hold (observed on SKAB).

## Can it prove that someone trained a model on my data?

**It can give statistical evidence under fairly narrow conditions. It does not prove it, and it does not guarantee
that every use is detected.**

* **Detected:** models that fit the delivered data strongly. MLP (20 epochs) on SKAB with the delivery being 16 % of
  its training data: 6/6 detected and attributed (z ≈ 11); MLP (30 epochs) on ETTm1 at 10 %: 5/6. For such models,
  output noise, quantisation, truncated outputs, ensembling, fine-tuning and distillation did not remove the evidence;
  smoothing the data before training defeats the plain queries, and the owner recovers it with smoothed queries.
  Only API access to the suspect model is needed.
* **Not detected / not reliable:** linear models (DLinear) on both datasets; weakly-fitting models (PatchTST, 5 epochs,
  z ≈ 4) lose the evidence under cheap API-side tricks (0.5σ output noise, returning only the first 4 steps,
  ensembling) and under fine-tuning, distillation or smoothing — 4× more queries did not help. **Fine-tuned pre-trained
  foundation models have not been tested with this method.**
* **Which recipient:** each recipient gets a different withheld set; a conditional test prevents innocent recipients
  from inheriting the leaker's signal. Zero false attributions in the experiments, but attribution power under weak
  signals is unstable (2/6 to 4/6).

## How does a third party know the owner did not cheat?

Keys and parameters are fixed by commitments in a release record signed at delivery (add an external timestamp);
the verifier recomputes every statistic with source code anyone can read and run; for training evidence the verifier trains its own reference
model from the committed recipe, checks that it is not biased towards the withheld blocks, and can regenerate the
queries to re-query the model itself. **Still declared by the owner:** how many recipients were screened.

## What does revealing a subkey cost?

It burns that recipient's fingerprint (whoever holds the subkey can strip that mark). The master key and other
recipients' fingerprint keys are never revealed; training evidence also reveals the holdout keys of the recipients
used for the conditional test.

## Does marking damage the data?

Marks are about 0.1× the local noise level and capped by per-sensor absolute tolerances; the commercial
constraint-aware embedding guarantees tolerances, ranges, rates and linear conservation laws (FORMAL.md P1) and never
touches fault labels. Measured: SKAB 680/680 fidelity certificates passed, anomaly-detection F1 0.7485 → 0.7483;
ETTm1 forecast error change ≤ 0.3 %. The holdout method changes no values; it withholds about 20 % of time blocks.

## What is experimental?

The `gl`, `cue`, `xc`, `xcue` marks and the mark-based training probes. They are not capability claims
(e.g. `cue` was not detected on an 80 % crop of a marked copy).
