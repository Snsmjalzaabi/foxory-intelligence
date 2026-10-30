/* Argument-free loaded-library probe; no X server or untrusted replies. SPDX-License-Identifier: Apache-2.0 */
#define _GNU_SOURCE
#include <X11/Xlib.h>
#include <X11/extensions/Xrender.h>
#include <dlfcn.h>
#include <stdio.h>
int main(int argc,char **argv) {
    (void)argv; if (argc!=1) return 64;
    Dl_info info;
    if (!dladdr((void *)XRenderQueryFormats,&info) || !info.dli_fname) return 1;
    printf("{\"symbol\":\"XRenderQueryFormats\",\"loaded_path\":\"%s\"}\n",info.dli_fname);
    return 0;
}
