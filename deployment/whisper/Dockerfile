# syntax=docker/dockerfile:1
ARG FOXORY_APP_IMAGE=foxory-local-app:latest
FROM ubuntu:24.04@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake ca-certificates && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:645445da884df6dbd52b30f82d7be7c01d1767c938714e477e786b88d529e9f4 https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/d1be6fde11ac6e0407606b4e42fe72d34add8037 /tmp/whisper.tar.gz
RUN mkdir /src && tar -xzf /tmp/whisper.tar.gz -C /src --strip-components=1
# The upstream server lets any caller load a model from an arbitrary path via POST /load.
# FOXORY uses one pinned model, so that route is removed; the build fails if the patch does not apply.
RUN sed -i 's|svr->Post(sparams.request_path + "/load"|if (false) svr->Post(sparams.request_path + "/load"|' /src/examples/server/server.cpp \
 && grep -q 'if (false) svr->Post(sparams.request_path + "/load"' /src/examples/server/server.cpp
RUN cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON -DWHISPER_BUILD_SERVER=ON -DWHISPER_CURL=OFF -DWHISPER_SDL2=OFF -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF \
 && cmake --build /build --target whisper-server -j 4
RUN mkdir /licenses && cd /src && find . -type f \( -iname 'license*' -o -iname 'copying*' -o -iname '*notice*' \) -exec cp --parents '{}' /licenses/ \;
# Reuse the reviewed FOXORY runtime base; build tools never ship.
FROM ${FOXORY_APP_IMAGE}
COPY --from=build /build/bin/whisper-server /usr/local/bin/whisper-server
COPY --from=build /licenses /usr/share/doc/foxory/whisper-third-party
COPY --from=build /src/LICENSE /usr/share/doc/foxory/WHISPER-CPP-LICENSE
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"
ENTRYPOINT ["/usr/local/bin/whisper-server"]
