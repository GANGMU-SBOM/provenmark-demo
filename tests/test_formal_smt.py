# Copied from tests/test_formal_smt.py by packaging/export_public.py (imports rewritten).
import subprocess, sys, os
import pytest

z3 = pytest.importorskip("z3")


def test_smt_proofs_hold():
    """formal/smt_proofs.py: every lemma PROVED and the false variants refuted."""
    root = os.path.dirname(os.path.dirname(__file__))
    r = subprocess.run([sys.executable, os.path.join(root, "formal", "smt_proofs.py")], capture_output=True, text=True,
                       timeout=1800)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ALL PROVED" in r.stdout and "COUNTEREXAMPLE" not in r.stdout and "UNKNOWN" not in r.stdout
