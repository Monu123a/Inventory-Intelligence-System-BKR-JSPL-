export const normalizeResponse = (res) => {
  if (!res) return null

  // If backend returns a paginated structure, preserve the whole object
  if (typeof res === 'object' && ('total_records' in res || 'total' in res || 'total_pages' in res)) {
    return res
  }

  // If backend wraps in { data }
  if (typeof res === 'object' && 'data' in res) {
    return res.data
  }

  return res
}
