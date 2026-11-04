# syntax=docker/dockerfile:1
ARG FOXORY_APP_IMAGE=foxory-local-app:7.0.1
FROM ubuntu:24.04@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake ca-certificates && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:1688a167a8edd9499cdd0c19b8bd044f0fa184b466981977bbf2222d884953a4 https://codeload.github.com/ggml-org/llama.cpp/tar.gz/8642541b255bfb5dc39cd351a178be09013a55d6 /tmp/llama.tar.gz
RUN mkdir /src && tar -xzf /tmp/llama.tar.gz -C /src --strip-components=1 && cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF && cmake --build /build --target llama-server -j 4
RUN mkdir /licenses && cd /src && find . -type f \( -iname 'license*' -o -iname 'copying*' -o -iname '*notice*' \) -exec cp --parents '{}' /licenses/ \;
# Reuse the reviewed/patched FOXORY runtime base; build tools never ship.
FROM ${FOXORY_APP_IMAGE}
COPY --from=build /build/bin/llama-server /usr/local/bin/llama-server
COPY --from=build /licenses /usr/share/doc/foxory/llama-third-party
COPY --from=build /src/LICENSE /usr/share/doc/foxory/LLAMA-CPP-LICENSE
COPY deployment/llama/entrypoint.py /opt/foxory-ai-entrypoint.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"
ENTRYPOINT ["python", "/opt/foxory-ai-entrypoint.py"]
CMD ["--help"]
