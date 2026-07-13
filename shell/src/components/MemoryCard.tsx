import React from 'react';
import { FileText, Video, File, Globe } from 'lucide-react';
import type { RegistryObject } from '../services/api';

import { Link } from 'react-router-dom';

interface MemoryCardProps {
  memory: RegistryObject;
}

export const MemoryCard: React.FC<MemoryCardProps> = ({ memory }) => {
  const { object_type, title, source_system, created_at, metadata_json, uuid } = memory;

  // Select appropriate icon
  const getIcon = () => {
    switch (object_type.toLowerCase()) {
      case 'video':
        return <Video className="w-5 h-5" />;
      case 'note':
        return <FileText className="w-5 h-5" />;
      case 'document':
        return <File className="w-5 h-5" />;
      default:
        return <Globe className="w-5 h-5" />;
    }
  };

  // Format metadata line
  const typeLabel = object_type.charAt(0).toUpperCase() + object_type.slice(1);
  const sourceLabel = source_system.charAt(0).toUpperCase() + source_system.slice(1);
  const year = created_at ? new Date(created_at).getFullYear() : new Date().getFullYear();

  // Try to parse tags from metadata_json
  let tags: string[] = [];
  try {
    const meta = JSON.parse(metadata_json || '{}');
    if (meta.tags && Array.isArray(meta.tags)) {
      tags = meta.tags;
    } else if (meta.provider) {
      tags.push(meta.provider);
    }
  } catch {
    // fallback
  }

  const isVideo = object_type.toLowerCase() === 'video';
  const styles = isVideo ? {
    iconColor: 'text-accent-video',
    iconBgHover: 'group-hover:bg-accent-video/10',
    titleHover: 'group-hover:text-accent-video',
    cardBorderHover: 'hover:border-accent-video/20'
  } : {
    iconColor: 'text-accent-memory',
    iconBgHover: 'group-hover:bg-accent-memory/10',
    titleHover: 'group-hover:text-accent-memory',
    cardBorderHover: 'hover:border-accent-memory/20'
  };

  return (
    <Link 
      to={`/memories/${uuid}`}
      className={`p-5 rounded-2xl border border-border-primary bg-surface-card transition-all duration-200 shadow-sm flex flex-col justify-between space-y-4 hover:shadow-md block cursor-pointer group ${styles.cardBorderHover}`}
    >
      <div>
        <div className="flex items-center space-x-2">
          <div className={`p-2 rounded-lg bg-background-primary transition-colors ${styles.iconColor} ${styles.iconBgHover}`}>
            {getIcon()}
          </div>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border shrink-0 ${
            isVideo 
              ? 'bg-accent-video/10 text-accent-video border-accent-video/15' 
              : 'bg-accent-memory/10 text-accent-memory border-accent-memory/15'
          }`}>
            {typeLabel} &bull; {sourceLabel} &bull; {year}
          </span>
        </div>
        <h4 className={`text-lg font-bold text-text-primary mt-3 leading-snug transition-colors ${styles.titleHover}`}>
          {title}
        </h4>
        {memory.description && (
          <p className="text-sm text-text-secondary mt-1.5 line-clamp-2 leading-relaxed">
            {memory.description}
          </p>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-2">
          {tags.map((tag, idx) => (
            <span 
              key={idx} 
              className="px-2.5 py-0.5 rounded-md text-xs font-medium bg-background-primary text-text-secondary border border-border-primary"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
};

