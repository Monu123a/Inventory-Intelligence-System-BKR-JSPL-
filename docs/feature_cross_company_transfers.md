# Cross-Company Transfers (BKR ⇄ JSPL)

This feature allows for safe, idempotent stock replenishment between BKR and JSPL company contexts.

## Enabling Flags
- **Backend**: Set `CROSS_COMPANY_TRANSFERS=true` in the backend environment to permit cross-company API requests. If `false`, the backend immediately rejects these requests with 403 Forbidden.
- **Frontend**: Set `VITE_CROSS_COMPANY_TRANSFERS=true` in the frontend `.env` to enable the cross-company warehouse selection toggles and UI components.

## Verification Commands
After enabling the feature, run the following to verify:

1. **UAT Script**:
   ```bash
   python3 scratch/uat_cross_company_transfers.py
   ```

2. **Database Verification (SQL)**:
   ```sql
   -- Check inventory movements count for transfer (should be 2 × number of SKUs)
   SELECT COUNT(*) FROM inventory_movements WHERE transfer_id = <TRANSFER_ID>;
   
   -- Ensure OUT movement exists for source company
   SELECT * FROM inventory_movements
    WHERE transfer_id = <TRANSFER_ID> AND company_id = <SOURCE_COMPANY_ID> AND movement_type = 'OUT';
    
   -- Ensure IN movement exists for destination company
   SELECT * FROM inventory_movements
    WHERE transfer_id = <TRANSFER_ID> AND company_id = <DEST_COMPANY_ID> AND movement_type = 'IN';
   ```

## Rollback Plan
If any issues are discovered:
1. Immediately set `CROSS_COMPANY_TRANSFERS=false` in the backend and restart the service.
2. Set `VITE_CROSS_COMPANY_TRANSFERS=false` in the frontend and redeploy.
3. If database corruption occurred, restore from the pre-release backup.
4. If the database migration is problematic, run `alembic downgrade -1`.
