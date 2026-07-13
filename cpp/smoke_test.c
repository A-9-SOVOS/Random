#include "rrann.h"
#include <stdio.h>
#include <string.h>

int main(void) {
  double a = rrann_stream_seed(2.4, 0);
  double b = rrann_stream_seed(2.4, 1);
  printf("stream0=%.15g\n", a);
  printf("stream1=%.15g\n", b);
  if (a == b) {
    fprintf(stderr, "stream seeds should differ\n");
    return 1;
  }
  char commit[80];
  if (rrann_commit_seed(2.4, "demo", "s1", commit, sizeof commit) != 0) {
    fprintf(stderr, "commit failed\n");
    return 1;
  }
  printf("commit=%s\n", commit);
  if (rrann_verify_commit(commit, 2.4, "demo", "s1") != 1) {
    fprintf(stderr, "verify failed\n");
    return 1;
  }
  if (rrann_verify_commit(commit, 2.4, "other", "s1") != 0) {
    fprintf(stderr, "verify should reject\n");
    return 1;
  }

  double xf = rrann_extract_float(2.4, -1);
  printf("extract_float=%.15g\n", xf);
  if (!(xf >= 0.0 && xf < 1.0)) {
    fprintf(stderr, "extract_float out of range\n");
    return 1;
  }
  uint64_t bits = rrann_extract_u64(2.4, 32, 2);
  printf("extract_u64_32=0x%llx\n", (unsigned long long)bits);
  char digs[64];
  int dn = rrann_harvest_digits(2.4, 12, digs, sizeof digs);
  if (dn < 1) {
    fprintf(stderr, "harvest_digits failed\n");
    return 1;
  }
  printf("digits=%s diverge=%d\n", digs, rrann_divergence_index(2.4));

  printf("ok\n");
  return 0;
}
