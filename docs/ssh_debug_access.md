> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Temporary SSH debug access — Pi 5

The Aluminium system does not include an SSH daemon. The trial reuses sshd and
libssh from the already boot-tested Pi baseline
`AOSP17-20260702-KonstaKANG-rpi5.img` (OpenSSH 8.0p1 / BoringSSL). This is a
temporary bring-up endpoint on the local network, not a production SSH update.

## Endpoint

- IPv4 TCP 2222, account shell (UID 2000).
- Only the generated workstation Ed25519 public key is authorized.
- Password/interactive authentication, root login, forwarding and tunnels disabled.
- Existing enforcing shell SELinux domain; no new policy rules/permissive types.
- Baseline dependencies are isolated in /system/lib64/portssh. The session
  wrapper clears LD_LIBRARY_PATH before executing diagnostic commands.

No private key is printed in logs or committed. Local keys, payload and emulator
workspace are ignored under work/ssh-trial/. Client key stays on this workstation;
the image receives only its public key plus a distinct server host private key.
Server key is owned by shell, mode 0600, in a root-owned directory. SSH client
helper pins the server public key through a dedicated known_hosts file.

After boot, connect Pi and workstation to the same LAN and obtain the Pi IPv4
address from Settings/router. Then:

    tools/pi_ssh.sh PI_IP
    tools/pi_ssh.sh PI_IP 'getprop sys.boot_completed; service list'
    tools/pi_ssh.sh PI_IP 'logcat -b all -d -t 2000'

Remote account is Android shell, not root. Android DAC, framework permissions
and SELinux still govern diagnostics. This does not bypass authorization or
grant access to every app's private files. The key is not a replacement for sudo.

## Files

- /system/bin/port-sshd
- /system/lib64/portssh/*.so
- /system/etc/portssh/{sshd_config,start.sh,session.sh,authorized_keys,ssh_host_ed25519_key}
- /system/etc/init/portssh.rc
- Runtime log: /data/local/tmp/portssh.log

Service starts after post-fs-data independently of desktop launch. It restarts
on failure through normal init behavior; connection testing on hardware is
required. To remove the endpoint offline, remove portssh.rc and optionally the
payload files using the same unmounted-image editing workflow.

## Validation

- Binary and private dependencies extracted from the Pi baseline; 16 KiB ELF
  segment alignment confirmed for sshd.
- ARM64 QEMU loaded the baseline SSH libraries with Aluminium's linker and
  bootstrap bionic runtime. sshd -t passed and sshd -T confirmed key-only auth,
  shell-only account, no root login and port 2222.
- Non-root emulator startup bound 127.0.0.1:22222 and stayed running until the
  test timeout. Hardware SELinux/session execution was not emulated.
- Installer validates content, modes, uid/gid and labels without exposing key
  contents, then runs e2fsck. Files are system_file/system_lib_file, matching
  existing shell permissions. No platform libraries are overwritten.
- Actual SSH login on Pi remains pending until it is booted and reachable.

Installed on Hynix V2 /dev/sda5, serial YOUR_SSD_SERIAL, on 2026-11-04.
System journal recovered before editing; file verification and e2fsck passed;
writes flushed. Evidence: work/ssh-trial/install-disk.log. No SHA reader started.
