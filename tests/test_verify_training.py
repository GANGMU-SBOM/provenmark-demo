import json

import numpy as np

from conftest import make_df, fixed_bundle
from _helpers import run, write_pub, holdout_release, training_evidence
from provenmark_verify import holdout as ho, integrity
from provenmark_verify.io import read_table

BL, L, H = 128, 48, 16
REF = {"type": "ridge", "context": L, "horizon": H}


def knn_memoriser(x, L, H):
    idx = np.arange(0, len(x) - L - H)
    C = np.stack([x[i:i + L] for i in idx]); Y = np.stack([x[i + L:i + L + H] for i in idx])
    cn = (C ** 2).sum(1)
    return lambda ctx: Y[np.argmin(cn[None, :] - 2 * ctx @ C.T, axis=1)]


def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    b = fixed_bundle("public-training")
    write_pub(b, "pub.json")
    make_df(BL * 60, seed=4).to_csv("orig.csv", index=False)
    orig = read_table("orig.csv", ["ts"])
    root = integrity.fingerprint(orig)["merkle_root"]
    delivered, rel, hk = holdout_release(orig, b, "beta", BL, 0.2, REF, root)
    q = ho.make_queries(orig, rel["manifest"]["extra"]["params"]["holdout"], ["temp", "vib"], L, H, 8, 0)
    return b, orig, delivered, rel, hk, q


def predict(models, q):
    out = np.zeros(q["fut"].shape)
    for j, f in models.items():
        m = q["col"] == j
        out[m] = f(q["ctx"][m])
    return out


def test_training_evidence_verifies_and_rejects_tampering(tmp_path, monkeypatch):
    b, orig, delivered, rel, hk, q = setup(tmp_path, monkeypatch)
    pred = predict({j: knn_memoriser(delivered[c].to_numpy(), L, H) for j, c in enumerate(["temp", "vib"])}, q)
    np.save("pred.npy", pred)
    ev = training_evidence(orig, rel, hk, q, pred)
    assert ev["result"]["supported"]
    json.dump(ev, open("ev.json", "w"))
    out = run("verify-evidence", "ev.json", "--original", "orig.csv", "--predictions", "pred.npy", "--pubkey", "pub.json")
    assert "VERIFIED" in out and "claim supported" in out
    np.save("pred2.npy", pred + 1e-3)
    assert "FAIL predictions_sha256" in run("verify-evidence", "ev.json", "--original", "orig.csv", "--predictions", "pred2.npy",
                                             "--pubkey", "pub.json", code=1)
    bad = json.loads(json.dumps(ev)); bad["result"]["p"] /= 10
    json.dump(bad, open("bad.json", "w"))
    assert "FAIL recomputed_p" in run("verify-evidence", "bad.json", "--original", "orig.csv", "--predictions", "pred.npy",
                                        "--pubkey", "pub.json", code=1)
    orig.assign(temp=orig["temp"] + 0.01).to_csv("orig2.csv", index=False)       # not the signed original
    assert "FAIL original_matches_signed_root" in run("verify-evidence", "ev.json", "--original", "orig2.csv", "--predictions",
                                                      "pred.npy", "--pubkey", "pub.json", code=1)


def test_model_that_never_saw_the_data_is_not_claimed(tmp_path, monkeypatch):
    b, orig, delivered, rel, hk, q = setup(tmp_path, monkeypatch)
    other = make_df(BL * 60, seed=11)
    pred = predict({j: knn_memoriser(other[c].to_numpy(), L, H) for j, c in enumerate(["temp", "vib"])}, q)
    np.save("pred.npy", pred)
    ev = training_evidence(orig, rel, hk, q, pred)
    json.dump(ev, open("ev.json", "w"))
    out = run("verify-evidence", "ev.json", "--original", "orig.csv", "--predictions", "pred.npy", "--pubkey", "pub.json")
    assert "VERIFIED" in out and "not supported" in out


def test_regenerated_queries_match(tmp_path, monkeypatch):
    b, orig, delivered, rel, hk, q = setup(tmp_path, monkeypatch)
    ev = training_evidence(orig, rel, hk, q, np.zeros(q["fut"].shape), n_decoys=200)
    json.dump(ev, open("ev.json", "w"))
    run("holdout-queries", "orig.csv", "--evidence", "ev.json", "--out", "q.npz")
    assert np.array_equal(np.load("q.npz")["ctx"], q["ctx"])
