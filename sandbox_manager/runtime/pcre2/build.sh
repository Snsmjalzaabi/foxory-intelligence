#!/bin/sh
# Trusted, non-root IMAGE BUILD code; never an agent tool or a host installer.
set -eu
test "${FOXORY_WORKER_IMAGE_BUILD:-}" = 1
test "$(id -u)" = 1000
cd /build/pcre2
export SOURCE_DATE_EPOCH=1790599717
source_dir="$PWD/pcre2-10.49"
for mode in normal sanitized; do
    mkdir "$mode"
    cd "$mode"
    if [ "$mode" = sanitized ]; then
        export CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
        export LDFLAGS='-fsanitize=address,undefined'
        export ASAN_OPTIONS='detect_leaks=1:abort_on_error=1'
        export UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'
    else
        export CFLAGS='-O2 -g0 -ffile-prefix-map=/build/pcre2=.'
        export LDFLAGS=''
    fi
    "$source_dir/configure" --prefix=/usr --libdir="/usr/lib/$(dpkg-architecture -qDEB_HOST_MULTIARCH)" \
        --enable-shared --disable-static --enable-jit --enable-unicode \
        --enable-pcre2-8 --disable-pcre2-16 --disable-pcre2-32 \
        --disable-pcre2grep-libz --disable-pcre2grep-libbz2
    timeout 600 make -j2
    timeout 600 make -j2 check
    cc $CFLAGS $LDFLAGS -I src /opt/foxory-pcre2/probe.c -L .libs -lpcre2-8 -o probe
    LD_LIBRARY_PATH="$PWD/.libs" timeout 30 ./probe
    cd ..
done
unset CFLAGS LDFLAGS ASAN_OPTIONS UBSAN_OPTIONS
python3 /opt/foxory-pcre2/package.py
