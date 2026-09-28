#!/bin/bash
OLD_DB="postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"
NEW_DB="postgresql://postgres.ttlxrvjydjhpltdotnml:xakket-famqec-7Mysto@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

echo "Dumping old DB..."
docker run --rm postgres:latest pg_dump "$OLD_DB" --clean --if-exists -O -x > render_dump_latest.sql

echo "File size:"
ls -lh render_dump_latest.sql

echo "Restoring to Supabase..."
docker run --rm -i postgres:latest psql "$NEW_DB" -q < render_dump_latest.sql
echo "Done."
