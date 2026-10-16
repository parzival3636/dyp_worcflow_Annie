import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { CheckCircle, AlertTriangle, AlertCircle, Sparkles, Info } from 'lucide-react';

const ToastContext = createContext();

export function useToast() {
  return useContext(ToastContext);
}

const ICONS = {
  green: CheckCircle,
  red: AlertCircle,
  purple: Sparkles,
  blue: Info,
  amber: AlertTriangle,
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const addToast = useCallback((message, type = 'blue', duration = 5000) => {
    const id = ++idRef.current;
    setToasts(prev => {
      const next = [...prev, { id, message, type }];
      return next.slice(-3); // max 3 visible
    });
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, duration);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="toast-container">
        {toasts.map(t => {
          const Icon = ICONS[t.type] || Info;
          return (
            <div key={t.id} className={`toast toast-${t.type}`} onClick={() => removeToast(t.id)}>
              <Icon size={16} />
              <span>{t.message}</span>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
