"""Owner-side helpers for the public tests: build release records and evidence bundles from the documented formats
(docs/FORMATS.md) using only public primitives. They double as a conformance check of the format specification."""
import hashlib
import json

import numpy as np
from click.testing import CliRunner

from provenmark_verify import core, holdout as ho, integrity
from provenmark_verify.addressing import fit_address
from provenmark_verify.cli import main
from provenmark_verify.io import read_table
from provenmark_verify.keys import commitment
from provenmark_verify.methods import ssw


def run(*a, code=0):
    r = CliRunner().invoke(main, [str(x) for x in a])
    assert r.exit_code == code, r.output
    return r.output


def write_pub(bundle, path):
    json.dump({"format": "provenmark.pub/1", "key_id": bundle.key_id, "public_key": bundle.public_key.hex()},
              open(path, "w"))


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def ssw_release(df, bundle, recipient, columns, time_col="ts", alpha=0.1):
    addr = fit_address(df, time_col)
    k = bundle.subkey("ssw", recipient)
    marked, _ = ssw.embed(df, k, addr, columns, alpha)
    params = {"format": core.PARAMS_FORMAT, "tool": "test", "recipient": recipient, "address": addr.to_dict(),
              "columns": columns, "methods": {"ssw": {"columns": columns, "alpha": alpha}},
              "commitments": {"ssw": commitment(k)}}
    rel = integrity.seal(marked, bundle, "marked.csv",
                         {"kind": "release", "params": params, "license": {}, "parent_merkle_root": None})
    return marked, rel, k


def copy_evidence(suspect_path, rel, keys, n_screen=1, alpha=1e-6, max_shift=0):
    params = rel["manifest"]["extra"]["params"]
    sdf = read_table(str(suspect_path), params["address"]["columns"])
    res = core.detect_with_keys(sdf, keys, params, max_shift)
    comb = core.combine(res)
    fam = min(1.0, comb["p_fisher"] * n_screen)
    return {"format": "provenmark.evidence/1", "suspect_sha256": sha256_file(suspect_path),
            "suspect_rows": int(len(sdf)), "release_record": rel, "recipient": params["recipient"],
            "revealed_subkeys": {m: k.hex() for m, k in keys.items()},
            "result": {"methods": {m: {"z": float(v["z"]), "p": float(v["p"])} for m, v in res.items()},
                       "p_fisher": comb["p_fisher"], "p_min_bonferroni": comb["p_min_bonferroni"],
                       "familywise_p": fam, "licensees_screened": n_screen, "supported": bool(fam < alpha)},
            "alpha": alpha, "max_shift": max_shift}


def holdout_release(original, bundle, recipient, block_len, q, reference, parent_root):
    hk = bundle.subkey("holdout", recipient)
    nb = len(original) // block_len
    w = ho.assign(hk, nb, q)
    hp = {"format": "provenmark.holdout/1", "block_len": block_len, "q": q, "start": 0, "n_blocks": nb,
          "withheld_blocks": int(w.sum()), "reference": reference}
    keep = np.zeros(len(original), bool)
    for b in range(nb):
        if not w[b]:
            keep[b * block_len:(b + 1) * block_len] = True
    delivered = original[keep]
    addr = fit_address(original, "ts")
    cols = ["temp", "vib"]
    params = {"format": core.PARAMS_FORMAT, "tool": "test", "recipient": recipient, "address": addr.to_dict(),
              "columns": cols, "methods": {}, "commitments": {"holdout": commitment(hk)}, "holdout": hp}
    rel = integrity.seal(delivered, bundle, "delivery.csv",
                         {"kind": "release", "params": params, "license": {}, "parent_merkle_root": parent_root})
    return delivered, rel, hk


def training_evidence(original, rel, hk, q, pred, n_decoys=2000, alpha=1e-3):
    hp = rel["manifest"]["extra"]["params"]["holdout"]
    losses = ho.losses_from_predictions(q, pred, hp["n_blocks"])
    refs = [ho.reference_losses(original, hp, q, c) for c in ho.reference_components(hp["reference"])]
    r = ho.best_of_test(losses, hp, hk, refs, n_decoys, seed=0)
    fair = min((ho.reference_fairness(rf, hp, hk, n_decoys) for rf in refs), key=lambda f: f["p_fair"])
    return {"format": "provenmark.evidence-training/1", "release_record": rel,
            "recipient": rel["manifest"]["extra"]["params"]["recipient"], "revealed_holdout_key": hk.hex(),
            "queries": {k: q[k] for k in ("columns", "context", "horizon", "per_block", "seed")},
            "predictions_sha256": hashlib.sha256(np.ascontiguousarray(pred, dtype="<f8").tobytes()).hexdigest(),
            "result": {"z": r["z_vs_decoys"], "p": r["p_perm"], "p_floor": r["p_min_possible"], "n_decoys": n_decoys,
                       "reference": hp["reference"], "reference_fairness_p": fair["p_fair"],
                       "components": r["components"], "p_conditional": {}, "familywise_p": r["p_perm"],
                       "licensees_screened": 1, "supported": bool(r["p_perm"] <= alpha)},
            "conditioning": [], "screening": None, "alpha": alpha}
