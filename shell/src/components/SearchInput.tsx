import React from 'react';
import { Search } from 'lucide-react';

interface SearchInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  onSearch?: (value: string) => void;
}

export const SearchInput: React.FC<SearchInputProps> = ({ onSearch, className, ...props }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onSearch) {
      onSearch(e.target.value);
    }
  };

  return (
    <div className={`relative w-full max-w-md ${className || ''}`}>
      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-text-secondary">
        <Search className="w-5 h-5" />
      </div>
      <input
        type="text"
        className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-border-primary bg-surface-card text-text-primary placeholder-text-secondary/70 focus:outline-none focus:ring-2 focus:ring-accent-primary/25 focus:border-accent-primary transition-all text-sm shadow-sm"
        onChange={handleChange}
        {...props}
      />
    </div>
  );
};
