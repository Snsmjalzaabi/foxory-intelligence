/* Fixed, argument-free ABI/security regression probe. SPDX-License-Identifier: Apache-2.0 */
#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static pcre2_code *compile(const char *pattern, uint32_t flags) {
  int error; PCRE2_SIZE offset;
  pcre2_code *code = pcre2_compile((PCRE2_SPTR)pattern, PCRE2_ZERO_TERMINATED, flags, &error, &offset, NULL);
  if (!code) { fprintf(stderr, "PCRE2 compile failed: %d at %zu\n", error, offset); exit(1); }
  return code;
}

int main(int argc, char **argv) {
  (void)argv;
  if (argc != 1) return 64;
  char version[128]; uint32_t jit = 0, unicode = 0;
  if (pcre2_config(PCRE2_CONFIG_VERSION, version) < 0 || strncmp(version, "10.49 ", 6) != 0) return 1;
  if (pcre2_config(PCRE2_CONFIG_JIT, &jit) || jit != 1 || pcre2_config(PCRE2_CONFIG_UNICODE, &unicode) || unicode != 1) return 1;
  pcre2_match_data *data = pcre2_match_data_create(2000, NULL);
  pcre2_match_context *context = pcre2_match_context_create(NULL);
  if (!data || !context) return 1;
  pcre2_code *code = compile("caf\xc3\xa9", PCRE2_UTF | PCRE2_UCP);
  int rc = pcre2_match(code, (PCRE2_SPTR)"FOXORY caf\xc3\xa9", 12, 0, 0, data, context);
  pcre2_code_free(code);
  if (rc < 1) return 1;
  /* Upstream c932e704 regression: recursive DFA workspace exhaustion must fail safely. */
  code = compile("(*LIMIT_HEAP=4)(?=(?=(?=(?=(?=(?=(?=(?=a))(?R))))))).", 0);
  int workspace[1000];
  int dfa = pcre2_dfa_match(code, (PCRE2_SPTR)"a", 1, 0, 0, data, context, workspace, 1000);
  pcre2_code_free(code);
  if (dfa != PCRE2_ERROR_HEAPLIMIT) { fprintf(stderr, "Unexpected DFA result %d\n", dfa); return 1; }
  /* Upstream 2b403829 regression, expanded equivalent of testinput17's 1400 groups. */
  char pattern[20000] = "((?(DEFINE)";
  for (int i = 0; i < 1400; i++) strcat(pattern, "()\\g{-1}");
  strcat(pattern, ").{1}(?R)|)");
  code = compile(pattern, 0);
  if (pcre2_jit_compile(code, PCRE2_JIT_COMPLETE)) return 1;
  pcre2_jit_stack *stack = pcre2_jit_stack_create(32768, 192 * 1024, NULL);
  if (!stack) return 1;
  pcre2_jit_stack_assign(context, NULL, stack);
  int growable = pcre2_jit_match(code, (PCRE2_SPTR)"AAAAAA", 6, 0, 0, data, context);
  pcre2_jit_stack_free(stack); pcre2_code_free(code);
  pcre2_match_context_free(context); pcre2_match_data_free(data);
  if (growable != PCRE2_ERROR_JIT_STACKLIMIT) { fprintf(stderr, "Unexpected JIT result %d\n", growable); return 1; }
  printf("{\"version\":\"%s\",\"unicode\":true,\"jit\":true,\"dfa_error\":%d,\"jit_stack_error\":%d}\n", version, dfa, growable);
  return 0;
}
