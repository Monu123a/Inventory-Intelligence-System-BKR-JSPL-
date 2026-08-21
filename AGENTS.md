---
name: Database Updates
description: Guidelines on how to update data in the database safely and efficiently.
trigger: always_on
---

# Database Updates

When asked to update data in the database, follow these steps:

1. **Write a Python script** in the `backend/` directory to perform the updates.
2. **Use raw `psycopg2` and `psycopg2.extras.execute_values`** for bulk updates instead of SQLAlchemy `executemany`. SQLAlchemy can be extremely slow or cause locks over remote connections (e.g., Render). `execute_values` guarantees high-performance, single-query execution.
3. **Use the centralized database URL** if provided, or read from `.env`.
   - e.g., `DATABASE_URL = "postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg"`
4. **Parse data files** using `pandas` (for `.xlsx`, `.csv`). Always strip string fields and handle `nan` gracefully.
5. **Deduce GST calculations** when necessary. If a price is inclusive of GST and we need the exclusive price, use the formula: `Price_excl_GST = Price_incl_GST / (1 + (GST % / 100))`.
6. **Commit the transaction** and print the number of updated records.
