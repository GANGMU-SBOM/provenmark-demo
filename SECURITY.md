# Security policy / 安全策略

## What this package must guarantee

`provenmark-verify` is used to decide whether evidence holds. Its security goal is:

> A bundle that does not support its claim must not be reported as "VERIFIED; claim supported", and a correct bundle
> must verify on any conforming implementation.

So we treat as **security vulnerabilities** (please report privately):

* any way to make a forged, altered or unsupported claim verify (signature, commitment, digest or recomputation checks
  bypassed; statistics accepted without recomputation);
* statistical-validity bugs that inflate significance: false-positive rates above the nominal level, wrong
  multiple-testing corrections, p-values that are not super-uniform under the null hypothesis;
* format ambiguities that let two parties compute different digests or statistics from the same files;
* key handling flaws (subkey derivation, commitments, accidental disclosure of key material).

## Threat model (summary)

| Party | Can | Assumed / mitigated by |
|---|---|---|
| Data owner (prover) | choose keys, parameters, reference recipe; select what to report | keys and parameters fixed by commitments inside a record signed at delivery (anchor with an external timestamp); the verifier recomputes; the verifier trains its own reference model; reference fairness check. **Not mitigated:** the number of recipients screened is declared by the owner. |
| Accused recipient | know the algorithms and the public format; hold its own copy (and, after the dispute, its burnt subkeys) | security rests on the key (Kerckhoffs): marks are outputs of AES-256 used as a PRF; recovering keys or predicting unseen marks from data reduces to breaking AES (docs/FORMAL.md, S1). Removal **without** the key (smoothing, denoising, collusion) is an experimental question, not a provable one. |
| Third party / arbitrator | full access to this code, the bundle, the files | needs nothing secret; must obtain the owner's public key independently. |
| Detection-oracle attacker | query a detector repeatedly | detection requires the subkey; bundles reveal only the accused recipient's burnt subkeys, never the master key. |

Out of scope: legal admissibility; side channels in the owner's key storage; a recipient who legitimately holds the
same source data from elsewhere (breaks the training-evidence assumption A3, see FORMAL.md T2).
Known limitations are listed in [docs/FAQ.md](docs/FAQ.md).

## Reporting

Report privately through **GitHub private vulnerability reporting** on this repository (Security tab → "Report a
vulnerability"), or by e-mail to **64031875@qq.com** (subject "[security] provenmark-verify"), with a minimal
reproduction (bundle + files, or a script). We aim to acknowledge within **5 business days** and to
agree on a disclosure date within 90 days. Please do not open a
public issue for unfixed vulnerabilities. Never send real customer data or secret key files; synthetic reproductions
are enough.

---

请通过本仓库的 **GitHub 私密漏洞报告**（Security → Report a vulnerability）私下报告，或发邮件到 **64031875@qq.com**（标题注明 [security]），5 个工作日内确认，附最小复现（证据包 + 文件或脚本）。
能让虚假或不成立的主张通过复核的任何方法、使误报率高于名义水平的统计错误、格式歧义、密钥处理缺陷，都按安全问题处理。
不要发送真实客户数据或密钥文件。
