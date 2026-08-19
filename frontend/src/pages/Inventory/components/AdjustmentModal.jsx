import React, { useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import Input from '../../../components/forms/Input';
import styles from './AdjustmentModal.module.css';

export const AdjustmentModal = ({ isOpen, onClose, onSubmit, inventoryRow, isLoading = false }) => {
  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    defaultValues: { quantity: 1, adjustment_type: 'INCREASE', reason: '', reference_id: '' }
  });

  const idempotencyKeyRef = useRef('');

  useEffect(() => {
    if (isOpen) {
      reset({ quantity: 1, adjustment_type: 'INCREASE', reason: '', reference_id: '' });
      idempotencyKeyRef.current = window.crypto.randomUUID();
    }
  }, [isOpen, reset]);

  const onFormSubmit = (data) => {
    onSubmit({
      idempotency_key: idempotencyKeyRef.current,
      product_sku: inventoryRow.product?.sku,
      warehouse_id: inventoryRow.warehouse_id,
      quantity: parseInt(data.quantity, 10),
      adjustment_type: data.adjustment_type,
      reason: data.reason.trim(),
      reference_id: data.reference_id.trim() || undefined,
      admin_password: data.admin_password
    });
  };

  if (!inventoryRow) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Manual Inventory Adjustment" maxWidth="500px">
      <div className={styles.contextPanel}>
        <p><strong>SKU:</strong> {inventoryRow.product?.sku}</p>
        <p><strong>Product:</strong> {inventoryRow.product_name}</p>
        <p><strong>Warehouse:</strong> {inventoryRow.warehouse_name}</p>
        <p><strong>Current Available:</strong> {inventoryRow.available_qty}</p>
      </div>

      <form onSubmit={handleSubmit(onFormSubmit)} className={styles.form}>
        <div className={styles.inputGroup}>
          <label className={styles.label}>Adjustment Type</label>
          <select className={styles.select} {...register('adjustment_type')}>
            <option value="INCREASE">Increase Stock (Add)</option>
            <option value="DECREASE">Decrease Stock (Remove)</option>
          </select>
        </div>

        <Input 
          label="Quantity" 
          type="number"
          min="1"
          {...register('quantity', { required: 'Quantity is required', min: { value: 1, message: 'Must be at least 1' } })}
          error={errors.quantity}
        />

        <Input 
          label="Reason *" 
          {...register('reason', { required: 'Reason is required', validate: v => v.trim() !== '' || 'Cannot be empty' })}
          error={errors.reason}
        />

        <Input 
          label="Reference ID (Optional)" 
          placeholder="e.g. TICKET-123"
          {...register('reference_id')}
        />

        <Input 
          label="Admin Password *" 
          type="password"
          placeholder="Enter admin password"
          {...register('admin_password', { required: 'Admin password is required' })}
          error={errors.admin_password}
        />

        <div className={styles.actions}>
          <Button variant="secondary" onClick={onClose} type="button" disabled={isLoading}>Cancel</Button>
          <Button variant="primary" type="submit" isLoading={isLoading}>Submit Adjustment</Button>
        </div>
      </form>
    </Modal>
  );
};
