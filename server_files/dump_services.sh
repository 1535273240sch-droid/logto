#!/bin/bash
for svc in chat file image tool workflow api; do
  echo "=== $svc ==="
  sudo docker exec dream-os-backend-1 cat /dream-os/services/$svc/service.py
done
