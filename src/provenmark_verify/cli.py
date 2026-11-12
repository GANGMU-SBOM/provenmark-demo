# Public-package source: packaging/overlay/provenmark_verify/cli.py
"""provenmark-verify command line: third-party verification (no secret key) and a basic ssw trial.

Hand-written for the public package (packaging/overlay/); the logic of `verify-evidence` mirrors the full tool's
command of the same name so that evidence reports can point either at it or at this package.
"""
from __future__ import annotations

import json
import os
import sys

import click
import numpy as np

from . import __version__, core, evidence as evidence_mod, integrity
from .addressing import fit_address
from .io import default_out, read_table, write_table
from .keys import KeyBundle, commitment
from .methods import ssw

PARAMS_FORMAT = core.PARAMS_FORMAT


def _fmt_p(p):
    return "n/a" if p is None else f"{p:.3g}"


def _jdump(obj, path=None):
    s = json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    if path:
        with open(path, "w") as f:
            f.write(s)
    return s


def _pubkey(path):
    if not path:
        return None
    with open(path) as f:
        d = json.load(f)
    return bytes.fromhex(d["public_key"])


def _params(rec):
    try:
        return rec["manifest"]["extra"]["params"]
    except (KeyError, TypeError):
        raise click.ClickException("not a provenmark release record (manifest.extra.params missing)")


def _suspect(path, params):
    cols = params["address"].get("columns", []) if params["address"]["kind"] == "time" else []
    return read_table(path, cols)


def _print_checks(res):
    for c in res["checks"]:
        click.echo(f"  {'OK  ' if c['ok'] else 'FAIL'} {c['check']}" + (f"  ({c['note']})" if not c["ok"] and c.get("note") else ""))
    click.echo(f"evidence {'VERIFIED' if res['verified'] else 'NOT VERIFIED'}; claim "
               f"{'supported' if res['claim_supported'] else 'not supported'} (recomputed family-wise p = {_fmt_p(res['familywise_p'])})")


@click.group()
@click.version_option(__version__)
def main():
    """provenmark-verify: check ProvenMark evidence bundles and signed records without any secret key."""


@main.command("verify-evidence")
@click.argument("evidence_json", type=click.Path(exists=True))
@click.argument("suspect", type=click.Path(exists=True), required=False)
@click.option("--pubkey", type=click.Path(exists=True), help="Owner's public key JSON, obtained independently. Required for VERIFIED: without it the signer is not pinned")
@click.option("--original", type=click.Path(exists=True), help="Training evidence: the original data (all blocks)")
@click.option("--predictions", type=click.Path(exists=True), help="Training evidence: the suspect model's predictions (.npy)")
@click.option("--reference-seed", default=1, show_default=True, help="Training evidence: seed for the verifier's own reference model")
@click.option("--json", "as_json", is_flag=True, help="Print the full check list as JSON")
def verify_evidence(evidence_json, suspect, pubkey, original, predictions, reference_seed, as_json):
    """Recompute and check an evidence bundle (copy evidence or training evidence). Exit 0 = verified."""
    with open(evidence_json) as f:
        ev = json.load(f)
    fmt = ev.get("format")
    params = _params(ev.get("release_record"))
    pk = _pubkey(pubkey)
    if fmt == "provenmark.evidence-training/1":
        if not (original and predictions):
            raise click.ClickException("training evidence needs --original and --predictions")
        res = evidence_mod.verify_training(ev, _suspect(original, params), np.load(predictions, allow_pickle=False),
                                           pk, reference_seed=reference_seed)
    elif fmt == "provenmark.evidence/1":
        if not suspect:
            raise click.ClickException("copy evidence needs the SUSPECT file")
        res = evidence_mod.verify(ev, _suspect(suspect, params), core.suspect_digest(suspect), pk)
    else:
        raise click.ClickException(f"unknown evidence format {fmt!r}")
    click.echo(_jdump(res)) if as_json else _print_checks(res)
    sys.exit(0 if res["verified"] else 1)


@main.command("verify-manifest")
@click.argument("data", type=click.Path(exists=True))
@click.option("--manifest", required=True, type=click.Path(exists=True), help="Signed manifest or release record")
@click.option("--pubkey", type=click.Path(exists=True), help="Pin the expected signer (public key JSON)")
@click.option("--time-col", multiple=True, help="Parse as datetime when reading CSV")
def verify_manifest(data, manifest, pubkey, time_col):
    """Check a file against a signed manifest / release record; localises modified columns and row ranges."""
    with open(manifest) as f:
        rec = json.load(f)
    res = integrity.verify(read_table(data, list(time_col)), rec, _pubkey(pubkey))
    if not pubkey:
        click.echo("warning: no --pubkey: the signature was checked against the key embedded in the manifest only "
                   "(anyone can self-sign); pin the signer with --pubkey", err=True)
    click.echo(_jdump(res))
    sys.exit(0 if res["identical"] else 1)


@main.command("holdout-queries")
@click.argument("original", type=click.Path(exists=True))
@click.option("--evidence", "evidence_json", required=True, type=click.Path(exists=True),
              help="Training evidence bundle (query settings are taken from it)")
@click.option("--out", default="queries.npz", show_default=True)
def holdout_queries(original, evidence_json, out):
    """Regenerate the exact query windows of a training-evidence bundle, to re-query the suspect model yourself."""
    from . import holdout as ho
    with open(evidence_json) as f:
        ev = json.load(f)
    params = _params(ev["release_record"])
    qm = ev["queries"]
    q = ho.make_queries(_suspect(original, params), params["holdout"], qm["columns"], qm["context"], qm["horizon"],
                        qm["per_block"], qm["seed"])
    np.savez_compressed(out, ctx=q["ctx"], col=q["col"], block=q["block"], start=q["start"], meta=json.dumps(qm))
    click.echo(f"{len(q['ctx'])} query windows -> {out}; forecast each ctx row for {qm['horizon']} steps, save as "
               f"an array of shape ({len(q['ctx'])}, {qm['horizon']}) and pass it to verify-evidence --predictions")


# ---- basic ssw trial (evaluation only) --------------------------------------------------------------------------
@main.command()
@click.option("--out", required=True, type=click.Path(), help="Secret key file to create (never commit or share it)")
@click.option("--public-out", type=click.Path(), help="Write the public verification key (JSON) here")
def keygen(out, public_out):
    """Generate a key for the ssw trial (master secret + Ed25519 signing key)."""
    b = KeyBundle.generate()
    b.save(out)
    if public_out:
        _jdump({"format": "provenmark.pub/1", "key_id": b.key_id, "public_key": b.public_key.hex()}, public_out)
    click.echo(f"key id {b.key_id} written to {out}")


@main.command("ssw-mark")
@click.argument("data", type=click.Path(exists=True))
@click.option("--key", required=True, type=click.Path(exists=True))
@click.option("--recipient", required=True)
@click.option("--time-col", help="Timestamp column (else rows are addressed by position)")
@click.option("--columns", help="Comma list of float columns (default: all markable float columns)")
@click.option("--alpha", default=0.1, show_default=True, help="Strength (x local noise level)")
@click.option("--tol", multiple=True, help="Max abs error per column, e.g. temp=0.05")
@click.option("--out", type=click.Path())
def ssw_mark(data, key, recipient, time_col, columns, alpha, tol, out):
    """Basic ssw mark for EVALUATION: marked copy + signed record (provenmark.params/1 with an ssw commitment)."""
    b = KeyBundle.load(key)
    df = read_table(data, [time_col] if time_col else None)
    addr = fit_address(df, time_col)
    cols = columns.split(",") if columns else ssw.markable_columns(df, set(addr.address_columns))
    k = b.subkey("ssw", recipient)
    tol_d = {t.split("=", 1)[0]: float(t.split("=", 1)[1]) for t in tol}
    marked, info = ssw.embed(df, k, addr, cols, alpha, tol_d or None)
    out = out or default_out(data, f".{recipient}")
    write_table(marked, out)
    params = {"format": PARAMS_FORMAT, "tool": f"provenmark-verify {__version__}", "recipient": recipient,
              "address": addr.to_dict(), "columns": cols, "methods": {"ssw": {"columns": cols, "alpha": alpha}},
              "commitments": {"ssw": commitment(k)}}
    rec = integrity.seal(read_table(out, [time_col] if time_col else None), b, os.path.basename(out),
                         {"kind": "release", "params": params, "license": {"note": "evaluation"},
                          "parent_merkle_root": None})
    _jdump(rec, out + ".release.json")
    click.echo(f"marked -> {out}\nrecord -> {out}.release.json")
    for c, v in info.items():
        click.echo(f"  {c}: " + ", ".join(f"{a}={x:.4g}" if isinstance(x, float) else f"{a}={x}" for a, x in v.items()))


@main.command("ssw-detect")
@click.argument("suspect", type=click.Path(exists=True))
@click.option("--key", required=True, type=click.Path(exists=True))
@click.option("--release", required=True, type=click.Path(exists=True))
@click.option("--recipient", help="Override the recipient in the record")
@click.option("--alpha", default=1e-6, show_default=True)
@click.option("--max-shift", default=30, show_default=True, help="Also search +-N offsets (2 x min p); 0 = off")
def ssw_detect(suspect, key, release, recipient, alpha, max_shift):
    """Blind ssw detection with the key and the record (no original needed). Exit 0 = detected, 2 = not detected."""
    b = KeyBundle.load(key)
    with open(release) as f:
        params = _params(json.load(f))
    rcp = params["recipient"] if recipient is None else recipient
    if "ssw" not in params["methods"]:
        raise click.ClickException("record has no ssw parameters")
    k = b.subkey("ssw", rcp)
    if commitment(k) != params["commitments"].get("ssw"):
        raise click.ClickException(f"key/recipient does not match the commitment in the record (recipient '{rcp}')")
    r = core.detect_with_keys(_suspect(suspect, params), {"ssw": k}, params, max_shift)["ssw"]
    detected = r["p"] < alpha
    click.echo(f"ssw z={r['z']:.2f} p={r['p']:.2e} -> {'WATERMARK DETECTED' if detected else 'not detected'} (alpha {alpha:g})")
    sys.exit(0 if detected else 2)


if __name__ == "__main__":
    main()
