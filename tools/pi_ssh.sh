#!/usr/bin/env bash
# Key-pinned shell access to the temporary Pi SSH endpoint.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
address=${1:?usage: pi_ssh.sh PI_IP [COMMAND ...]}
shift
[[ $address =~ ^[a-zA-Z0-9][a-zA-Z0-9.:-]*$ ]] || { echo 'Invalid address' >&2; exit 2; }
state="$project/work/ssh-trial"
exec ssh -p 2222 -i "$state/keys/client_ed25519" \
    -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
    -o HostKeyAlias=aluminium-pi5 \
    -o UserKnownHostsFile="$state/known_hosts" \
    -o ConnectTimeout=8 "shell@$address" "$@"
