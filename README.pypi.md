# provenmark-verify

**Check ProvenMark evidence yourself — no secret key, no trust in the data owner's software.**

ProvenMark puts an invisible, per-customer fingerprint into licensed industrial time-series / tabular data and can build
training-use evidence from a keyed holdout of time blocks. When a data owner says *"this leaked file came from
customer X"* or *"this model was trained on the data delivered to X"*, it hands over an evidence bundle.
`provenmark-verify` lets anyone — the accused customer, an expert, an arbitrator — re-check that bundle:

- the delivery record was signed by the owner at delivery time and fixed the keys by commitment;
- the revealed key is the one committed then, not chosen after seeing the suspect file;
- the suspect file / original data / recorded model answers are exactly the ones in question;
- every statistic and the conclusion are recomputed from scratch on your machine.

```bash
pip install provenmark-verify            # add [torch] for training evidence with a neural reference model

provenmark-verify verify-evidence evidence.json suspect.csv --pubkey owner.pub.json
provenmark-verify verify-evidence evidence_training.json --original original.csv \
    --predictions predictions.npy --pubkey owner.pub.json
```

`--pubkey` is required: obtain the owner's public key through an independent channel. Exit code 0 = verified.

Also included: every detector that can appear in a ProvenMark delivery record, the exact permutation tests,
`verify-manifest` for signed data manifests, `holdout-queries` to re-query a suspect model yourself, and a basic
watermark (`keygen`, `ssw-mark`, `ssw-detect`) to try on your own data.

**Documentation** (GitHub): [README and 60-second demo](https://github.com/GANGMU-SBOM/provenmark-demo) ·
[FAQ](https://github.com/GANGMU-SBOM/provenmark-demo/blob/main/docs/FAQ.md) ·
[evidence formats and verification procedure](https://github.com/GANGMU-SBOM/provenmark-demo/blob/main/docs/FORMATS.md) ·
[provable properties](https://github.com/GANGMU-SBOM/provenmark-demo/blob/main/docs/FORMAL.md) ·
[security policy](https://github.com/GANGMU-SBOM/provenmark-demo/blob/main/SECURITY.md)

**Licence:** source-available under the PolyForm Shield License 1.0.0 (included in the package with its NOTICE):
anyone may use, read, modify and redistribute it for any purpose — including companies, experts and law firms verifying
evidence — except to provide a product that competes with it. It is not an OSI open-source licence.

Contact: 64031875@qq.com
