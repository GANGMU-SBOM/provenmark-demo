# Copied from tests/conftest.py by packaging/export_public.py (imports rewritten).
import numpy as np, pandas as pd, pytest
from provenmark_verify.keys import KeyBundle


def fixed_bundle(label: str = "provenmark-tests") -> KeyBundle:
    """Deterministic key so unit tests are reproducible. Statistical calibration (false-positive rates) is
    tested separately with many random keys (test_null_* tests, bench/r2/null_calibration.py); a single-draw
    unit test must not assert e.g. 'null p > 0.05', which fails 5% of the time by construction."""
    import hashlib
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    h = lambda s: hashlib.sha256((label + s).encode()).digest()
    return KeyBundle(h("/master"), Ed25519PrivateKey.from_private_bytes(h("/signing")))


@pytest.fixture(scope="session")
def bundle():
    return fixed_bundle()


def make_df(n=20000, seed=0, freq="1s"):
    r = np.random.default_rng(seed)
    i = np.arange(n)
    return pd.DataFrame({
        "ts": pd.date_range("2025-01-01", periods=n, freq=freq, tz="UTC"),
        "temp": 60 + 3 * np.sin(i / 2000) + np.cumsum(r.normal(size=n)) * 0.01 + r.normal(size=n) * 0.3,
        "vib": np.abs(r.normal(2, 0.4, n)),
        "state": r.integers(0, 3, n)})


@pytest.fixture(scope="session")
def df():
    return make_df()
