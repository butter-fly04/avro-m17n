# Avro Phonetic for m17n

A port of the **Avro Phonetic** Bangla layout to a plain [m17n](https://www.nongnu.org/m17n/) input method file (`bn-avro-phonetic.mim`). It is a fixed layout: every character can be typed from keys alone, with **no dictionary, suggestions or autocorrect**.

```
ami avro diye borrno likhi   ->   আমি আভ্র দিয়ে বর্ন লিখি
```

Because it is an ordinary `.mim` file, it should work with any front end built on m17n-lib (ibus-m17n, fcitx5-m17n, ibus-typing-booster) without Qt or a separate engine.

> **Status:** the layout is verified against a reference implementation in the real m17n engine (see [Testing](#testing)). It has **not** been tried in ibus, fcitx5 or typing-booster. The install steps below are the usual m17n ones, not confirmed here.

## Files

| File | Purpose |
|---|---|
| `bn-avro-phonetic.mim` | The generated input method. This is the only file you need to use the layout. |
| `gen_mim.py` | Generator: reads `avrophonetic.json` and writes the `.mim`. |
| `avrophonetic.json` | Avro Phonetic rule set (patterns, vowel/consonant tables, context rules), copied from OpenBangla's `riti` engine. |
| `avro_ref.py` | Small reference implementation of the Avro algorithm, used as the oracle for tests. |
| `harness.c` | Test driver: feeds key strings into an m17n input method and prints the resulting text. |
| `difftest.py` | Word-level differential tests (m17n engine vs reference). |
| `difftest2.py` | Sentence-level and Backspace differential tests. |

## Install

1. Copy the file to your user m17n directory:

   ```sh
   mkdir -p ~/.m17n.d
   cp bn-avro-phonetic.mim ~/.m17n.d/
   ```

2. Install an m17n front end (for example `ibus-m17n` or `fcitx5-m17n`) and restart it.
3. Add the input method **bn:avro-phonetic** ("Bangla Avro Phonetic") in your input method settings.

If it does not appear, your m17n-lib may need an `mdb.dir` entry for the file. Check your distribution's m17n documentation. `~/.m17n.d/` is the standard location for user input methods.

## Regenerating the layout

```sh
python3 gen_mim.py bn-avro-phonetic.mim
```

Needs only Python 3 and the standard library. The output is deterministic: running it again produces an identical file. Do not edit the `.mim` by hand; change the generator or the rule JSON instead.

## How it works

Avro's rules look at only a little context: the **raw character before** a match and, for a few patterns, the **raw character after** it. That fits m17n well.

| Avro feature | m17n mechanism |
|---|---|
| Longest-match pattern lookup | The key-sequence trie in `(map ...)`. |
| Case normalisation (Avro lower-cases all letters except `oiudgjnrstyz`) | Every pattern is generated in all upper/lower variants of the letters Avro folds. |
| Prefix rules ("previous char is a consonant / vowel / punctuation / exactly `a`…") | **State machine.** There is one m17n state per class of the previous character: `init` (start or punctuation), `s1` vowel, `s2` `a`, `s3` `o`, `s4` consonant, `s5` `r`, `s6` `y`, `s7` `w`, `s8` `x`, `s9` `Z`. Each token ends with `(shift <state for the character just typed>)`. |
| Suffix rules ("next char is a vowel / a digit / not a backtick…") | One-key lookahead entries such as `rr`+consonant. They emit the token and `(pushback 1)` the lookahead key so it is processed again. |
| Prefixes that are not patterns (for example `kS` on the way to `kSh`) | Explicit fall-back entries that emit the shorter match and push the extra key back. |
| Backspace | `((BackSpace) (undo))`, as in khipro. It removes one raw key and re-converts, like Avro's word buffer. |

Context is carried by the **state**, not by variables, because variables did not survive between tokens in at least one real setup. Khipro also relies on states for this reason. The cost is size: each context has its own copy of every entry (about 7,850 entries, about 180 KB).

Behaviour notes:

* The current word stays in the underlined preedit until a delimiter. A space, Enter or any key that is not part of a pattern commits it.
* Tokens that end in punctuation or a digit return to `init`, which also commits.

## Testing

The tests run the generated `.mim` through the real m17n engine and compare the output with `avro_ref.py`:

* every pattern alone, and between 17 different neighbouring characters (about 81,000 strings)
* every 2- and 3-character string over the Avro alphabet (about 242,000)
* 300,000 random strings, including mixed case
* 60,000 random sentences with spaces, punctuation and digits
* 30,000 random Backspace sequences within a word
* a set of real sentences

At the time of writing, all of these match with 0 mismatches.

### What the tests do and do not prove

* They prove the `.mim` behaves like `avro_ref.py`. They do **not** prove `avro_ref.py` equals the original Avro Keyboard in every case.
* The reference was written from OpenBangla's rule data and `riti`'s matching code. It reproduces the examples in rupantor's documentation and the 30 test pairs taken from pyAvroPhonetic's suite. The rupantor source itself could not be read.
* Nothing here tests the ibus, fcitx5 or typing-booster front ends.

### Running the tests yourself

The harness links against m17n-lib. You need m17n-lib (with headers) and, ideally, m17n-db installed.

```sh
# build the harness (adjust flags to your system)
gcc harness.c -o harness $(pkg-config --cflags --libs m17n-shell)

# point the tests at it
export M17N_HARNESS=$PWD/harness
# only needed if m17n-db is not installed system-wide:
# export GLOBAL_MIM=/path/to/m17n-db/MIM/global.mim

python3 difftest.py
python3 difftest2.py
```

The `gcc` line is untested. The tests in this project were run against m17n-lib compiled by hand, and `pkg-config` names vary between distributions.

To try one input quickly (the file path must be absolute):

```sh
echo "ami avro diye borrno likhi" | ./harness "$PWD/bn-avro-phonetic.mim" bn avro-phonetic
```

## Limitations

* No dictionary, suggestions, autocomplete or autocorrect (intentionally).
* Only the **phonetic** Avro layout is covered.
* Front-end behaviour (preedit display, focus-out handling, Wayland quirks) depends on ibus, fcitx5 or typing-booster and was not tested.
* The file is large for an input method because of the state-per-context design.

## Credits and licensing

* **Avro Phonetic** was created by Mehdi Hasan Khan (OmicronLab). See [Avro-Keyboard](https://github.com/mugli/Avro-Keyboard).
* The rule data comes from [OpenBangla Keyboard](https://github.com/OpenBangla/OpenBangla-Keyboard)'s `riti` engine.
* The approach (a Bangla layout with complex context rules written as a pure m17n file, with states and an explicit Backspace binding) follows [khipro-m17n](https://github.com/rank-coder/khipro-m17n).
* **Licence .** since `avrophonetic.json` is copied from OpenBangla's repository and the generated `.mim` is derived from it. It's licensed under GPLV3.
