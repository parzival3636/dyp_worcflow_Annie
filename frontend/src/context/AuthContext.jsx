import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiGet, apiPost } from '../hooks/useSnapshot';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const data = await apiGet('/auth/me');
      setUser(data);
      return data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email, password) => {
    const data = await apiPost('/auth/login', { email, password });
    setUser(data);
    return data;
  };

  const signup = async ({ email, password, name, role = 'leader' }) => {
    const data = await apiPost('/auth/signup', { email, password, name, role });
    setUser(data);
    return data;
  };

  const logout = async () => {
    try {
      await apiPost('/auth/logout');
    } catch {
      // ignore
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
