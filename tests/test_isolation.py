"""The public package must work without the full ProvenMark package: import every module with `provenmark`
blocked, and check statically that nothing imports it."""
import ast
import pathlib
import subprocess
import sys

import provenmark_verify

PKG = pathlib.Path(provenmark_verify.__file__).parent
BLOCK = """
import importlib.abc, sys
class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name == "provenmark" or name.startswith("provenmark."):
            raise ImportError("blocked: " + name)
sys.meta_path.insert(0, _Block())
"""


def _modules():
    for p in sorted(PKG.rglob("*.py")):
        rel = p.relative_to(PKG.parent).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts[-1] != "models":                 # needs the optional torch dependency
            yield ".".join(parts)


def test_no_import_of_full_package():
    for p in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text())):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
            for n in names:
                assert not (n == "provenmark" or n.startswith("provenmark.")), f"{p}: imports {n}"


def test_all_modules_import_with_full_package_blocked():
    code = BLOCK + "import importlib\n" + "".join(f"importlib.import_module({m!r})\n" for m in _modules())
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_no_embedding_engine_in_public_package():
    from provenmark_verify.methods import csw, evt, tone
    from provenmark_verify import holdout, evidence
    assert not hasattr(csw, "embed") and not hasattr(evt, "embed") and not hasattr(tone, "embed")
    assert not hasattr(holdout, "split_release") and not hasattr(holdout, "attribute")
    assert not hasattr(evidence, "build") and not hasattr(evidence, "build_training")
