# Demos — be the arbitrator / 你来当仲裁方

Two disputes, already "filed". The owner has done its part with the commercial ProvenMark tool on **synthetic plant
data** (1 Hz, 12 h, temperature, vibration, pressure, machine state) and handed over evidence bundles. Your job: decide
whether the evidence holds, using only this repository and the owner's public key.

两起"已经立案"的纠纷。所有者已用 ProvenMark 商业版在**合成工厂数据**上完成取证，交出了证据包。你的任务：只用本仓库和所有者公钥，判断证据是否成立。

## Setup / 准备

```bash
pip install -e .                    # case 2 also needs: pip install -e ".[torch]"
# download sample_evidence.zip from the Releases page, then:
unzip sample_evidence.zip -d demos/
```

## Case 1 — "Who leaked our plant data?" / 谁泄露的

The same export went to three licensees (acme, beta, gamma), each copy with a different invisible fingerprint
(`ssw` per-sample + `csw` smoothing-robust chips + `evt` on machine-state transitions). A copy found online had been
**smoothed with a 9-point moving average, cropped to the middle 60 % and re-stamped by +7 s**. The owner accuses beta.

同一份数据交付给 acme、beta、gamma，每份带不同的隐形指纹。网上出现的拷贝被 **9 点平滑、截取中间 60%、时间戳 +7 秒**。所有者指认 beta。

```bash
bash demos/verify_sample_evidence.sh leak
```

Every statistic is recomputed on your machine; the owner's readable report is `sample_evidence/leak/evidence.md`.

## Case 2 — "Did they train an AI on it?" / 是否被拿去训练 AI

Each licensee's delivery silently withheld a different keyed 20 % of time blocks — nothing was added to the data.
Licensee beta trained a forecaster on its delivery and serves it as an API. The owner only recorded the API's answers
to a query set spread over all blocks. You receive the original (synthetic) data, the recorded answers and the bundle,
**train your own reference model** from the recipe signed at delivery, and recompute the test — including the
conditional test showing it is beta and not another licensee whose withheld weeks happen to overlap.

每个被许可方少给 20% 的时间块（数据不加任何标记）。beta 用交付数据训练了预测模型并对外提供 API；所有者只记录了 API 的回答。
你拿到原始数据、记录的回答和证据包，**按交付时签名的配方自己训练参考模型**，重算检验，包括排除"无辜方被误指认"的条件检验。

```bash
bash demos/verify_sample_evidence.sh training
```

The bundle also contains beta's model's recorded answers (`predictions.npy`). To check that the owner recorded them
honestly, regenerate the queries and ask the model yourself:
`provenmark-verify holdout-queries sample_evidence/training/plant.csv --evidence sample_evidence/training/evidence_training.json`.

## Try to break it / 试着攻破它

* Change one `z` or `p` in `evidence.json`, or set `"supported": true` on a bundle that does not support its claim.
* Add `1e-3` to one value of `predictions.npy`.
* Verify against a different file, or with a different public key, or with no `--pubkey` at all.
* Re-sign the delivery record with your own key.

Each of these makes verification fail. If you find a way to make a false claim verify, that is a security issue:
please report it ([SECURITY.md](../SECURITY.md)) — we treat false-positive bugs as vulnerabilities.

改一个数字、改一个预测值、换文件、换公钥、不给公钥、用自己的密钥重签交付记录——复核都会失败。如果你找到了让虚假主张通过复核的办法，
请按 [SECURITY.md](../SECURITY.md) 报告。

## What the demos do not show / 演示没有展示的

Detection is statistical evidence, not proof. Training-use evidence needs a model that fitted the delivered data
(linear models are not detected; weakly-fitting models can evade it). ≥ 5-copy collusion with noise defeats the copy
fingerprint. Details: [docs/FAQ.md](../docs/FAQ.md).

The bundles are generated with `packaging/export_public.py --e2e --with-torch --demo-bundles` in the ProvenMark
repository (synthetic data, throwaway keys) and published as the release asset `sample_evidence.zip`.
Questions, pilots on your own data: **64031875@qq.com** · ⭐ the repo to follow new demos.
