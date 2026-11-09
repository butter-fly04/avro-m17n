#!/usr/bin/env python3
"""Differential test: real m17n engine running bn-avro-phonetic.mim  vs  Avro reference."""
import os, random, subprocess, sys, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from avro_ref import Avro
A = Avro()
HARNESS = os.environ["M17N_HARNESS"]
MIM = os.path.join(HERE, "bn-avro-phonetic.mim")

def run_m17n(lines):
    inp = "\n".join(l + " " for l in lines) + "\n"   # terminator key (space) resolves any pending node
    p = subprocess.run([HARNESS, MIM, "bn", "avro-phonetic"], input=inp, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("harness failed: " + p.stderr[:300])
    out = p.stdout.split("\n")
    if out and out[-1] == "":
        out.pop()
    out = [o[:-1] if o.endswith(" ") else "<<NO-TRAILING-SPACE>>" + o for o in out]
    assert len(out) == len(lines), (len(out), len(lines))
    return out

def compare(name, lines, show=8):
    lines = [l for l in dict.fromkeys(lines) if l and "\n" not in l]
    got = []
    CH = 20000
    for i in range(0, len(lines), CH):
        got += run_m17n(lines[i:i+CH])
    bad = [(l, g, A.parse(l)) for l, g in zip(lines, got) if g != A.parse(l)]
    print(f"{name:34s} {len(lines)-len(bad):>7}/{len(lines):<7} ({100*(len(lines)-len(bad))/max(1,len(lines)):.3f}%)")
    for l, g, r in bad[:show]:
        print(f"    MISMATCH  keys={l!r}\n      m17n={g!r}\n      ref ={r!r}")
    return bad

if __name__ == "__main__":
    random.seed(int(os.environ.get("SEED", "1")))
    allbad = []
    pats = [f for f in A.pat if A.fix(f) == f]
    # 1. every pattern alone, with every single-char left/right neighbour
    nb = ["", "a", "e", "o", "O", "k", "r", "y", "w", "x", "Z", "`", " ", "1", ".", "A", "K"]
    allbad += compare("each pattern alone", pats)
    allbad += compare("pattern with 1 neighbour each side", [l + p + r for p in pats for l in nb for r in nb])
    # 2. exhaustive short strings over the Avro alphabet incl. uppercase variants
    alpha = sorted(set("".join(pats)) | set("AEKHBWQ x"))
    for n in (2, 3):
        allbad += compare(f"exhaustive len {n} ({len(alpha)} syms)", ["".join(t) for t in itertools.product(alpha, repeat=n)])
    # 3. random strings, pattern-weighted
    def rnd():
        return "".join(random.choice(pats) if random.random() < .6 else random.choice(alpha) for _ in range(random.randint(1, 8)))
    allbad += compare("random pattern-weighted x200k", [rnd() for _ in range(200000)])
    # 4. random pure-letter strings like real typing
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    allbad += compare("random letters x100k", ["".join(random.choice(letters) for _ in range(random.randint(1, 12))) for _ in range(100000)])
    print("TOTAL mismatches:", len(allbad))
