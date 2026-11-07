#!/system/bin/sh
# Stop after five minutes; leave the Pi running for observation.
exec >> /data/local/tmp/portdiag-state.txt 2>&1
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    echo "=== snapshot $attempt ==="
    cat /proc/uptime
    getprop init.svc.system_suspend
    getprop init.svc.surfaceflinger
    getprop init.svc.gpuservice
    getprop init.svc.vendor.graphics.allocator
    getprop init.svc.portdiag_logcat
    getprop sys.boot_completed
    ps -A
    service check appwidget
    service check wifi
    sync
    sleep 10
done
