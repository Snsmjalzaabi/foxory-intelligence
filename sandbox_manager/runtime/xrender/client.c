/* Fixed test client; only run in disposable builder fixtures. SPDX-License-Identifier: Apache-2.0 */
#include <X11/Xlib.h>
#include <X11/extensions/Xrender.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    if (argc!=2 || (strcmp(argv[1],"healthy") && strcmp(argv[1],"reject"))) return 64;
    Display *display=XOpenDisplay(NULL);
    if (!display) { fputs("No controlled display\n",stderr);return 1; }
    int result=XRenderQueryFormats(display);
    XCloseDisplay(display);
    printf("{\"formats\":%d}\n",result);
    return result==(!strcmp(argv[1],"healthy")) ? 0 : 1;
}
