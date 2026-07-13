import React from 'react';
import * as Icons from 'lucide-react';

interface StatCardProps {
  title: string;
  count: number;
  iconName: keyof typeof Icons;
}

export const StatCard: React.FC<StatCardProps> = ({ title, count, iconName }) => {
  const IconComponent = Icons[iconName] as React.ComponentType<{ className?: string }>;

  return (
    <div className="p-5 rounded-2xl border border-border-primary bg-surface-card transition-all duration-200 shadow-sm flex items-center space-x-4">
      <div className="p-3 rounded-xl bg-background-primary text-accent-primary">
        {IconComponent && <IconComponent className="w-6 h-6" />}
      </div>
      <div>
        <p className="text-sm font-medium text-text-secondary uppercase tracking-wider">{title}</p>
        <p className="text-3xl font-bold text-text-primary mt-1">{count}</p>
      </div>
    </div>
  );
};
