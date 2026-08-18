#!/bin/bash

echo "🔍 Running Frontend Integrity Checks..."
echo "--------------------------------------"

FAIL=0

# 1. Wrong service import paths (plural mistake)
echo "Checking wrong service paths..."
grep -r "services/warehouses" frontend/src && FAIL=1 || echo "✅ No plural service path issues"

# 2. Broken nested service usage (old bug)
echo ""
echo "Checking nested service access..."
grep -r "\.warehouseService\." frontend/src && FAIL=1 || echo "✅ No nested service misuse"

# 3. queryFn executing immediately (critical bug)
echo ""
echo "Checking queryFn execution mistakes..."
grep -r "queryFn: .*()" frontend/src && FAIL=1 || echo "✅ All queryFn are function refs"

# 4. mutationFn incorrect wrapping
echo ""
echo "Checking mutationFn mistakes..."
grep -r "mutationFn: () => .*Service\." frontend/src && FAIL=1 || echo "✅ mutationFn correctly passed"

# 5. Axios response leaks (VERY IMPORTANT)
echo ""
echo "Checking response normalization..."
grep -r "return response$" frontend/src/services && FAIL=1 || echo "✅ No raw response leaks"

# 6. Direct fetch usage (bypassing api.js)
echo ""
echo "Checking raw fetch usage..."
grep -r "fetch(" frontend/src && FAIL=1 || echo "✅ No raw fetch calls"

# 7. Ensure all services use normalizer
echo ""
echo "Checking normalized responses..."
grep -r "response.data" frontend/src/services >/dev/null || echo "⚠️ WARNING: No normalization found"

# 8. Build test
echo ""
echo "Running production build..."
cd frontend && npm run build >/dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "❌ Build failed"
  FAIL=1
else
  echo "✅ Build successful"
fi

echo "--------------------------------------"

if [ $FAIL -eq 0 ]; then
  echo "🚀 FRONTEND STATUS: BULLETPROOF"
else
  echo "❌ FRONTEND STATUS: ISSUES FOUND"
fi
