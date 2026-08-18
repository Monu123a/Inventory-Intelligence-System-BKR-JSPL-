#!/bin/bash

echo "🔍 Fixing incorrect service paths..."

# Fix common plural mistakes
find frontend/src -type f -name "*.js" -o -name "*.jsx" | while read file; do
  sed -i '' 's|../services/warehouses|../services/warehouse|g' "$file"
  sed -i '' 's|../services/inventories|../services/inventory|g' "$file"
  sed -i '' 's|../services/reportsService|../services/reports|g' "$file"
done

echo "✅ Paths fixed."

echo "🔍 Standardizing import style to '* as service'..."

# Convert named imports to namespace imports
find frontend/src -type f -name "*.js" -o -name "*.jsx" | while read file; do
  sed -i '' 's|import { warehouseService } from "\(.*services/warehouse\)"|import * as warehouseService from "\1"|g' "$file"
  sed -i '' 's|import { inventoryService } from "\(.*services/inventory\)"|import * as inventoryService from "\1"|g' "$file"
  sed -i '' 's|import { reportsService } from "\(.*services/reports\)"|import * as reportsService from "\1"|g' "$file"
  sed -i '' 's|import { posService } from "\(.*services/pos\)"|import * as posService from "\1"|g' "$file"
  sed -i '' 's|import { damageService } from "\(.*services/damageService\)"|import * as damageService from "\1"|g' "$file"
  sed -i '' 's|import { transferService } from "\(.*services/transferService\)"|import * as transferService from "\1"|g' "$file"
done

echo "✅ Import style standardized."

echo "🔍 Removing accidental double slashes or typos..."

find frontend/src -type f -name "*.js" -o -name "*.jsx" | while read file; do
  sed -i '' 's|//services|/services|g' "$file"
done

echo "✅ Cleanup done."

echo "🎯 Verification..."

echo "➡️ Checking for broken 'warehouses' imports..."
grep -r "services/warehouses" frontend/src && echo "❌ Still exists!" || echo "✅ Clean"

echo "➡️ Checking mixed import styles..."
grep -r "import { .*Service }" frontend/src && echo "❌ Mixed imports still exist!" || echo "✅ Clean"

echo "🚀 Done. Restart Vite now."
