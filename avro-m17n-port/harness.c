/* Feed key strings to an m17n input method; print committed+preedit text per line.
   usage: harness file.mim lang name < lines   (each line = keys; '\n' ends the test; 'BS' not supported here)
   Special: a literal "<BS>" in a line is a backspace key. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <m17n.h>

static void append_mt(char *out, size_t *n, MText *mt) {
  if (!mt) return;
  int len = mtext_len(mt);
  for (int i = 0; i < len; i++) {
    int c = mtext_ref_char(mt, i);
    char b[8]; int k = 0;
    if (c < 0x80) b[k++] = c;
    else if (c < 0x800) { b[k++] = 0xC0|(c>>6); b[k++] = 0x80|(c&63); }
    else if (c < 0x10000) { b[k++] = 0xE0|(c>>12); b[k++] = 0x80|((c>>6)&63); b[k++] = 0x80|(c&63); }
    else { b[k++] = 0xF0|(c>>18); b[k++] = 0x80|((c>>12)&63); b[k++] = 0x80|((c>>6)&63); b[k++] = 0x80|(c&63); }
    memcpy(out + *n, b, k); *n += k;
  }
}

int main(int argc, char **argv) {
  if (argc < 4) { fprintf(stderr, "usage\n"); return 2; }
  M17N_INIT();
  minput_open_im(msymbol("zz"), msymbol("zz"), NULL); /* force lazy init so Minput_method is set */
  { char *g = getenv("GLOBAL_MIM"); if (g) mdatabase_define(Minput_method, Mt, Mnil, msymbol("global"), NULL, g); }
  MSymbol lang = msymbol(argv[2]), name = msymbol(argv[3]);
  mdatabase_define(Minput_method, lang, name, Mnil, NULL, argv[1]);
  MInputMethod *im = minput_open_im(lang, name, NULL);
  if (!im) { fprintf(stderr, "cannot open im (merror=%d)\n", merror_code); return 1; }
  int verbose = argc > 4;
  char line[4096];
  while (fgets(line, sizeof line, stdin)) {
    size_t L = strlen(line); if (L && line[L-1] == '\n') line[--L] = 0;
    MInputContext *ic = minput_create_ic(im, NULL);
    char *out = calloc(1, 65536); size_t n = 0;
    MText *committed = mtext();
    for (size_t i = 0; i < L; ) {
      MSymbol key;
      char kb[16];
      if (!strncmp(line + i, "<BS>", 4)) { key = msymbol("BackSpace"); i += 4; }
      else { kb[0] = line[i]; kb[1] = 0; i++; key = msymbol(kb); }
      int r = minput_filter(ic, key, NULL);
      MText *mt = mtext();
      int r2 = minput_lookup(ic, key, NULL, mt);
      /* mt holds text committed by this key */
      mtext_cat(committed, mt);
      m17n_object_unref(mt);
      if (r2 == -1) {
        /* key not handled by IM: application inserts the key itself */
        if (strcmp(msymbol_name(key), "BackSpace")) { mtext_cat_char(committed, (unsigned char)kb[0]); }
        else if (mtext_len(committed) > 0) mtext_del(committed, mtext_len(committed)-1, mtext_len(committed));
      }
      if (verbose) {
        size_t m = 0; char tmp[4096]; memset(tmp,0,sizeof tmp);
        append_mt(tmp, &m, ic->preedit);
        fprintf(stderr, "  key=%s filter=%d lookup=%d preedit=[%s]\n", msymbol_name(key), r, r2, tmp);
      }
    }
    append_mt(out, &n, committed);
    append_mt(out, &n, ic->preedit);
    out[n] = 0;
    puts(out);
    free(out);
    m17n_object_unref(committed);
    minput_destroy_ic(ic);
  }
  minput_close_im(im);
  M17N_FINI();
  return 0;
}
