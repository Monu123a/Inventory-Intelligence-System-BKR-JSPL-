import React from 'react';
import { useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useQueryClient } from '@tanstack/react-query';
import { FiBox } from 'react-icons/fi';
import { companyService } from '../../services/companies';
import useCompanyStore from '../../stores/useCompanyStore';
import styles from './CompanySelector.module.css';

// Fallback companies used only if the API fails to fetch the companies list
const FALLBACK_COMPANIES = [
  { id: 3, code: 'JSPL', name: 'JSPL' },
  { id: 2, code: 'BKR', name: 'BKR' },
];

const CompanySelector = () => {
  const queryClient = useQueryClient();
  const { companyId, companyCode, currentCompany, setCompany } = useCompanyStore();
  
  const { data: companies, isLoading, error } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companyService.getCompanies(),
  });

  const availableCompanies = companies?.length ? companies : FALLBACK_COMPANIES;
  const selectedCompany = useMemo(() => (
    availableCompanies.find((company) => company.id === companyId) ||
    availableCompanies.find((company) => company.code === companyCode) ||
    availableCompanies.find((company) => company.id === currentCompany?.id) ||
    availableCompanies.find((company) => company.code === currentCompany?.code) ||
    FALLBACK_COMPANIES[0]
  ), [availableCompanies, companyId, currentCompany, companyCode]);

  useEffect(() => {
    if (
      selectedCompany &&
      (currentCompany?.id !== selectedCompany.id ||
        currentCompany?.code !== selectedCompany.code ||
        currentCompany?.name !== selectedCompany.name ||
        !currentCompany?.legal_name)
    ) {
      setCompany(selectedCompany.id, selectedCompany.code, selectedCompany.name, selectedCompany);
    }
  }, [currentCompany?.code, currentCompany?.id, currentCompany?.name, currentCompany?.legal_name, selectedCompany, setCompany]);

  const handleChange = (e) => {
    const newId = parseInt(e.target.value, 10);
    const selected = availableCompanies.find((company) => company.id === newId);
    setCompany(newId, selected?.code || '', selected?.name || selected?.code || '', selected);
    queryClient.invalidateQueries();
  };
  
  let badgeClass = styles.badgeDefault;
  if (selectedCompany) {
    if (selectedCompany.code === 'JSPL') badgeClass = styles.badgeJSPL;
    else if (selectedCompany.code === 'BKR') badgeClass = styles.badgeBKR;
  }

  return (
    <div className={styles.selectorWrapper}>
      <div className={`${styles.iconWrapper} ${badgeClass}`} title={selectedCompany?.name || 'Current company'}>
        <FiBox size={14} />
      </div>
      <div className={styles.selectContainer}>
        <span className={styles.label}>Company</span>
        <select 
          className={styles.select} 
          value={selectedCompany?.id ?? FALLBACK_COMPANIES[0].id}
          onChange={handleChange}
          aria-label="Select company"
        >
          {availableCompanies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name} ({company.code})
            </option>
          ))}
        </select>
      </div>
      {isLoading && <span className={styles.status}>Loading...</span>}
      {error && !companies?.length && <span className={styles.status}>Offline list</span>}
    </div>
  );
};

export default CompanySelector;
