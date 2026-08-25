import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set) => ({
  user: null,
  token: (localStorage.getItem('token') && localStorage.getItem('token') !== 'null' && localStorage.getItem('token') !== 'undefined') ? localStorage.getItem('token') : null,
  isAuthenticated: !!(localStorage.getItem('token') && localStorage.getItem('token') !== 'null' && localStorage.getItem('token') !== 'undefined'),
  setAuth: (user, token) => {
    if (!token) {
      localStorage.removeItem('token');
      set({ user: null, token: null, isAuthenticated: false });
      return;
    }
    localStorage.setItem('token', token);
    set({ user, token, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('company-storage');
    set({ user: null, token: null, isAuthenticated: false });
  },
    }),
    {
      name: 'auth-storage',
    }
  )
);
