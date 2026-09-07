import React from 'react';
import styles from './ErrorBoundary.module.css';
import Button from '../forms/Button';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.container}>
          <div className={styles.content}>
            <h2 className={styles.title}>Something went wrong</h2>
            <p className={styles.message}>
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <Button onClick={() => window.location.reload()} variant="primary">
              Refresh Page
            </Button>
            <div style={{marginTop: '20px', padding: '10px', backgroundColor: '#fee2e2', borderRadius: '8px', color: '#991b1b', textAlign: 'left', overflowX: 'auto'}}>
              <h4 style={{margin: '0 0 10px 0'}}>Error Details (Please copy this for support):</h4>
              <pre className={styles.debug} style={{margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all'}}>{this.state.error?.toString()}</pre>
              <pre className={styles.debug} style={{margin: '10px 0 0 0', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '11px'}}>{this.state.errorInfo?.componentStack}</pre>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
