/* Deterministic integer i-j-k matrix multiply. Every output is validated using
 * an independent closed-form sum, avoiding a second O(n^3) reference multiply. */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: matrix SIZE (2..128)\n"); return 2; }
    char *end = NULL;
    errno = 0;
    long parsed = strtol(argv[1], &end, 10);
    if (errno || end == argv[1] || *end || parsed < 2 || parsed > 128) return 2;
    size_t n = (size_t)parsed;
    uint64_t *a = calloc(n*n, sizeof(*a));
    uint64_t *b = calloc(n*n, sizeof(*b));
    uint64_t *c = calloc(n*n, sizeof(*c));
    if (!a || !b || !c) { free(a); free(b); free(c); return 3; }
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < n; ++j) {
            a[i*n+j] = i + j + 1;
            b[i*n+j] = 2*i + j + 1;
        }
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < n; ++j)
            for (size_t k = 0; k < n; ++k)
                c[i*n+j] += a[i*n+k] * b[k*n+j];
    uint64_t checksum = 0;
    uint64_t s1 = n*(n-1)/2, s2 = n*(n-1)*(2*n-1)/6;
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < n; ++j) {
            uint64_t expected = 2*s2 + (2*(i+1)+j+1)*s1 + n*(i+1)*(j+1);
            if (c[i*n+j] != expected) {
                fprintf(stderr, "validation failed at %zu,%zu\n", i, j);
                free(a); free(b); free(c); return 1;
            }
            checksum += c[i*n+j];
        }
    printf("MATRIX_OK n=%zu checksum=%" PRIu64 "\n", n, checksum);
    free(a); free(b); free(c);
    return 0;
}
