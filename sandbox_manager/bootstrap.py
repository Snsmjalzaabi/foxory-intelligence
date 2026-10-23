"""Trusted single-process Linux entry point, mounted read-only before sealing."""
import ctypes
import errno
import os
import runpy
import sys
import unittest
# This fixed profile forbids all process/thread creation and all network syscalls.
lib=ctypes.CDLL('libseccomp.so.2')
lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_release.argtypes=[ctypes.c_void_p]
ctx=lib.seccomp_init(0x7fff0000)
if not ctx:raise RuntimeError('seccomp unavailable')
try:
    for name in '''socket socketpair connect bind listen accept accept4 sendto recvfrom sendmsg recvmsg
execve execveat fork vfork clone clone3 ptrace process_vm_readv process_vm_writev pidfd_getfd
pidfd_send_signal kill tkill tgkill mount umount2 unshare setns chroot pivot_root bpf io_uring_setup
io_uring_enter io_uring_register open_by_handle_at name_to_handle_at userfaultfd setuid setgid
setresuid setresgid capset prctl seccomp keyctl add_key request_key reboot kexec_load perf_event_open'''.split():
        number=lib.seccomp_syscall_resolve_name(name.encode())
        if number>=0 and lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,number,0)!=0:raise RuntimeError('seccomp rule failure')
    if ctypes.CDLL(None).prctl(38,1,0,0,0)!=0 or lib.seccomp_load(ctx)!=0:raise RuntimeError('seccomp activation failure')
finally:lib.seccomp_release(ctx)
if os.getuid()==0:raise RuntimeError('Root execution refused')
os.chdir('/work');sys.path.insert(0,'/work')
status=0
entrypoint=sys.argv[1];sys.argv=[entrypoint]
try:
    runpy.run_path(entrypoint,run_name='__main__')
except SystemExit as error:
    status=error.code if isinstance(error.code,int) else (0 if error.code is None else 1)
except BaseException:
    import traceback
    traceback.print_exc();status=1
sys.exit(status)
