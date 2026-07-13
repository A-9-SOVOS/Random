/*
 * Feed RRann binary dump (or live Python pipe) into TestU01 batteries.
 *
 * Build (after installing TestU01 to ~/.local/testu01):
 *   ./build_testu01_rrann.sh
 *
 * Usage:
 *   ./testu01_rrann smallcrush rrann_sts_1e6x1000.bin
 *   ./testu01_rrann crush     rrann_sts_1e6x1000.bin
 *   ./testu01_rrann bigcrush  rrann_sts_1e6x1000.bin   # hours; needs lots of numbers
 *   ./testu01_rrann rabbit    rrann_sts_1e6x1000.bin [nb_bits]
 *   ./testu01_rrann alphabit  rrann_sts_1e6x1000.bin [nb_bits]
 *
 * Binary file format: packed MSB-first bits (same as NIST STS binary input).
 * Each call returns one U01 float built from 32 consecutive bits.
 *
 * Notes on batteries (TestU01 Bbattery module):
 *   SmallCrush  — 10 tests, fast (~seconds–minutes)
 *   Crush       — 96 tests, slower
 *   BigCrush    — 106 tests, very slow; typically needs ~2^38 random numbers
 *   Rabbit      — bit-oriented; good for binary dumps
 *   Alphabit    — bit-oriented hardware-style tests
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#include "unif01.h"
#include "bbattery.h"

typedef struct {
    FILE *fp;
    const char *path;
    uint64_t words_read;
    int eof;
} FileState;

static FileState g_state;

static unsigned long read_u32_from_file(void *param, void *state)
{
    FileState *st = (FileState *)state;
    unsigned char b[4];
    size_t n;
    unsigned long w;

    (void)param;
    if (st->eof)
        return 0;

    n = fread(b, 1, 4, st->fp);
    if (n < 4) {
        /* Rewind and continue so long batteries can re-consume the file.
         * This is not ideal statistically (period = file length) but matches
         * common file-based TestU01 usage when the dump is finite.
         */
        if (st->words_read == 0) {
            fprintf(stderr, "ERROR: empty or unreadable file %s\n", st->path);
            st->eof = 1;
            return 0;
        }
        clearerr(st->fp);
        if (fseek(st->fp, 0L, SEEK_SET) != 0) {
            st->eof = 1;
            return 0;
        }
        n = fread(b, 1, 4, st->fp);
        if (n < 4) {
            st->eof = 1;
            return 0;
        }
    }

    /* Big-endian bit packing: first file byte is MSBs of first word */
    w = ((unsigned long)b[0] << 24) |
        ((unsigned long)b[1] << 16) |
        ((unsigned long)b[2] << 8) |
        ((unsigned long)b[3]);
    st->words_read++;
    return w;
}

static double read_u01_from_file(void *param, void *state)
{
    /* Map 32-bit word to [0,1) */
    return read_u32_from_file(param, state) * (1.0 / 4294967296.0);
}

static void write_file_state(void *state)
{
    FileState *st = (FileState *)state;
    printf(" RRann file generator: %s  words_read=%llu  eof=%d\n",
           st->path,
           (unsigned long long)st->words_read,
           st->eof);
}

static unif01_Gen *create_file_gen(const char *path)
{
    unif01_Gen *gen;
    size_t len;

    g_state.fp = fopen(path, "rb");
    if (!g_state.fp) {
        perror(path);
        return NULL;
    }
    g_state.path = path;
    g_state.words_read = 0;
    g_state.eof = 0;

    gen = malloc(sizeof(unif01_Gen));
    if (!gen)
        return NULL;

    gen->state = &g_state;
    gen->param = NULL;
    gen->Write = write_file_state;
    gen->GetU01 = read_u01_from_file;
    gen->GetBits = read_u32_from_file;

    len = strlen(path) + 32;
    gen->name = malloc(len);
    if (gen->name)
        snprintf(gen->name, len, "RRannFile(%s)", path);
    else
        gen->name = (char *)"RRannFile";

    return gen;
}

static void usage(const char *argv0)
{
    fprintf(stderr,
        "Usage: %s <battery> <binary_file> [nb_bits]\n"
        "  battery: smallcrush | crush | bigcrush | rabbit | alphabit | fips\n"
        "  binary_file: packed RRann bits (NIST STS binary format)\n"
        "  nb_bits: for rabbit/alphabit (default 2^25 = 33554432)\n",
        argv0);
}

int main(int argc, char **argv)
{
    unif01_Gen *gen;
    const char *battery;
    const char *path;
    double nb_bits = 33554432.0; /* 2^25 */

    if (argc < 3) {
        usage(argv[0]);
        return 1;
    }
    battery = argv[1];
    path = argv[2];
    if (argc >= 4)
        nb_bits = atof(argv[3]);

    gen = create_file_gen(path);
    if (!gen)
        return 1;

    printf("=== TestU01 Bbattery on RRann dump ===\n");
    printf("battery=%s file=%s\n", battery, path);
    gen->Write(gen->state);
    printf("\n");

    if (strcmp(battery, "smallcrush") == 0) {
        bbattery_SmallCrush(gen);
    } else if (strcmp(battery, "crush") == 0) {
        bbattery_Crush(gen);
    } else if (strcmp(battery, "bigcrush") == 0) {
        bbattery_BigCrush(gen);
    } else if (strcmp(battery, "rabbit") == 0) {
        bbattery_Rabbit(gen, nb_bits);
    } else if (strcmp(battery, "alphabit") == 0) {
        /* r=0, s=32 → use all bits of each 32-bit word */
        bbattery_Alphabit(gen, nb_bits, 0, 32);
    } else if (strcmp(battery, "fips") == 0) {
        bbattery_FIPS_140_2(gen);
    } else {
        usage(argv[0]);
        fclose(g_state.fp);
        return 1;
    }

    printf("\nDone. words_consumed=%llu\n",
           (unsigned long long)g_state.words_read);
    fclose(g_state.fp);
    free(gen->name);
    free(gen);
    return 0;
}
