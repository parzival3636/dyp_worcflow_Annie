import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { ToastProvider } from './components/ToastProvider';
import './index.css';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled UI error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '40px 24px',
          maxWidth: '600px',
          margin: '60px auto',
          background: '#FFFFFF',
          border: '1px solid #DFE1E6',
          borderRadius: '4px',
          boxShadow: '0 4px 12px rgba(9, 30, 66, 0.15)',
          fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'
        }}>
          <h2 style={{ color: '#DE350B', marginBottom: '12px', fontSize: '18px' }}>Something went wrong</h2>
          <p style={{ color: '#42526E', fontSize: '14px', marginBottom: '16px' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: '#0052CC',
              color: '#FFFFFF',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '3px',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <App />
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
