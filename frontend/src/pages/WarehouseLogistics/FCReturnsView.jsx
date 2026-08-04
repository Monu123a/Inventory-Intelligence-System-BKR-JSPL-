import React, { useState, useEffect } from 'react';
import axios from 'axios';

const FCReturnsView = () => {
  const [returns, setReturns] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [newReturn, setNewReturn] = useState({ dispatchId: '', reason: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchReturns();
  }, []);

  const fetchReturns = () => {
    setLoading(true);
    axios.get('/api/fc-returns')
      .then(res => setReturns(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  const handleCreateReturn = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/fc-returns', newReturn);
      setShowModal(false);
      setNewReturn({ dispatchId: '', reason: '' });
      fetchReturns();
      alert('Return request created successfully');
    } catch (err) {
      console.error(err);
      alert('Error creating return request');
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">FC Returns</h1>
        <button 
          onClick={() => setShowModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-md shadow hover:bg-blue-700 transition-colors"
        >
          + New Return Request
        </button>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Return ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dispatch ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reason</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {returns.map(ret => (
              <tr key={ret.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{ret.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{ret.dispatchId}</td>
                <td className="px-6 py-4 text-sm text-gray-500 truncate max-w-xs">{ret.reason}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                    ${ret.status === 'APPROVED' ? 'bg-green-100 text-green-800' : 
                      ret.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' : 
                      'bg-gray-100 text-gray-800'}`}>
                    {ret.status || 'PENDING'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && returns.length === 0 && (
          <div className="p-8 text-center text-gray-500">No return requests found.</div>
        )}
        {loading && (
          <div className="p-8 text-center text-gray-500">Loading returns...</div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-xl font-bold text-gray-800">Initiate FC Return</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateReturn} className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Dispatch ID</label>
                <input 
                  type="text" 
                  value={newReturn.dispatchId}
                  onChange={(e) => setNewReturn({...newReturn, dispatchId: e.target.value})}
                  className="block w-full rounded-md border-gray-300 shadow-sm p-2 border focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g. DISP-1234"
                  required
                />
              </div>
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason for Return</label>
                <textarea 
                  value={newReturn.reason}
                  onChange={(e) => setNewReturn({...newReturn, reason: e.target.value})}
                  className="block w-full rounded-md border-gray-300 shadow-sm p-2 border focus:ring-blue-500 focus:border-blue-500 h-24"
                  placeholder="Explain why items are being returned"
                  required
                />
              </div>
              <div className="flex justify-end gap-3">
                <button 
                  type="button" 
                  onClick={() => setShowModal(false)} 
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 shadow-sm"
                >
                  Submit Return
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default FCReturnsView;
