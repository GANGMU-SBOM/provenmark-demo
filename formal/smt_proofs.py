"""Machine-checked (SMT, z3) proofs of the finite cores of docs/FORMAL.md.

Each lemma is stated for ALL real-valued inputs of the given size; z3 proves it by showing that the negation is
unsatisfiable. Sizes are bounded (the solver needs concrete dimensions), so these are proofs for every instance up to
the stated size, complementing the general pen-and-paper proofs in FORMAL.md.

  L1  rank lemma (T2, exact permutation p-value): for any m+1 reals s_0..s_m, the number of indices i whose
      p_i = (1 + #{j != i : s_j >= s_i}) / (1 + m) is <= k/(1+m) is at most k.  With exchangeable statistics the real
      key's index is uniform, so P(p <= k/(1+m)) <= k/(1+m): the test is valid.
  L2  conservation laws survive enforce() (P1-iii): if D' = s * D * P with P the null-space projector of a law a,
      then D' . a = 0 for every D and every row scale s.
  L3  tolerance after row scaling (P1-i): s = min(1, tol / |d|) gives |s d| <= tol, and s in [0, 1].
  L4  bounds after row scaling (P1-ii): if lo <= x <= hi and lo <= x + s* d <= hi, then for every s in [0, s*],
      lo <= x + s d <= hi (convexity), so shrinking never leaves the interval.
  L5  conditional test invariance (T3 / P5): the masked statistic does not depend on losses outside the mask.

python formal/smt_proofs.py        (prints PROVED / COUNTEREXAMPLE per lemma; exit 1 on any failure)
"""
import sys
import z3


def prove(name, claim, timeout_ms=120_000):
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    s.add(z3.Not(claim))
    r = s.check()
    status = "PROVED" if r == z3.unsat else "COUNTEREXAMPLE" if r == z3.sat else "UNKNOWN"
    print(f"{status:15s} {name}")
    if r == z3.sat:
        print("   ", s.model())
    return r == z3.unsat


def L1(m):
    s = z3.Reals(" ".join(f"s{i}" for i in range(m + 1)))
    ok = True
    for k in range(1, m + 2):
        # rank_i = 1 + #{j != i : s_j >= s_i};  p_i <= k/(1+m)  <=>  rank_i <= k
        ranks = [1 + z3.Sum([z3.If(s[j] >= s[i], 1, 0) for j in range(m + 1) if j != i]) for i in range(m + 1)]
        count = z3.Sum([z3.If(r <= k, 1, 0) for r in ranks])
        ok &= prove(f"L1 rank lemma, m={m}, k={k}", count <= k)
    return ok


def L2(n_cols=3):
    # law a = (1, 1, -1) (feed = a + b); projector P = I - a a^T / (a^T a); row d, scale s
    a = [1, 1, -1]
    aa = sum(x * x for x in a)
    P = [[(1 if i == j else 0) - z3.RealVal(a[i] * a[j]) / aa for j in range(n_cols)] for i in range(n_cols)]
    d = z3.Reals("d0 d1 d2")
    sc = z3.Real("scale")
    dp = [sc * z3.Sum([d[j] * P[i][j] for j in range(n_cols)]) for i in range(n_cols)]
    return prove("L2 conservation law preserved by projection + any row scaling", z3.Sum([dp[i] * a[i] for i in range(n_cols)]) == 0)


def L3():
    d, tol = z3.Reals("d tol")
    absd = z3.If(d >= 0, d, -d)
    sc = z3.If(absd > tol, tol / absd, 1)
    claim = z3.Implies(tol > 0, z3.And(z3.If(sc * d >= 0, sc * d, -sc * d) <= tol, sc >= 0, sc <= 1))
    return prove("L3 tolerance respected after row scaling", claim)


def L4():
    x, d, lo, hi, s_star, s = z3.Reals("x d lo hi s_star s")
    pre = z3.And(lo <= x, x <= hi, lo <= x + s_star * d, x + s_star * d <= hi, 0 <= s, s <= s_star)
    return prove("L4 bounds kept for every smaller scale (convexity)", z3.Implies(pre, z3.And(lo <= x + s * d, x + s * d <= hi)))


def L5(nb=6):
    # statistic of one assignment w restricted to mask m: mean(withheld & m) - mean(delivered & m)
    w = [z3.Bool(f"w{i}") for i in range(nb)]
    msk = [z3.Bool(f"m{i}") for i in range(nb)]
    l1 = z3.Reals(" ".join(f"a{i}" for i in range(nb)))
    l2 = z3.Reals(" ".join(f"b{i}" for i in range(nb)))

    def stat(l):
        na = z3.Sum([z3.If(z3.And(w[i], msk[i]), 1, 0) for i in range(nb)])
        nd = z3.Sum([z3.If(z3.And(z3.Not(w[i]), msk[i]), 1, 0) for i in range(nb)])
        sa = z3.Sum([z3.If(z3.And(w[i], msk[i]), l[i], 0) for i in range(nb)])
        sd = z3.Sum([z3.If(z3.And(z3.Not(w[i]), msk[i]), l[i], 0) for i in range(nb)])
        return na, nd, sa, sd
    na, nd, sa1, sd1 = stat(l1)
    _, _, sa2, sd2 = stat(l2)
    same_inside = z3.And([z3.Implies(msk[i], l1[i] == l2[i]) for i in range(nb)])
    # compare cross-multiplied means (no division): identical inside the mask => identical statistic
    claim = z3.Implies(z3.And(same_inside, na > 0, nd > 0),
                       z3.And(sa1 == sa2, sd1 == sd2))
    return prove(f"L5 masked statistic ignores blocks outside the mask (n_blocks={nb})", claim)


def sanity():
    """Non-vacuity: deliberately FALSE variants must be refuted, or the setup proves anything."""
    s_ = z3.Reals("t0 t1 t2 t3")
    ranks = [1 + z3.Sum([z3.If(s_[j] >= s_[i], 1, 0) for j in range(4) if j != i]) for i in range(4)]
    count = z3.Sum([z3.If(r <= 2, 1, 0) for r in ranks])
    s1 = z3.Solver(); s1.add(z3.Not(count <= 1))                      # false: up to 2 can rank in the top 2
    d, tol = z3.Reals("dd tt")
    s2 = z3.Solver(); s2.add(z3.Not(z3.Implies(tol > 0, d <= tol)))     # false without the scaling
    ok = s1.check() == z3.sat and s2.check() == z3.sat
    print(f"{'OK' if ok else 'FAILED':15s} sanity: false variants are refuted")
    return ok


if __name__ == "__main__":
    ok = sanity()
    for m in (1, 2, 3, 4, 5, 6, 7):
        ok &= L1(m)
    ok &= L2() & L3() & L4() & L5()
    print("ALL PROVED" if ok else "SOME LEMMA NOT PROVED")
    sys.exit(0 if ok else 1)
