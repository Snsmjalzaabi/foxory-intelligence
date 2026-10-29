# Optional private Unix manager API transport

The default Compose stack still has no execution manager or host runtime socket.
A manager bound to host loopback cannot be reached through a normal Docker bridge
at `127.0.0.1`. The optional Linux Unix-socket transport avoids exposing a new TCP
listener or giving the application Podman/Docker access. Existing trusted-local
HTTP transport remains supported.

Only a verified operator configures `FOXORY_SANDBOX_SOCKET`. It must be an absolute
Unix socket path (at most 100 bytes), not a symlink, not world-writable, inside a
directory that is neither group- nor world-writable. Explicit enablement and the
same 32+-character private manager key remain mandatory. `FOXORY_SANDBOX_URL`
must be empty; ambiguous transports fail closed. Client requests preserve their
workspace header and authentication, ignore HTTP proxies and never follow
redirects. Missing/unsafe socket settings report unavailable capabilities.

`deployment/foxory-sandbox-oci-uds.socket` and `.service` are **installation
templates awaiting owner topology verification**. Install only in the dedicated
account's user-unit directory after reviewing host requirements. The socket unit
creates `%t/foxory-sandbox-api/manager.sock` mode0660 in a mode0750 directory,
owned by that account/primary group. The service uses the inherited FD and the
same private environment, delegation/quotas and active probes as the TCP manager.
Keep manager persistent state in a different private mode0700 directory. Enable
the socket unit rather than starting both TCP and Unix managers on one state dir.

For the application's normal Linux Docker deployment, the optional override is:

```bash
# In the private owner .env: actual dedicated-account primary GID and socket dir
# FOXORY_SANDBOX_GID=<id -g foxory-sandbox>
# FOXORY_SANDBOX_SOCKET_DIR=/run/user/<dedicated UID>/foxory-sandbox-api
# FOXORY_SANDBOX_KEY=<same private manager key; never print/commit>
docker compose -f compose.yaml -f compose.sandbox-socket.yaml config --quiet
# After all host/topology approvals and acceptance, deliberately select this
# override when starting the owner's application. It enables optional execution.
```

The override adds that numeric supplementary group and mounts **only the private
FOXORY API socket directory**, read-only, with automatic path creation disabled.
It does not mount the manager home/state, Podman storage, privileged runtime
sockets or host source. A read-only mount still permits socket communication;
server authentication/permissions remain essential. The app can submit requests
as the trusted manager client, so compromise of the app/client key remains a
security boundary. Agent/user workspace and approval policies still apply.

Numeric GID mapping/rootless Docker/SELinux, boot socket recreation, actual
systemd activation and final Compose connectivity must be validated on the
owner host. Do not change directory modes to0777, expose runtime sockets or
disable AppArmor to work around permission failures. Hosted FD/Unix adapter
results and controlled HTTP fixture results have distinct scopes; neither proves
all host installations work. Default configurations remain disabled.
