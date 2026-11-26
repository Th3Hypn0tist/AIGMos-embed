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
"$cc" -std=c99 -Wall -Wextra -Werror -pedantic hardcore/cs.c hardcore/routine.c tests/routine_test.c -o "$tmp/routine"
"$tmp/routine"
"$cc" -std=c99 -Wall -Wextra -Werror -pedantic -DAIGMOS_ACCESSCORE hardcore/cs.c tests/access_test.c -o "$tmp/access"
"$tmp/access"
"$cc" -std=c99 -Wall -Wextra -Werror -pedantic hardcore/state.c hardcore/input.c core/validate.c tests/validate_test.c -o "$tmp/validate"
"$tmp/validate"
printf '%s\n' 'Host tests passed'
