import React from 'react';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FiBox } from 'react-icons/fi';
import { getCompanies } from '../../services/companies';
import useCompanyStore from '../../stores/useCompanyStore';
import styles from './CompanySelector.module.css';

const FALLBACK_COMPANIES = [
  { id: 1, code: 'JSPL', name: 'JSPL' },
  { id: 2, code: 'BKR', name: 'BKR' },
];

const CompanySelector = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { companyId, companyCode, currentCompany, setCompany } = useCompanyStore();
  
  const { data: companies, isLoading, error } = useQuery({
    queryKey: ['companies'],
    queryFn: getCompanies,
  });

  const availableCompanies = companies?.length ? companies : FALLBACK_COMPANIES;
  const selectedCompany =
    availableCompanies.find((company) => company.id === companyId) ||
    currentCompany ||
    availableCompanies.find((company) => company.code === companyCode) ||
    FALLBACK_COMPANIES[0];

  useEffect(() => {
    if (
      selectedCompany &&
      (currentCompany?.id !== selectedCompany.id ||
        currentCompany?.code !== selectedCompany.code ||
        currentCompany?.name !== selectedCompany.name)
    ) {
      setCompany(selectedCompany.id, selectedCompany.code, selectedCompany.name);
    }
  }, [currentCompany?.code, currentCompany?.id, currentCompany?.name, selectedCompany, setCompany]);

  const handleChange = (e) => {
    const newId = parseInt(e.target.value, 10);
    const selected = availableCompanies.find((company) => company.id === newId);
    setCompany(newId, selected?.code || '', selected?.name || selected?.code || '');
    queryClient.invalidateQueries();
    navigate('/');
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
