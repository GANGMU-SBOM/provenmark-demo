# Demos — be the independent reviewer / 你来当复核方

Two **simulated** scenarios on **synthetic** plant data (1 Hz, 12 h: temperature, vibration, pressure, machine state).
The data owner and the licensees acme, beta and gamma are fictional; no real company, dataset or dispute is involved.
The owner's side was produced with the commercial ProvenMark tool and packaged as evidence bundles. Your role is the
independent reviewer: decide whether the evidence holds, using only this repository and the owner's public key.

两个**模拟场景**，使用**合成**的工厂数据（1 Hz、12 小时：温度、振动、压力、设备状态）。数据所有者与被许可方 acme、beta、gamma 均为虚构，
不涉及任何真实的公司、数据或纠纷。所有者一侧用 ProvenMark 商业版生成证据包；你扮演独立的复核方：只用本仓库和所有者公钥，判断证据是否成立。

## Setup / 准备

```bash
pip install provenmark-verify                 # scenario 2 also needs: pip install "provenmark-verify[torch]"
curl -LO https://github.com/GANGMU-SBOM/provenmark-demo/releases/latest/download/sample_evidence.zip
unzip -q sample_evidence.zip -d demos/        # in a clone of this repository; elsewhere just unzip it
```

The commands below use `bash demos/verify_sample_evidence.sh` from a clone of this repository. Without a clone, run
`provenmark-verify verify-evidence` on the files in `sample_evidence/leak` or `sample_evidence/training`, as shown in
the [main README](../README.md). / 下面的命令在本仓库的克隆目录中运行；不克隆时，对 `sample_evidence/leak` 或
`sample_evidence/training` 里的文件直接运行 `provenmark-verify verify-evidence`（见[主 README](../README.zh-CN.md)）。

## Scenario 1 — "Who leaked the plant data?" / 场景 1：谁泄露的

The same export went to three licensees (acme, beta, gamma), each copy with a different invisible fingerprint
(`ssw` per-sample + `csw` smoothing-robust chips + `evt` on machine-state transitions). A copy found online had been
**smoothed with a 9-point moving average, cropped to the middle 60 % and re-stamped by +7 s**. The owner accuses beta.

同一份数据交付给 acme、beta、gamma，每份带不同的隐形指纹。网上出现的拷贝被 **9 点平滑、截取中间 60%、时间戳 +7 秒**。所有者指认 beta。

```bash
bash demos/verify_sample_evidence.sh leak
```

Every statistic is recomputed on your machine; the owner's readable report is `sample_evidence/leak/evidence.md`.

## Scenario 2 — "Was it used to train an AI?" / 场景 2：是否被拿去训练 AI

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

## Where the conclusions apply / 结论的适用范围

The evidence is statistical, with a stated error rate. Training-use evidence is strongest for models that really
learned the delivered data (like beta's forecaster here); linear models memorise little and are not detected, and
weakly-fitting models can evade it on purpose. Leak tracing holds up to 2–3 colluding copies; five or more averaged
with noise can defeat it. Details: [docs/FAQ.md](../docs/FAQ.md).

证据是误报率明确的统计证据。训练使用证据对真正学到交付数据的模型最有力（如本例中 beta 的预测模型）；线性模型几乎不记住具体数据、检不出，
拟合较弱的模型若有意规避可能检不出。泄露追溯扛得住 2–3 份拷贝合谋，5 份以上平均再加噪可能失效。详见 [docs/FAQ.zh-CN.md](../docs/FAQ.zh-CN.md)。

The bundles are generated with `packaging/export_public.py --e2e --with-torch --demo-bundles` in the ProvenMark
repository (synthetic data, throwaway keys) and published as the release asset `sample_evidence.zip`.
Questions, pilots on your own data: **64031875@qq.com** · ⭐ the repo to follow new demos.
