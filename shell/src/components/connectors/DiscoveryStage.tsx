import React, { useEffect, useState } from 'react';
import { Folder, Video, Calendar, Search, ShieldCheck, Database, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import type { CapabilitySummary } from '../../services/api';

interface DiscoveryStageProps {
  onSelect: (providerId: string) => void;
}

export const DiscoveryStage: React.FC<DiscoveryStageProps> = ({ onSelect }) => {
  const [capabilities, setCapabilities] = useState<CapabilitySummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchCapabilities = async () => {
      try {
        setLoading(true);
        const data = await api.getProviderCapabilities();
        if (isMounted) {
          setCapabilities(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          console.error('Failed to load provider capabilities', err);
          setError('Failed to load available connectors.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    fetchCapabilities();
    return () => {
      isMounted = false;
    };
  }, []);

  const renderIcon = (iconName?: string) => {
    switch (iconName) {
      case 'Folder':
        return <Folder className="w-6 h-6" />;
      case 'Video':
        return <Video className="w-6 h-6" />;
      case 'Calendar':
        return <Calendar className="w-6 h-6" />;
      case 'Search':
        return <Search className="w-6 h-6" />;
      default:
        return <Database className="w-6 h-6" />;
    }
  };

  const getAccentStyles = (accentColor?: string) => {
    switch (accentColor) {
      case 'accent-memory':
        return 'bg-accent-memory/10 text-accent-memory group-hover:bg-accent-memory/25';
      case 'accent-video':
        return 'bg-accent-video/10 text-accent-video';
      case 'accent-concept':
        return 'bg-accent-concept/10 text-accent-concept';
      case 'accent-assistant':
        return 'bg-accent-primary/10 text-accent-primary';
      default:
        return 'bg-accent-primary/10 text-accent-primary';
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="text-center max-w-md mx-auto space-y-2">
        <ShieldCheck className="w-12 h-12 text-accent-primary mx-auto" />
        <h2 className="text-2xl font-bold tracking-tight text-text-primary">Connect Knowledge Source</h2>
        <p className="text-sm text-text-secondary">
          DeepCore is a private offline workspace. Select a source to onboard a trusted connector.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12 text-text-secondary">
          <Loader2 className="w-6 h-6 animate-spin mr-2 text-accent-primary" />
          <span className="text-sm">Discovering capabilities...</span>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-status-error/10 border border-status-error/20 text-status-error text-center text-sm max-w-md mx-auto">
          {error}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl mx-auto">
          {capabilities.map((cap) => {
            const isAvailable = cap.availability_state === 'available' && cap.configurable && cap.enabled;
            const badgeLabel =
              cap.availability_state === 'coming_soon'
                ? 'Soon'
                : cap.availability_state === 'disabled'
                ? 'Disabled'
                : null;

            if (isAvailable) {
              return (
                <button
                  key={cap.id}
                  onClick={() => onSelect(cap.id)}
                  className="flex items-start space-x-4 p-5 rounded-2xl border border-border-primary bg-surface-card hover:border-accent-primary hover:bg-background-primary/5 transition-all text-left group cursor-pointer w-full"
                >
                  <div className={`p-3 rounded-xl transition-all ${getAccentStyles(cap.accent_color)}`}>
                    {renderIcon(cap.icon)}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-sm text-text-primary">{cap.name}</h3>
                    <p className="text-xs text-text-secondary mt-1">{cap.description}</p>
                  </div>
                </button>
              );
            }

            return (
              <div
                key={cap.id}
                className="flex items-start space-x-4 p-5 rounded-2xl border border-border-primary/50 bg-surface-card/65 opacity-60 text-left select-none"
              >
                <div className={`p-3 rounded-xl ${getAccentStyles(cap.accent_color)}`}>
                  {renderIcon(cap.icon)}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-sm text-text-primary flex items-center space-x-1.5">
                    <span>{cap.name}</span>
                    {badgeLabel && (
                      <span className="text-[8px] bg-border-primary text-text-secondary px-1.5 py-0.5 rounded font-bold uppercase">
                        {badgeLabel}
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-text-secondary mt-1">{cap.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
