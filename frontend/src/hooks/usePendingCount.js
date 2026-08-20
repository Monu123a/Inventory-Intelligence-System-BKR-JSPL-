import { useEffect, useState } from 'react';
import api from '../services/api';

export default function usePendingCount() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        const r = await api.get('/api/admin-approvals/?status=PENDING&limit=1');
        if (!mounted) return;
        
        // Use X-Total-Count if available from the backend response headers
        if (r.headers && r.headers['x-total-count']) {
           setCount(parseInt(r.headers['x-total-count'], 10));
        } else {
           setCount(r.data && r.data.length > 0 ? 1 : 0);
        }
      } catch (err) {
        // Ignore poll errors quietly
      }
    }
    
    poll();
    const t = setInterval(poll, 30000);
    return () => { 
      mounted = false; 
      clearInterval(t); 
    };
  }, []);

  return count;
}
