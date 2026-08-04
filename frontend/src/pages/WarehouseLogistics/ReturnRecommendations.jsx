import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ReturnRecommendations = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('/api/fc-dispatches/recommendations')
      .then(res => {
        // Handle both direct array or wrapped data response
        setRecommendations(Array.isArray(res.data) ? res.data : (res.data.data || []));
      })
      .catch(err => console.error('Error fetching recommendations:', err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Return Recommendations</h1>
        <p className="text-gray-600 mt-1">45-Day Aging FC Inventory Recommendations</p>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Product</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">FC Warehouse</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Days Aging</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quantity</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {recommendations.map((rec, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{rec.product || rec.productName}</div>
                  {rec.sku && <div className="text-xs text-gray-500">{rec.sku}</div>}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{rec.warehouse || rec.warehouseName}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                    ${(rec.daysSinceDispatch || rec.daysAging) > 60 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>
                    {rec.daysSinceDispatch || rec.daysAging} days
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{rec.quantity || 1} units</td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button className="text-blue-600 hover:text-blue-900 bg-blue-50 px-3 py-1 rounded-md border border-blue-200 transition-colors">
                    Initiate Return
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {!loading && recommendations.length === 0 && (
          <div className="p-12 text-center bg-gray-50">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No pending recommendations</h3>
            <p className="mt-1 text-sm text-gray-500">All inventory within healthy aging limits.</p>
          </div>
        )}
        
        {loading && (
          <div className="p-8 text-center text-gray-500">Analyzing inventory aging...</div>
        )}
      </div>
    </div>
  );
};

export default ReturnRecommendations;
