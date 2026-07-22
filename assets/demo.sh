#!/usr/bin/env bash
# Demo script for asciinema/agg GIF generation.

set -e

type_line() {
    local line="$1"
    printf '$ '
    for (( i=0; i<${#line}; i++ )); do
        printf '%s' "${line:$i:1}"
        sleep 0.04
    done
    echo ''
    sleep 0.2
}

type_line 'python3 flight.py diff examples/auth-failure-good.flight examples/auth-failure-bad.flight'
python3 flight.py diff examples/auth-failure-good.flight examples/auth-failure-bad.flight
sleep 2
