import { create } from 'zustand';

export const useApprovalStore = create((set) => ({
  isOpen: false,
  requestType: '',
  payload: null,
  openModal: (requestType, payload) => set({ isOpen: true, requestType, payload }),
  closeModal: () => set({ isOpen: false, requestType: '', payload: null }),
}));
