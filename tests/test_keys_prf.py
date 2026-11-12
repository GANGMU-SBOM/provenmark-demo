# Copied from tests/test_keys_prf.py by packaging/export_public.py (imports rewritten).
import numpy as np, pytest
from provenmark_verify import prf
from provenmark_verify.keys import KeyBundle, derive, commitment


def test_prf_deterministic_random_access_and_balance():
    k = bytes(range(32))
    a = prf.prf_sign(k, 1, np.arange(100000))
    assert np.array_equal(a[500:510], prf.prf_sign(k, 1, np.arange(500, 510)))
    assert abs(a.mean()) < 0.02
    assert not np.array_equal(a[:100], prf.prf_sign(k, 2, np.arange(100)))        # domain separation
    assert not np.array_equal(a[:100], prf.prf_sign(bytes(32), 1, np.arange(100)))  # key dependence
    u = prf.prf_unit(k, 3, np.arange(50000))
    assert 0 <= u.min() and u.max() < 1 and abs(u.mean() - .5) < .01


def test_negative_and_large_indices():
    k = bytes(32)
    prf.prf_sign(k, 0, np.array([-5, 2 ** 62, -2 ** 62]))


def test_derive_independent_and_commitment(bundle):
    assert bundle.subkey("ssw", "a") != bundle.subkey("ssw", "b")
    assert bundle.subkey("ssw", "a") != bundle.subkey("tone", "a")
    assert commitment(bundle.subkey("ssw", "a")) == commitment(bundle.subkey("ssw", "a"))


def test_keyfile_roundtrip_encrypted_and_no_overwrite(tmp_path):
    b = KeyBundle.generate()
    p = str(tmp_path / "k")
    b.save(p, "pw")
    assert KeyBundle.load(p, "pw").master == b.master
    with pytest.raises(ValueError):
        KeyBundle.load(p)
    with pytest.raises(Exception):
        KeyBundle.load(p, "wrong")
    with pytest.raises(FileExistsError):
        b.save(p)
    p2 = str(tmp_path / "k2"); b.save(p2)
    assert KeyBundle.load(p2).key_id == b.key_id
    assert oct((tmp_path / "k2").stat().st_mode & 0o777) == "0o600"


def test_decoy_keys_derivation_is_frozen():
    """R4: decoy keys moved from audit to provenmark.decoys; the derivation is part of the evidence format (exact
    permutation p-values of cue / xc / xcue are recomputed by third parties), so it must never change."""
    import hashlib
    from provenmark_verify.decoys import decoy_keys
    assert decoy_keys(1, 0)[0] == hashlib.sha256(b"provenmark/decoy" + bytes(8) + bytes(8)).digest()
    g = hashlib.sha256(b"".join(decoy_keys(50, 7) + decoy_keys(5, 0) + decoy_keys(3, 2 ** 40))).hexdigest()
    assert g == "57879b80f412014e05dd964d09f2c8ddf2bcc0bcb438dd9bbc0e8c4be8582e23"
