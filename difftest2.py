#!/usr/bin/env python3
"""Sentence-level and Backspace differential tests (m17n engine vs Avro reference)."""
import os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from avro_ref import Avro
A = Avro(); H = os.environ["M17N_HARNESS"]; MIM = os.path.join(HERE, "bn-avro-phonetic.mim")
def run(lines):
    p = subprocess.run([H, MIM, "bn", "avro-phonetic"], input="\n".join(l + " " for l in lines) + "\n", capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[:200]
    out = p.stdout.split("\n")[:len(lines)]
    return [o[:-1] if o.endswith(" ") else "<<NOSPACE>>" + o for o in out]
random.seed(7)
pats = [f for f in A.pat if A.fix(f) == f]
letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
def word(): return "".join(random.choice(pats) if random.random() < .5 else random.choice(letters) for _ in range(random.randint(1, 7)))
seps = [" ", " ", " ", ", ", ". ", "  ", "-", "? ", "; ", "(", ")", "1", "2.5 "]
def sentence():
    return "".join(word() + random.choice(seps) for _ in range(random.randint(2, 9))) + word()
S = [sentence() for _ in range(60000)]
got = run(S); bad = [(s, g, A.parse(s)) for s, g in zip(S, got) if g != A.parse(s)]
print(f"sentences (words+punct+digits)   {len(S)-len(bad)}/{len(S)}")
for s, g, r in bad[:5]: print("  MISMATCH", repr(s), "\n    m17n", repr(g), "\n    ref ", repr(r))
# real sentences
real = ["ami banglay gan gai", "ami avro diye borrno likhi", "amar sonar bangla, ami tomay valobasi",
        "o amar desher mati, tomar 'ponor' thekai matha nato kore dao he", "rabindranath thakur",
        "bishshobidyaloy", "ekhane ki hocche? kichu bujhte parchhi na!", "kSoma koro, ami bujhte parini",
        "Ami bhat khai, tumi ki khao?", "2026 sale 15 tarikh 3.5 taka", "kemon acho? bhalo achi, dhonnobad"]
for r, g in zip(real, run(real)): 
    print("OK " if g == A.parse(r) else "BAD", r, "->", g)
# Backspace: keys with <BS> inside ONE word; expectation = parse(raw buffer after deletions)
def with_bs():
    buf = []; keys = ""
    for _ in range(random.randint(3, 12)):
        if buf and random.random() < .3:
            buf.pop(); keys += "<BS>"
        else:
            c = random.choice(pats) if random.random() < .4 else random.choice(letters)
            buf.append(c); keys += c
    return keys, "".join(buf)
def expand(buf):  # list-of-tokens -> raw; BS removes ONE raw key, so track per key
    pass
def with_bs_rawkeys():
    buf = []; keys = ""
    for _ in range(random.randint(3, 14)):
        if buf and random.random() < .3:
            buf.pop(); keys += "<BS>"
        else:
            c = random.choice(letters); buf.append(c); keys += c
    return keys, "".join(buf)
T = [with_bs_rawkeys() for _ in range(30000)]
got = run([k for k, _ in T]); bad = [(k, g, A.parse(e)) for (k, e), g in zip(T, got) if g != A.parse(e)]
print(f"Backspace mid-word (raw-key undo)  {len(T)-len(bad)}/{len(T)}")
for k, g, r in bad[:6]: print("  MISMATCH keys", repr(k), "\n    m17n", repr(g), "\n    ref ", repr(r))
