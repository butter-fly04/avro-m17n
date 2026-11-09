"""Reference implementation of the Avro Phonetic transliteration algorithm.

Semantics follow rupantor / riti (the engine used by OpenBangla Keyboard):
  * input is case-normalised: every letter is lowercased except the
    "case sensitive" letters listed in the rule file (oiudgjnrstyz)
  * at each position the longest `find` (max 5 chars) wins
  * for the matching pattern the first rule whose conditions ALL hold gives
    the replacement, otherwise the pattern's default replacement is used
  * prefix/suffix conditions look at ONE raw (normalised) character; outside
    the string counts as punctuation (but never as vowel/consonant/number)
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


class Avro:
    def __init__(self, path=None):
        d = json.load(open(path or os.path.join(HERE, "avrophonetic.json")))["layout"]
        self.vowel = set(d["vowel"])
        self.consonant = set(d["consonant"])
        self.number = set(d["number"])
        self.cs = set(d["casesensitive"])
        self.pat = {}
        for p in d["patterns"]:
            self.pat.setdefault(p["find"], p)      # first definition wins
        self.maxlen = max(len(k) for k in self.pat)

    # -- helpers -------------------------------------------------------
    def fix(self, s):
        return "".join(c if c.lower() in self.cs else c.lower() for c in s)

    def is_vowel(self, c):
        return c.lower() in self.vowel

    def is_cons(self, c):
        return c.lower() in self.consonant

    def is_punct(self, c):
        return not (self.is_vowel(c) or self.is_cons(c))

    def _match(self, m, t, start, end):
        scope = m["scope"]
        neg = scope.startswith("!")
        if neg:
            scope = scope[1:]
        prefix = m["type"] == "prefix"
        i = start - 1 if prefix else end
        inb = 0 <= i < len(t)
        if scope == "punctuation":
            r = True if not inb else self.is_punct(t[i])
        elif scope == "vowel":
            r = inb and self.is_vowel(t[i])
        elif scope == "consonant":
            r = inb and self.is_cons(t[i])
        elif scope == "number":
            r = inb and t[i] in self.number
        elif scope == "exact":
            v = m["value"]
            if prefix:
                a, b = start - len(v), start
            else:
                a, b = end, end + len(v)
            r = a >= 0 and b <= len(t) and t[a:b] == v
        else:
            raise ValueError(scope)
        return (not r) if neg else r

    def replacement(self, p, t, start, end):
        for rule in p["rules"]:
            if all(self._match(m, t, start, end) for m in rule["matches"]):
                return rule["replace"]
        return p["replace"]

    # -- main ----------------------------------------------------------
    def parse(self, text):
        t = self.fix(text)
        out = []
        cur = 0
        while cur < len(t):
            for l in range(min(self.maxlen, len(t) - cur), 0, -1):
                p = self.pat.get(t[cur:cur + l])
                if p is not None:
                    out.append(self.replacement(p, t, cur, cur + l))
                    cur += l
                    break
            else:
                out.append(t[cur])
                cur += 1
        return "".join(out)


if __name__ == "__main__":
    a = Avro()
    for line in sys.stdin:
        print(a.parse(line.rstrip("\n")))
