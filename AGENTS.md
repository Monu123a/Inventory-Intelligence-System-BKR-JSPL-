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

# SKU and Product Management

When adding new products, parsing raw files, or updating the catalog, adhere to the following rules:

1. **SKU Pattern Extraction:** When attempting to extract a valid SKU from a messy product name or string, use the standard pattern: **2 alphabetic characters followed by 4+ numeric digits, optionally followed by a hyphen and more digits/letters**. 
   - *Example Matches:* `LG0831`, `LG0831-1`, `AC12345`
   - *Regex Reference:* `\b[A-Za-z]{2}\d{4}[0-9\-]*\b`

2. **Strict SKU Variant Isolation:** A product with a suffix like `-1` (e.g., `LG0831-1`) is a **completely distinct and separate product** from its base SKU (`LG0831`). 
   - **Never** automatically merge inventory or consolidate records for SKUs that share a base but have different suffixes. 
   - Treat them as unique, separate products in the system to prevent critical inventory mismatches.

3. **Generating Lists:** Before executing bulk stock merges or major SKU catalog modifications, always generate a dry-run list (e.g., New vs. Old SKUs, Conflicts, Missing Patterns) for user review.
