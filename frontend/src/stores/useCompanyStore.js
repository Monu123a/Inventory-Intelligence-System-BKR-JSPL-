import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const DEFAULT_COMPANY = {
  id: 3,
  code: 'JSPL',
  name: 'JSPL',
};

const useCompanyStore = create(
  persist(
    (set) => ({
      // Default to JSPL (Company ID 1) if nothing is selected
      companyId: DEFAULT_COMPANY.id,
      companyCode: DEFAULT_COMPANY.code,
      currentCompany: DEFAULT_COMPANY,
      setCompany: (id, code, name, fullObj = null) =>
        set({
          companyId: id,
          companyCode: code,
          currentCompany: fullObj || {
            id,
            code,
            name: name || code || `Company ${id}`,
          },
        }),
      // Keep backward compat
      setCompanyId: (id) =>
        set((state) => ({
          companyId: id,
          currentCompany:
            state.currentCompany?.id === id
              ? state.currentCompany
              : {
                  id,
                  code: state.companyCode || '',
                  name: state.currentCompany?.name || state.companyCode || `Company ${id}`,
                },
        })),
    }),
    {
      name: 'company-storage',
    }
  )
);

export default useCompanyStore;
