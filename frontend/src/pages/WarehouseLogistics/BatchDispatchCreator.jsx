import React, { useState } from 'react';
import axios from 'axios';

const BatchDispatchCreator = () => {
  const [warehouse, setWarehouse] = useState('');
  const [products, setProducts] = useState([{ product: '', quantity: 1 }]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/fc-dispatches', {
        warehouse,
        items: products
      });
      alert('Dispatch created successfully');
      setWarehouse('');
      setProducts([{ product: '', quantity: 1 }]);
    } catch (err) {
      console.error(err);
      alert('Error creating dispatch');
    }
  };

  const addProduct = () => {
    setProducts([...products, { product: '', quantity: 1 }]);
  };

  const removeProduct = (idx) => {
    const newProducts = [...products];
    newProducts.splice(idx, 1);
    setProducts(newProducts);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Create Batch Dispatch</h1>
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md border border-gray-100">
        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">FC Warehouse</label>
          <input 
            type="text" 
            value={warehouse} 
            onChange={(e) => setWarehouse(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm p-3 border focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter warehouse name or ID"
            required
          />
        </div>
        
        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-3">Products to Dispatch</label>
          {products.map((p, idx) => (
            <div key={idx} className="flex gap-3 mb-3 items-center bg-gray-50 p-3 rounded-md">
              <div className="flex-1">
                <input 
                  type="text" 
                  placeholder="Product ID/Name" 
                  value={p.product}
                  onChange={(e) => {
                    const newProducts = [...products];
                    newProducts[idx].product = e.target.value;
                    setProducts(newProducts);
                  }}
                  className="w-full rounded-md border-gray-300 shadow-sm p-2 border focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
              <div className="w-32">
                <input 
                  type="number" 
                  min="1"
                  placeholder="Qty"
                  value={p.quantity}
                  onChange={(e) => {
                    const newProducts = [...products];
                    newProducts[idx].quantity = parseInt(e.target.value, 10);
                    setProducts(newProducts);
                  }}
                  className="w-full rounded-md border-gray-300 shadow-sm p-2 border focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
              {products.length > 1 && (
                <button 
                  type="button" 
                  onClick={() => removeProduct(idx)}
                  className="text-red-500 hover:text-red-700 p-2 font-bold"
                >
                  &times;
                </button>
              )}
            </div>
          ))}
          <button 
            type="button" 
            onClick={addProduct} 
            className="mt-2 text-sm font-medium text-blue-600 hover:text-blue-500 flex items-center"
          >
            + Add Another Product
          </button>
        </div>

        <div className="border-t border-gray-200 pt-5 flex justify-end">
          <button 
            type="submit" 
            className="bg-blue-600 text-white px-6 py-2.5 rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 font-medium"
          >
            Submit Dispatch
          </button>
        </div>
      </form>
    </div>
  );
};

export default BatchDispatchCreator;
