#!/bin/bash
# Fails if a credential file is readable by anyone but its owner.
# Run it from the docker/ folder before `docker compose up`.
set -u
status=0
for f in gaia.env geoserver.env proxy.env; do
    [ -e "$f" ] || { echo "MISSING   $f"; status=1; continue; }
    mode=$(stat -c '%a' "$f")
    if [ $(( 8#$mode & 8#077 )) -ne 0 ]; then
        echo "TOO OPEN  $f (mode $mode) - run: chmod 600 $f"
        status=1
    else
        echo "ok        $f (mode $mode)"
    fi
done
exit $status
