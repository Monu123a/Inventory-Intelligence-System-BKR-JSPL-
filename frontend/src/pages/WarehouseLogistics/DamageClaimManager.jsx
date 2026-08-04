import React, { useState, useEffect } from 'react';
import axios from 'axios';

const DamageClaimManager = () => {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchClaims();
  }, []);

  const fetchClaims = () => {
    setLoading(true);
    axios.get('/api/damage-claims')
      .then(res => setClaims(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  const handleUpdateStatus = async (id, status) => {
    if (!window.confirm(`Are you sure you want to ${status.toLowerCase()} this claim?`)) return;
    
    try {
      await axios.patch(`/api/damage-claims/${id}/status`, { status });
      fetchClaims(); // Refresh list
    } catch (err) {
      console.error(err);
      alert('Error updating claim status');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Damage Claims Management</h1>
      
      <div className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Claim ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Item Details</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reported Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {claims.map(claim => (
              <tr key={claim.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{claim.id}</td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  <div className="font-medium text-gray-900">{claim.item}</div>
                  {claim.description && <div className="text-xs text-gray-500 mt-1 truncate max-w-xs">{claim.description}</div>}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {claim.date ? new Date(claim.date).toLocaleDateString() : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                    ${claim.status === 'APPROVED' ? 'bg-green-100 text-green-800' : 
                      claim.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 
                      'bg-yellow-100 text-yellow-800'}`}>
                    {claim.status || 'PENDING'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  {(claim.status === 'PENDING' || !claim.status) ? (
                    <div className="flex gap-3">
                      <button 
                        onClick={() => handleUpdateStatus(claim.id, 'APPROVED')}
                        className="text-green-600 hover:text-green-900 bg-green-50 px-2 py-1 rounded border border-green-200 transition-colors"
                      >
                        Approve
                      </button>
                      <button 
                        onClick={() => handleUpdateStatus(claim.id, 'REJECTED')}
                        className="text-red-600 hover:text-red-900 bg-red-50 px-2 py-1 rounded border border-red-200 transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  ) : (
                    <span className="text-gray-400 italic">Resolved</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {!loading && claims.length === 0 && (
          <div className="p-8 text-center text-gray-500 bg-gray-50">
            <div className="text-lg font-medium mb-1">No damage claims</div>
            <p className="text-sm">There are currently no damage claims to process.</p>
          </div>
        )}
        
        {loading && (
          <div className="p-8 text-center text-gray-500">Loading claims...</div>
        )}
      </div>
    </div>
  );
};

export default DamageClaimManager;
