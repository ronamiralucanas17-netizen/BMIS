#!/bin/bash
GDAL_PATH=$(find /nix/store -name "libgdal.so" 2>/dev/null | head -1)
GEOS_PATH=$(find /nix/store -name "libgeos_c.so" 2>/dev/null | head -1)

if [ -z "$GDAL_PATH" ]; then
    GDAL_PATH=$(find /usr -name "libgdal.so" 2>/dev/null | head -1)
fi

if [ -z "$GEOS_PATH" ]; then
    GEOS_PATH=$(find /usr -name "libgeos_c.so" 2>/dev/null | head -1)
fi

export GDAL_LIBRARY_PATH="${GDAL_LIBRARY_PATH:-$GDAL_PATH}"
export GEOS_LIBRARY_PATH="${GEOS_LIBRARY_PATH:-$GEOS_PATH}"
export LD_LIBRARY_PATH="/usr/lib:/usr/local/lib:$LD_LIBRARY_PATH"

echo "Starting with GDAL_LIBRARY_PATH=$GDAL_LIBRARY_PATH"
echo "Starting with GEOS_LIBRARY_PATH=$GEOS_LIBRARY_PATH"

exec gunicorn bmis.wsgi