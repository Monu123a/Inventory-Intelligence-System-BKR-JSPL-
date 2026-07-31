import { create } from 'zustand';

export const useUIStore = create((set) => ({
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  
  isLoadingOverlayActive: false,
  loadingOverlayMessage: '',
  showLoadingOverlay: (message = 'Loading...') => set({ isLoadingOverlayActive: true, loadingOverlayMessage: message }),
  hideLoadingOverlay: () => set({ isLoadingOverlayActive: false, loadingOverlayMessage: '' }),
}));
