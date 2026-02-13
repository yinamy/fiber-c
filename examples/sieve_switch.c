// Cooperative calculation of primes
#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <fiber_switch.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_PRIMES_LIMIT 203280220

typedef struct {
  bool a;
  long int b;
} tuple;

static bool filter(int32_t my_prime,fiber_t caller) {
  bool divisible = false;
  int32_t candidate = (int32_t)(intptr_t)fiber_switch(caller, NULL, &caller);
  while (candidate > 0) {
    divisible = (candidate % my_prime) == 0;
    candidate = (int32_t)(intptr_t)fiber_switch(caller, (void*)(intptr_t)divisible, &caller);
  }
  return false;
}

static bool sanitise_input_number(const char *s) {
  for (; *s != '\0'; s++) {
    if (!isdigit(*s)) return false;
  }
  return true;
}

static void print_input_error_and_exit(void) {
  fprintf(stderr, "error: input must be a positive integer in the interval [1, %d]\n", MAX_PRIMES_LIMIT);
  exit(1);
}

void* run(void *arg, fiber_t caller) {
  tuple *t = (tuple *)arg;
  bool quiet = t->a;
  long int result = t->b;

  uint32_t max_primes = (uint32_t)result; // maximum number of primes to compute.
  uint32_t p = 0;                         // number of primes computed so far.
  int32_t i = 2;                          // the current candidate prime number.

  fiber_t *filters = (fiber_t*)malloc(sizeof(fiber_t) * max_primes);

  while (p < max_primes) {
    bool divisible = false;

    for (uint32_t j = 0; j < p; j++) {
      if (i==5 && j==1) {
        //printf("Switching to filter %u for candidate %d\n", j, i);
        if (&filters[j]) printf("Filter %u fiber pointer: %p\n", j, (void*)&filters[j]);
      }

      divisible = (bool)(intptr_t)fiber_switch(filters[j], (void*)(intptr_t)i, &filters[j]);
      if (divisible) break;
    }
    if (!divisible) {
      if (!quiet) {
        char sbuf[11]; // 10 digits + null character.
        int32_t len = snprintf(sbuf, sizeof(sbuf), "%" PRId32 " ", i);
        if (len < 1) {
          fprintf(stderr, "error: failed to convert int32_t to a string\n");
          abort();
        }
        for (int32_t i = 0; i < len; i++) {
          putc(sbuf[i], stdout);
        }
      }
      fiber_t filter_fiber = fiber_alloc((fiber_entry_point_t)(void*)filter);
      (void)fiber_switch(filter_fiber, (void*)(intptr_t)i, &filter_fiber);
      filters[p++] = filter_fiber;
    }
    i++;
  }
  if (!quiet) {
    putc('\n', stdout);
  }

  printf("Computed %u primes.\n", p);

  assert(p == max_primes);
  // Clean up
  for (uint32_t i = 0; i < p; i++) {
    (void)fiber_switch(filters[i], (void*)(intptr_t)0, &filters[i]);
    fiber_free(filters[i]);
  }
  free(filters);

  fiber_switch_return(caller, (void*)(intptr_t)0);

  return 0;
}

void *prog(int argc, char **argv) {

  size_t n_idx = argc == 2 ? 1 : 2;
  bool quiet = argc == 3 && strcmp(argv[1], "-q") == 0;

  if (!sanitise_input_number(argv[n_idx])) {
    print_input_error_and_exit();
  }

  errno = 0;
  long int result = strtol(argv[n_idx], NULL, 10 /* base 10 */);
  if (result <= 0 && (errno == ERANGE || errno == EINVAL || result > MAX_PRIMES_LIMIT)) {
    print_input_error_and_exit();
  }

  if (argc < 2 || argc > 3) {
    printf("usage: %s [-q] <n>\n", argv[0]);
    exit(1);
  }

  tuple t = {quiet, result};
  fiber_t run_fiber = fiber_alloc(run);
  int32_t fiber_result = (int32_t)(intptr_t)fiber_switch(run_fiber, &t, &run_fiber);
  fiber_free(run_fiber);
  return (void*)(intptr_t)fiber_result;
}

int main(int argc, char** argv) {

  int32_t const result = (int32_t)(intptr_t)fiber_main(prog, argc, argv);

  return result;
}

