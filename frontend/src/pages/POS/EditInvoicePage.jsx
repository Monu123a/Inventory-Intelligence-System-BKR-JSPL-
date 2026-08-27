import React from 'react';
import { useParams } from 'react-router-dom';
import EditInvoicePageImpl from './EditInvoicePageImpl';

class LocalErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  componentDidCatch(error, info) {
    this.setState({ error, info });
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', color: 'red', background: '#fff', minHeight: '100vh' }}>
          <h2>Inner Component Crashed:</h2>
          <pre>{this.state.error && this.state.error.toString()}</pre>
          <pre>{this.state.info && this.state.info.componentStack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function EditInvoicePage() {
  return (
    <LocalErrorBoundary>
      <EditInvoicePageImpl />
    </LocalErrorBoundary>
  );
}
