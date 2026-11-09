#!/usr/bin/env python3
"""Generate an m17n input method (bn-avro-phonetic.mim) from Avro Phonetic rules.

Context handling
  * prefix conditions  -> variable P (class of the previous raw character)
  * suffix conditions  -> one-key lookahead entries ("<pattern><key>") that
                          emit the token and push the key back
  * case normalisation -> every pattern is emitted in all upper/lower variants
                          of the letters Avro lower-cases
  * longest match      -> native m17n trie; non-pattern prefix nodes get explicit
                          fall-back entries
"""
import itertools, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from avro_ref import Avro

A = Avro()
CS = A.cs
CLASS_REPR = {0: None, 1: 'e', 2: 'a', 3: 'o', 4: 'k', 5: 'r', 6: 'y', 7: 'w', 8: 'x', 9: 'Z'}

def cls(ch):
    if ch == 'a': return 2
    if ch == 'o': return 3
    if ch == 'r': return 5
    if ch == 'y': return 6
    if ch == 'w': return 7
    if ch == 'x': return 8
    if ch == 'Z': return 9
    if A.is_vowel(ch): return 1
    if A.is_cons(ch): return 4
    return 0

# sanity: every 'exact' value used by rules must have its own class
exacts = {m["value"] for p in A.pat.values() for r in p["rules"] for m in r["matches"]
          if m["scope"].lstrip('!') == "exact" and m["type"] == "prefix"}
assert exacts <= set("aorywxZ"), exacts
sexacts = {m["value"] for p in A.pat.values() for r in p["rules"] for m in r["matches"]
           if m["scope"].lstrip('!') == "exact" and m["type"] == "suffix"}

# only patterns that survive case normalisation can ever match
PAT = {f: p for f, p in A.pat.items() if A.fix(f) == f}

def ctx_out(p, c, nxt):
    """Replacement for pattern p with previous-class c and next normalised char nxt (None=end)."""
    pre = CLASS_REPR[c]
    t = (pre or "") + p["find"] + (nxt or "")
    s = len(pre or "")
    return A.replacement(p, t, s, s + len(p["find"]))

def esc(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def out_expr(outs):
    """outs: {class: text} -> m17n action list text"""
    groups = {}
    for c, o in outs.items():
        groups.setdefault(o, []).append(c)
    if len(groups) == 1:
        o = next(iter(groups))
        return esc(o) if o else ""
    # largest group becomes the default
    items = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    clauses = []
    for o, cl in items[1:]:
        cond = " ".join(f"(= P {c})" for c in sorted(cl))
        cond = f"(| {cond})" if len(cl) > 1 else cond
        clauses.append(f"({cond} {esc(o) if o else chr(34)*2})")
    d = items[0][0]
    clauses.append(f"(1 {esc(d) if d else chr(34)*2})")
    return "(cond " + " ".join(clauses) + ")"

def raw_keys(n):
    """raw keys that normalise to n"""
    ks = {n}
    if n.isalpha() and n.lower() == n and n not in CS and n.upper() != n:
        ks.add(n.upper())
    return sorted(ks)

def variants(f):
    opts = []
    for ch in f:
        if ch.isalpha() and ch.islower() and ch not in CS:
            opts.append((ch, ch.upper()))
        else:
            opts.append((ch,))
    return ["".join(v) for v in itertools.product(*opts)]

NEXT_ALPHABET = [None] + [chr(c) for c in range(32, 127)]
NEXT_ALPHABET = [n for n in NEXT_ALPHABET if n is None or A.fix(n) == n]


CLASSES = sorted(CLASS_REPR)
SNAME = {0: "init", **{c: f"s{c}" for c in CLASSES if c}}
entries = {}      # (mapname, rawkeyseq) -> action text
conflicts = []
maps_used = {}    # mapname -> (state_class c, dest_class q, fallback_raw or None)

def put(mapname, seq, actions):
    k = (mapname, seq)
    if k in entries and entries[k] != actions:
        conflicts.append(k); return
    entries[k] = actions

def lit(o):
    return esc(o)   # an empty output must stay an explicit "" action, otherwise m17n echoes the raw key

pat_prefixes = set()
for f in PAT:
    for i in range(1, len(f) + 1):
        pat_prefixes.add(f[:i])

for f, p in sorted(PAT.items()):
    q = cls(f[-1])
    base = {c: ctx_out(p, c, None) for c in CLASSES}
    look = {}
    for n in NEXT_ALPHABET[1:]:
        o = {c: ctx_out(p, c, n) for c in CLASSES}
        if o != base:
            look[n] = o
    for c in CLASSES:
        mn = f"m{c}_{q}"; maps_used[mn] = (c, q, None)
        for v in variants(f):
            put(mn, v, lit(base[c]))
        for n, o in look.items():
            if f + n in pat_prefixes:
                continue
            for k in raw_keys(n):
                for v in variants(f):
                    put(mn, v + k, f"{lit(o[c])} (pushback 1)")

allseq = set(); patseq = {v for f in PAT for v in variants(f)}
for f in PAT:
    for v in variants(f):
        for i in range(1, len(v) + 1):
            allseq.add(v[:i])
for w in sorted(allseq - patseq):
    wn = A.fix(w)
    k = max((i for i in range(1, len(wn) + 1) if wn[:i] in PAT), default=0)
    if k == 0:
        conflicts.append(("nofallback", w)); continue
    p = PAT[wn[:k]]
    rem_norm, rem_raw = wn[k:], w[k:]
    q = cls(wn[k-1])
    for c in CLASSES:
        o = ctx_out(p, c, rem_norm[0])
        mn = f"f{c}_{q}_" + "_".join(f"{ord(ch):x}" for ch in rem_raw)
        maps_used[mn] = (c, q, rem_raw)
        put(mn, w, lit(o))


out = []
out.append(';; bn-avro-phonetic.mim -- Avro Phonetic (fixed layout, no dictionary) for m17n')
out.append(';; GENERATED by gen_mim.py from avrophonetic.json (OpenBangla riti rule set). Do not edit by hand.')
out.append(';; Context (class of the previous raw character) is carried by the m17n STATE, not by variables:')
out.append(';;   init=start/punctuation  s1=vowel  s2=a  s3=o  s4=consonant  s5=r  s6=y  s7=w  s8=x  s9=Z')
out.append('(input-method bn avro-phonetic)')
out.append('(description "Avro Phonetic for Bangla (fixed layout, no dictionary)")')
out.append('(title "অ")')
out.append('(map')
byname = {}
for (mn, seq), act in sorted(entries.items()):
    byname.setdefault(mn, []).append((seq, act))
for mn in sorted(byname):
    out.append(f" ({mn}")
    for seq, act in byname[mn]:
        out.append(f"  ({esc(seq)} {act})".replace(" )", ")"))
    out.append(" )")
out.append(" (backspace")
out.append("  ((BackSpace) (undo))")
out.append(" )")
out.append(")")
out.append("(state")
for c in CLASSES:
    out.append(f" ({SNAME[c]}")
    out.append("  (backspace)")
    for mn in sorted(byname):
        cc, q, rem = maps_used[mn]
        if cc != c: continue
        acts = (f"(pushback {esc(rem)}) " if rem else "") + f"(shift {SNAME[q]})"
        out.append(f"  ({mn} {acts})")
    out.append(" )")
out.append(")")
open(sys.argv[1] if len(sys.argv) > 1 else "bn-avro-phonetic.mim", "w").write("\n".join(out) + "\n")
print("entries:", len(entries), "maps:", len(byname), "conflicts:", len(conflicts), conflicts[:5])
