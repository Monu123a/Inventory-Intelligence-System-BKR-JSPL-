import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { ROUTES } from '../../constants/routes';
import Button from '../../components/forms/Button';
import Input from '../../components/forms/Input';
import { Card } from '../../components/Card/Card';
import styles from './Login.module.css';

const Login = () => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('password');
  const setAuth = useAuthStore(state => state.setAuth);
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    // Mock login for demo purposes
    setAuth({ name: 'Admin User', role: 'Admin' }, 'mock-jwt-token-12345');
    navigate(ROUTES.OVERVIEW);
  };

  return (
    <div className={styles.container}>
      <Card className={styles.loginCard}>
        <div className={styles.header}>
          <h2>JSPL Inventory</h2>
          <p>Please log in to continue</p>
        </div>
        <form onSubmit={handleLogin} className={styles.form}>
          <Input 
            label="Username" 
            value={username} 
            onChange={(e) => setUsername(e.target.value)} 
          />
          <Input 
            label="Password" 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
          />
          <Button variant="primary" type="submit" style={{ width: '100%', marginTop: '1rem' }}>
            Login
          </Button>
        </form>
      </Card>
    </div>
  );
};

export default Login;
