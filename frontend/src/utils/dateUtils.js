/**
 * Formats a date value into DD/MM/YYYY.
 * Handles ISO strings, timestamps, Date objects, and YYYY-MM-DD strings.
 */
export function formatDate(dateVal) {
  if (!dateVal) return '-';
  try {
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) {
      const str = String(dateVal).trim();
      if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
        const parts = str.slice(0, 10).split('-');
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
      return str;
    }
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  } catch (e) {
    return String(dateVal);
  }
}
