import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';

export interface ThemeContextType {
  isDark: boolean;
  setIsDark: (dark: boolean) => void;
}

export const AppShell: React.FC = () => {
  const [isDark, setIsDark] = useState<boolean>(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  return (
    <div className="min-h-screen flex flex-col bg-background-primary text-text-primary">
      <Outlet context={{ isDark, setIsDark } satisfies ThemeContextType} />
    </div>
  );
};

