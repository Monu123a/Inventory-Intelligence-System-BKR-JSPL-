import re

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "r") as f:
    content = f.read()

old_mutation = """  const checkoutMutation = useMutation({
    mutationFn: posService.checkout,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      
      const receipt = data.receipt;
      const saleId = receipt?.id;

      // Reset form
      setCart([]);
      setCustomerInfo({ name: '', mobile: '', gstin: '', address: '', state: '', state_code: '', place_of_supply: '', email: '', phone: '' });
      setInvoiceInfo({ payment_terms: '', delivery_note: '', delivery_note_date: '', dispatch_document_number: '', dispatch_through: '', destination: '', vehicle_number: '', lr_rr_number: '', terms_of_delivery: '', custom_invoice_number: '', custom_invoice_date: '' });
      setPaymentReference('');
      setSearchTerm('');
      localStorage.removeItem(POS_STORAGE_KEY);
      
      // Regenerate idempotency key for the next operation
      idempotencyKeyRef.current = window.crypto.randomUUID();

      if (!receipt?.id) return;

      if (saleId) {
        navigate(`/sales/${saleId}/invoice`, { state: { receipt } });
      }
    },
    onError: (err) => {
      handleApiError(err, "Checkout failed");
    }
  });"""

new_mutation = """  const checkoutMutation = useMutation({
    mutationFn: async (payload) => {
      const res = await api.put(`/api/pos/sales/${id}`, payload);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      
      localStorage.removeItem(POS_STORAGE_KEY);
      navigate(`/pos-history`);
    },
    onError: (err) => {
      handleApiError(err, "Update failed");
    }
  });"""

content = content.replace(old_mutation, new_mutation)

with open("frontend/src/pages/POS/EditInvoicePageImpl.jsx", "w") as f:
    f.write(content)
