#!/bin/sh
# Trusted build-only fixtures. Both X11 peers are disposable and network-disabled.
set -eu
test "${FOXORY_WORKER_IMAGE_BUILD:-}" = 1
test "$(id -u)" = 1000
cd /build/xrender
export SOURCE_DATE_EPOCH=1792182503
for mode in baseline-build normal sanitized; do
    if [ "$mode" = baseline-build ]; then source_dir="$PWD/baseline/libXrender-0.9.12"; else source_dir="$PWD/fixed/libXrender-0.9.13"; fi
    mkdir "$mode"; cd "$mode"
    if [ "$mode" = normal ]; then
        export CFLAGS='-O2 -g0 -ffile-prefix-map=/build/xrender=.' LDFLAGS=''
    else
        export CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
        export LDFLAGS='-fsanitize=address,undefined'
    fi
    "$source_dir/configure" --prefix=/usr --libdir="/usr/lib/$(dpkg-architecture -qDEB_HOST_MULTIARCH)" --disable-static --enable-shared --disable-specs
    timeout 300 make -j2
    cc $CFLAGS $LDFLAGS -I "$source_dir/include" /opt/foxory-xrender/client.c -L src/.libs -lXrender -lX11 -o client
    if [ "$mode" = baseline-build ]; then
        timeout 45 python3 /opt/foxory-xrender/regression.py --binary "$PWD/client" --library "$PWD/src/.libs" --vulnerable > regression.json
    else
        timeout 45 python3 /opt/foxory-xrender/regression.py --binary "$PWD/client" --library "$PWD/src/.libs" > regression.json
    fi
    cat regression.json
    if [ "$mode" = normal ]; then
        cc $CFLAGS -I "$source_dir/include" /opt/foxory-xrender/probe.c -L src/.libs -lXrender -ldl -o probe
    fi
    cd ..
done
python3 /opt/foxory-xrender/package.py
