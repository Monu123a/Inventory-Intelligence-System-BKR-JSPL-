export const normalizeResponse = (res) => {
  if (!res) return null

  // If backend wraps in { data }
  if (typeof res === 'object' && 'data' in res) {
    return res.data
  }

  return res
}
