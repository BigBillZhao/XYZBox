#!/bin/sh
# Desktop launcher also works when the NAS/network service is still starting.
for attempt in $(seq 1 60); do
    if curl --silent --fail --max-time 1 http://127.0.0.1:8830/ >/dev/null; then
        break
    fi
    sleep 1
done
exec xdg-open http://127.0.0.1:8830/
