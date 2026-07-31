import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Modal } from '../../../components/Modal/Modal';
import Button from '../../../components/forms/Button';
import Input from '../../../components/forms/Input';
import styles from './WarehouseFormModal.module.css';

export const WarehouseFormModal = ({ isOpen, onClose, onSubmit, initialData = null, isLoading = false }) => {
  const isEdit = !!initialData;
  
  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    defaultValues: {
      name: '',
      code: '',
      status: 'Active',
      address: '',
      contact_person: '',
      phone_number: '',
      email: ''
    }
  });

  useEffect(() => {
    if (isOpen) {
      if (isEdit && initialData) {
        reset({
          name: initialData.name,
          code: initialData.code,
          status: initialData.status,
          address: initialData.address || '',
          contact_person: initialData.contact_person || '',
          phone_number: initialData.phone_number || '',
          email: initialData.email || ''
        });
      } else {
        reset({
          name: '',
          code: '',
          status: 'Active',
          address: '',
          contact_person: '',
          phone_number: '',
          email: ''
        });
      }
    }
  }, [isOpen, isEdit, initialData, reset]);

  const onFormSubmit = (data) => {
    const trimmedData = {
      ...data,
      name: data.name.trim(),
      code: data.code.trim().toUpperCase(),
      address: data.address.trim(),
      contact_person: data.contact_person.trim(),
      phone_number: data.phone_number.trim(),
      email: data.email.trim(),
    };
    onSubmit(trimmedData);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={isEdit ? 'Edit Warehouse' : 'Add Warehouse'} maxWidth="600px">
      <form onSubmit={handleSubmit(onFormSubmit)} className={styles.form}>
        <div className={styles.grid}>
          <Input 
            label="Warehouse Name *" 
            {...register('name', { required: 'Warehouse Name is required', validate: v => v.trim() !== '' || 'Cannot be empty' })}
            error={errors.name}
          />
          <Input 
            label="Warehouse Code *" 
            {...register('code', { required: 'Warehouse Code is required', validate: v => v.trim() !== '' || 'Cannot be empty' })}
            error={errors.code}
            disabled={isEdit} // Immutable after creation
            placeholder="e.g. WH-01"
            style={{ textTransform: 'uppercase' }}
          />
        </div>
        
        <Input 
          label="Address" 
          {...register('address')}
        />
        
        <div className={styles.grid}>
          <Input 
            label="Contact Person" 
            {...register('contact_person')}
          />
          <div className={styles.inputGroup}>
            <label className={styles.label}>Status</label>
            <select className={styles.select} {...register('status')}>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>
        </div>

        <div className={styles.grid}>
          <Input 
            label="Phone Number" 
            {...register('phone_number', {
              pattern: {
                value: /^[\d\s+\-()]*$/,
                message: 'Invalid phone format'
              }
            })}
            error={errors.phone_number}
          />
          <Input 
            label="Email" 
            {...register('email', {
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: "Invalid email format"
              }
            })}
            error={errors.email}
          />
        </div>

        <div className={styles.actions}>
          <Button variant="secondary" onClick={onClose} type="button" disabled={isLoading}>Cancel</Button>
          <Button variant="primary" type="submit" isLoading={isLoading}>{isEdit ? 'Save Changes' : 'Create Warehouse'}</Button>
        </div>
      </form>
    </Modal>
  );
};
