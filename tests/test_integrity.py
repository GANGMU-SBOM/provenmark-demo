# Copied from tests/test_integrity.py by packaging/export_public.py (imports rewritten).
import copy, numpy as np
from provenmark_verify import integrity as I
from provenmark_verify.io import read_table, write_table
from provenmark_verify.keys import KeyBundle


def test_csv_parquet_same_root(tmp_path, df):
    write_table(df, str(tmp_path / "a.csv")); write_table(df, str(tmp_path / "a.parquet"))
    r1 = I.fingerprint(read_table(str(tmp_path / "a.csv"), ["ts"]))["merkle_root"]
    r2 = I.fingerprint(read_table(str(tmp_path / "a.parquet")))["merkle_root"]
    assert r1 == r2 == I.fingerprint(df)["merkle_root"]


def test_seal_verify_and_localise(bundle, df):
    s = I.seal(df, bundle)
    assert I.verify(df, s)["identical"]
    d = df.copy(); d.loc[5000, "temp"] += 1e-9
    r = I.verify(d, s)
    assert not r["identical"] and r["signature_valid"]
    assert r["columns_modified"] == ["temp"] and r["modified_row_ranges"] == [[4096, 5119]]


def test_signature_tamper_and_wrong_signer(bundle, df):
    s = I.seal(df, bundle)
    t = copy.deepcopy(s); t["manifest"]["dataset"]["rows"] += 1
    assert not I.verify_manifest_signature(t)
    other = KeyBundle.generate()
    assert not I.verify_manifest_signature(s, other.public_key)
    assert I.verify_manifest_signature(s, bundle.public_key)


def test_row_order_and_nan_and_negzero():
    import pandas as pd
    a = pd.DataFrame({"x": [0.0, np.nan, 1.5], "s": ["a", None, "c"]})
    b = pd.DataFrame({"x": [-0.0, np.nan, 1.5], "s": ["a", None, "c"]})
    assert I.fingerprint(a)["merkle_root"] == I.fingerprint(b)["merkle_root"]
    assert I.fingerprint(a)["merkle_root"] != I.fingerprint(a.iloc[::-1].reset_index(drop=True))["merkle_root"]


def test_row_index_scan_finds_shuffled_subset(bundle, df):
    k = bundle.subkey("rowindex")
    idx = I.row_index(df, k)
    sus = df.sample(frac=0.3, random_state=1)
    r = I.scan_overlap(sus, idx, k, list(df.columns))
    assert r["fraction"] == 1.0
    noisy = sus.copy(); noisy["temp"] += 1e-6
    assert I.scan_overlap(noisy, idx, k, list(df.columns))["fraction"] == 0.0
    assert I.scan_overlap(sus, idx, bundle.subkey("other"), list(df.columns))["fraction"] == 0.0
