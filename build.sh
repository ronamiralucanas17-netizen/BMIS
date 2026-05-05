#!/bin/bash
set -e

export GDAL_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu/libgdal.so.32"
export GEOS_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu/libgeos_c.so.1.17.1"

echo "GDAL_LIBRARY_PATH=$GDAL_LIBRARY_PATH"
echo "GEOS_LIBRARY_PATH=$GEOS_LIBRARY_PATH"

pip install -r requirements.txt

python manage.py collectstatic --noinput
