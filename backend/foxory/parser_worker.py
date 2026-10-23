"""Linux parsing boundary. Load trusted libraries, then deny filesystem/network/process access."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import base64
import codecs
import ctypes
import ctypes.util
import errno
import json
import resource
# All trusted imports occur before untrusted input is read or parsed.
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
import encodings.cp437, encodings.utf_16_le, encodings.utf_16_be
from foxory.documents import extract

def seal():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(12,12))
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(16,16))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    library=ctypes.util.find_library('seccomp')
    if not library:raise RuntimeError('libseccomp is required; no unsafe parser fallback')
    lib=ctypes.CDLL(library)
    lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
    lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_release.argtypes=[ctypes.c_void_p]
    ctx=lib.seccomp_init(0x7fff0000)
    if not ctx:raise RuntimeError('Cannot initialize sandbox')
    denied='open openat openat2 creat socket socketpair connect bind listen accept accept4 sendto recvfrom sendmsg recvmsg execve execveat fork vfork clone clone3 ptrace process_vm_readv process_vm_writev pidfd_getfd pidfd_send_signal kill tkill tgkill mount umount2 unshare setns chroot pivot_root bpf io_uring_setup io_uring_enter io_uring_register open_by_handle_at name_to_handle_at userfaultfd readlink readlinkat stat lstat newfstatat statx access faccessat faccessat2 getdents getdents64 unlink unlinkat rename renameat renameat2 mkdir mkdirat rmdir link linkat symlink symlinkat chmod fchmodat chown fchownat truncate setuid setgid setresuid setresgid capset'.split()
    try:
        for name in denied:
            nr=lib.seccomp_syscall_resolve_name(name.encode())
            if nr>=0 and lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,nr,0)!=0:raise RuntimeError('Cannot install sandbox rule')
        if ctypes.CDLL(None).prctl(38,1,0,0,0)!=0 or lib.seccomp_load(ctx)!=0:raise RuntimeError('Cannot activate sandbox')
    finally:lib.seccomp_release(ctx)

def main():
    seal()
    if '--self-test' in sys.argv:
        import socket,subprocess
        checks={}
        for name,operation in [('host_file',lambda:open('/etc/passwd').read()),('network',lambda:socket.socket()),('execution',lambda:subprocess.run(['/bin/true']))]:
            try:operation();checks[name]=False
            except (PermissionError,OSError):checks[name]=True
        print(json.dumps(checks));return
    payload=json.loads(sys.stdin.buffer.read(15_000_000))
    try:
        text=extract(payload['name'],base64.b64decode(payload['raw'],validate=True))
        print(json.dumps({'text':text}))
    except Exception as e:print(json.dumps({'error':type(e).__name__}))
if __name__=='__main__':main()
