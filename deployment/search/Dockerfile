FROM ghcr.io/searxng/searxng@sha256:79180616c984f39524f6f27f19625a46f82c8ad4aa6a2e553db52b14e1b4a768
COPY deployment/search/certifi.json deployment/search/update_certifi.py /tmp/
RUN /usr/sbin/python /tmp/update_certifi.py && rm /tmp/update_certifi.py /tmp/certifi.json
