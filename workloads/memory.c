#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t state = 0x12345678;
static uint32_t random32(void) {
    state ^= state << 13; state ^= state >> 17; state ^= state << 5;
    return state;
}
static int ascending(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    char *end = NULL;
    errno = 0;
    long parsed = strtol(argv[2], &end, 10);
    if (errno || end == argv[2] || *end || parsed < 2 || parsed > 262144) return 2;
    size_t n = (size_t)parsed;
    uint64_t *data = malloc(n * sizeof(*data));
    size_t *order = malloc(n * sizeof(*order)), *next = malloc(n * sizeof(*next));
    if (!data || !order || !next) { free(data); free(order); free(next); return 3; }
    for (size_t i = 0; i < n; ++i) { data[i] = i; order[i] = i; }
    for (size_t i = n - 1; i > 0; --i) {
        size_t j = random32() % (i + 1), t = order[i]; order[i] = order[j]; order[j] = t;
    }
    uint64_t sum = 0, expected = (uint64_t)n * (n-1) / 2;
    if (!strcmp(argv[1], "sequential")) {
        for (size_t i = 0; i < n; ++i) sum += data[i];
    } else if (!strcmp(argv[1], "random")) {
        for (size_t i = 0; i < n; ++i) sum += data[order[i]];
    } else if (!strcmp(argv[1], "traversal")) {
        for (size_t offset = 0; offset < 64; ++offset)
            for (size_t i = offset; i < n; i += 64) sum += data[i];
    } else if (!strcmp(argv[1], "pointer")) {
        for (size_t i = 0; i < n; ++i) next[order[i]] = order[(i+1)%n];
        size_t cursor = order[0];
        for (size_t i = 0; i < n; ++i) { sum += data[cursor]; cursor = next[cursor]; }
        if (cursor != order[0]) { free(data); free(order); free(next); return 1; }
    } else if (!strcmp(argv[1], "sorting")) {
        for (size_t i = 0; i < n; ++i) data[i] = n-i;
        qsort(data, n, sizeof(*data), ascending);
        for (size_t i = 0; i < n; ++i) {
            if (data[i] != i+1) { free(data); free(order); free(next); return 1; }
            sum += data[i];
        }
        expected = (uint64_t)n * (n+1) / 2;
    } else { free(data); free(order); free(next); return 2; }
    free(data); free(order); free(next);
    if (sum != expected) { fprintf(stderr, "checksum mismatch\n"); return 1; }
    printf("BENCHMARK_OK %s n=%zu checksum=%" PRIu64 "\n", argv[1], n, sum);
    return 0;
}
