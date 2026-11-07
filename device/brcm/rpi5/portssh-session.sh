#!/system/bin/sh
# Keep SSH's private libraries out of diagnostic commands and interactive shells.
unset LD_LIBRARY_PATH
if [ -n "$SSH_ORIGINAL_COMMAND" ]; then
    exec /system/bin/sh -c "$SSH_ORIGINAL_COMMAND"
fi
exec /system/bin/sh -i
