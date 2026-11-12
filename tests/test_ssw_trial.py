import json

import pandas as pd

from conftest import make_df
from _helpers import run


def test_ssw_trial_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_df().to_csv("d.csv", index=False)
    run("keygen", "--out", "k.pmkey", "--public-out", "pub.json")
    run("ssw-mark", "d.csv", "--key", "k.pmkey", "--recipient", "acme", "--time-col", "ts", "--columns", "temp,vib")
    rel = json.load(open("d.acme.csv.release.json"))
    assert rel["manifest"]["extra"]["params"]["format"] == "provenmark.params/1"
    d = pd.read_csv("d.acme.csv").iloc[3000:15000]
    d.to_csv("crop.csv", index=False)
    assert "WATERMARK DETECTED" in run("ssw-detect", "crop.csv", "--key", "k.pmkey", "--release", "d.acme.csv.release.json")
    run("ssw-detect", "d.csv", "--key", "k.pmkey", "--release", "d.acme.csv.release.json", code=2)       # unmarked
    run("ssw-detect", "crop.csv", "--key", "k.pmkey", "--release", "d.acme.csv.release.json", "--recipient", "beta",
        code=1)                                                                                         # wrong recipient
    run("verify-manifest", "d.acme.csv", "--manifest", "d.acme.csv.release.json", "--pubkey", "pub.json",
        "--time-col", "ts")
