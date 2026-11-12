import json

from conftest import make_df, fixed_bundle
from _helpers import run, write_pub, ssw_release, copy_evidence
from provenmark_verify import evidence as E
from provenmark_verify.io import read_table


def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    b = fixed_bundle("public-copy")
    write_pub(b, "pub.json")
    marked, rel, k = ssw_release(make_df(), b, "beta", ["temp", "vib"])
    marked.sample(frac=0.4, random_state=1).sort_index().to_csv("leak.csv", index=False)
    marked.to_csv("full.csv", index=False)
    ev = copy_evidence("leak.csv", rel, {"ssw": k})
    json.dump(ev, open("ev.json", "w"))
    return b, ev


def test_copy_evidence_verifies(tmp_path, monkeypatch):
    _, ev = setup(tmp_path, monkeypatch)
    assert ev["result"]["supported"]
    out = run("verify-evidence", "ev.json", "leak.csv", "--pubkey", "pub.json")
    assert "VERIFIED" in out and "claim supported" in out


def test_copy_evidence_tampering_is_detected(tmp_path, monkeypatch):
    _, ev = setup(tmp_path, monkeypatch)
    bad = json.loads(json.dumps(ev)); bad["result"]["methods"]["ssw"]["z"] += 5
    json.dump(bad, open("bad1.json", "w")); assert "FAIL recomputed_z:ssw" in run("verify-evidence", "bad1.json", "leak.csv", "--pubkey", "pub.json", code=1)
    bad = json.loads(json.dumps(ev)); bad["revealed_subkeys"]["ssw"] = "00" * 32
    json.dump(bad, open("bad2.json", "w")); assert "FAIL commitment:ssw" in run("verify-evidence", "bad2.json", "leak.csv", "--pubkey", "pub.json", code=1)
    bad = json.loads(json.dumps(ev)); bad["release_record"]["manifest"]["extra"]["license"] = {"x": 1}
    json.dump(bad, open("bad3.json", "w")); assert "FAIL release_signature" in run("verify-evidence", "bad3.json", "leak.csv", "--pubkey", "pub.json", code=1)
    assert "FAIL suspect_file_hash" in run("verify-evidence", "ev.json", "full.csv", "--pubkey", "pub.json", code=1)
    write_pub(fixed_bundle("someone-else"), "pub2.json")
    run("verify-evidence", "ev.json", "leak.csv", "--pubkey", "pub2.json", code=1)                  # other signer


def test_unmarked_copy_gives_no_claim(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    b = fixed_bundle("public-copy")
    _, rel, k = ssw_release(make_df(), b, "beta", ["temp", "vib"])
    make_df(seed=9).to_csv("clean.csv", index=False)
    ev = copy_evidence("clean.csv", rel, {"ssw": k})
    assert not ev["result"]["supported"]
    res = E.verify(ev, read_table("clean.csv", ["ts"]), ev["suspect_sha256"], b.public_key)
    assert res["verified"] and not res["claim_supported"]


def test_manifest_verification(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    from provenmark_verify import integrity
    b = fixed_bundle("public-copy")
    df = read_table("full.csv", ["ts"])
    json.dump(integrity.seal(df, b), open("m.json", "w"))
    run("verify-manifest", "full.csv", "--manifest", "m.json", "--pubkey", "pub.json", "--time-col", "ts")
    df.iloc[:100].to_csv("part.csv", index=False)
    run("verify-manifest", "part.csv", "--manifest", "m.json", "--time-col", "ts", code=1)


def test_forged_decision_is_rejected(tmp_path, monkeypatch):
    """The verifier recomputes the decision (p-values, Fisher, family-wise p, conclusion) instead of trusting it."""
    monkeypatch.chdir(tmp_path)
    b = fixed_bundle("public-copy")
    _, rel, k = ssw_release(make_df(), b, "beta", ["temp", "vib"])
    make_df(seed=9).to_csv("clean.csv", index=False)
    ev = copy_evidence("clean.csv", rel, {"ssw": k})
    ev["result"].update(familywise_p=1e-40, p_fisher=1e-40, supported=True)
    json.dump(ev, open("forged.json", "w"))
    write_pub(b, "pub.json")
    out = run("verify-evidence", "forged.json", "clean.csv", "--pubkey", "pub.json", code=1)
    assert "FAIL recomputed_conclusion" in out
    assert "NOT VERIFIED" in out and "not supported" in out


def test_unpinned_signer_is_not_verified(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    out = run("verify-evidence", "ev.json", "leak.csv", code=1)
    assert "FAIL signer_pinned" in out and "obtained independently" in out
