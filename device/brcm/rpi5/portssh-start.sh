#!/system/bin/sh
exec >> /data/local/tmp/portssh.log 2>&1
export LD_LIBRARY_PATH=/system/lib64/portssh
exec /system/bin/port-sshd -D -e -f /system/etc/portssh/sshd_config
