#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
cc="${CC:-cc}"
"$cc" -std=c99 -Wall -Wextra -Werror -pedantic hardcore/state.c tests/state_test.c -o "$tmp/state"
"$tmp/state"
"$cc" -std=c99 -Wall -Wextra -Werror -pedantic hardcore/state.c hardcore/cs.c hardcore/ter.c tests/ter_test.c -o "$tmp/ter"
"$tmp/ter"
printf '%s\n' 'Host tests passed'
