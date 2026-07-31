import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import Input from '../../../components/forms/Input';
import styles from './ProductFormModal.module.css';

export const ProductFormModal = ({ isOpen, onClose, onSubmit, initialData = null, isLoading = false }) => {
  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    defaultValues: initialData || {
      sku: '', name: '', category: '', brand: '', hsn: '', barcode: '', unit: '', min_stock_level: 0, item_rate: 0, status: 'Active'
    }
  });

  useEffect(() => {
    if (isOpen) {
      reset(initialData || {
        sku: '', name: '', category: '', brand: '', hsn: '', barcode: '', unit: '', min_stock_level: 0, item_rate: 0, status: 'Active'
      });
    }
  }, [isOpen, initialData, reset]);

  const onFormSubmit = (data) => {
    // Trim string inputs
    const processed = {
      ...data,
      sku: data.sku.trim(),
      name: data.name.trim(),
      category: data.category?.trim() || '',
      brand: data.brand?.trim() || '',
      hsn: data.hsn?.trim() || '',
      barcode: data.barcode?.trim() || '',
      unit: data.unit?.trim() || '',
      min_stock_level: parseInt(data.min_stock_level, 10) || 0,
      item_rate: parseFloat(data.item_rate) || 0.0,
    };
    onSubmit(processed);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={initialData ? "Edit Product" : "Create Product"} maxWidth="600px">
      <form onSubmit={handleSubmit(onFormSubmit)} className={styles.form}>
        <div className={styles.grid}>
          <Input 
            label="SKU *" 
            {...register('sku', { required: 'SKU is required', validate: v => v.trim() !== '' || 'Cannot be empty' })}
            error={errors.sku}
            disabled={!!initialData}
          />
          <Input 
            label="Product Name *" 
            {...register('name', { required: 'Name is required', validate: v => v.trim() !== '' || 'Cannot be empty' })}
            error={errors.name}
          />
          <Input 
            label="Category" 
            {...register('category')}
          />
          <Input 
            label="Brand" 
            {...register('brand')}
          />
          <Input 
            label="HSN Code" 
            {...register('hsn', { pattern: { value: /^[0-9]*$/, message: 'HSN must be numeric' } })}
            error={errors.hsn}
          />
          <Input 
            label="Barcode" 
            {...register('barcode')}
          />
          <Input 
            label="Unit (e.g., PCS, KG)" 
            {...register('unit')}
          />
          <div className={styles.inputGroup}>
            <label className={styles.label}>Status</label>
            <select className={styles.select} {...register('status')}>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>
          <Input 
            label="Min Stock Level" 
            type="number" 
            min="0"
            {...register('min_stock_level', { valueAsNumber: true, min: { value: 0, message: 'Cannot be negative' } })}
            error={errors.min_stock_level}
          />
          <Input 
            label="Item Rate" 
            type="number" 
            min="0"
            step="0.01"
            {...register('item_rate', { valueAsNumber: true, min: { value: 0, message: 'Cannot be negative' } })}
            error={errors.item_rate}
          />
        </div>
        
        <div className={styles.actions}>
          <Button variant="secondary" onClick={onClose} type="button" disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" isLoading={isLoading}>
            {initialData ? 'Save Changes' : 'Create Product'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
