#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
cc="${CC:-cc}"
for flag in '' '-DAIGMOS_ACCESSCORE'; do
    "$cc" -std=c99 -Os $flag tests/footprint.c -o "$tmp/profile"
    "$tmp/profile"
done
