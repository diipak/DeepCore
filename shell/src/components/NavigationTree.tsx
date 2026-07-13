import React, { useEffect, useState } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { useWorkspace } from '../services/workspaceState';
import type { ThemeContextType } from './AppShell';
import { api } from '../services/api';
import type { RegistryObject, SystemStats } from '../services/api';
import { 
  BookOpen, Brain, Network, FileText, Video, Calendar, Mail, DollarSign, 
  Activity, Sun, Moon, FolderSync, Home, GitBranch, Globe
} from 'lucide-react';

export const NavigationTree: React.FC<{ className?: string }> = ({ className }) => {
  const { state } = useWorkspace();
  const navigate = useNavigate();
  const [recentItems, setRecentItems] = useState<RegistryObject[]>([]);
  const [loadingRecents, setLoadingRecents] = useState<boolean>(false);
  const [stats, setStats] = useState<SystemStats | null>(null);
  
  // Safe outlet context fetch for theme
  const themeContext = useOutletContext<ThemeContextType | null>();
  const isDark = themeContext?.isDark ?? false;
  const setIsDark = themeContext?.setIsDark ?? (() => {});

  const fetchRecentActivity = async () => {
    setLoadingRecents(true);
    try {
      const items = await api.getRecentMemories(5);
      setRecentItems(items);
    } catch (err) {
      console.error('Failed to load recent activity in sidebar', err);
    } finally {
      setLoadingRecents(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load system stats in sidebar', err);
    }
  };

  useEffect(() => {
    fetchRecentActivity();
    fetchStats();
  }, [state.selectedObjectId]); // Re-fetch when selection changes

  // Helper checks for active status
  const isSurfaceActive = (surface: string, sourceFilter?: string) => {
    if (state.activeSurface !== surface) return false;
    if (sourceFilter && state.activeSourceFilter !== sourceFilter) return false;
    if (!sourceFilter && state.activeSourceFilter) return false;
    return true;
  };

  const getMemoryIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'video':
        return <Video className="w-3.5 h-3.5 shrink-0 text-accent-video" />;
      case 'note':
        return <FileText className="w-3.5 h-3.5 shrink-0 text-accent-memory" />;
      default:
        return <BookOpen className="w-3.5 h-3.5 shrink-0 text-accent-memory" />;
    }
  };

  return (
    <aside className={`h-full flex flex-col border-r border-border-primary bg-surface-card p-5 justify-between select-none overflow-y-auto ${className || ''}`}>
      <div className="space-y-6">
        {/* Title Brand Header */}
        <div className="flex items-center space-x-2.5 px-1 py-2 cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-8 h-8 rounded-xl bg-accent-assistant flex items-center justify-center text-white font-bold text-base shadow-sm shadow-accent-assistant/20">
            D
          </div>
          <span className="font-extrabold text-lg tracking-tight text-text-primary">DeepCore</span>
        </div>

        {/* 1. KNOWLEDGE */}
        <div className="space-y-1.5">
          <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-2.5">
            Knowledge
          </h4>
          <div className="space-y-0.5">
            <button
              onClick={() => navigate('/')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                isSurfaceActive('home')
                  ? 'bg-accent-memory/10 text-accent-memory font-bold'
                  : 'text-text-secondary hover:bg-background-primary hover:text-text-primary'
              }`}
            >
              <Home className="w-4 h-4 shrink-0 text-accent-memory" />
              <span>Home / Awareness</span>
            </button>

            <button
              onClick={() => navigate('/memories')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                isSurfaceActive('memories') && !state.selectedObjectId
                  ? 'bg-accent-memory/10 text-accent-memory font-bold'
                  : 'text-text-secondary hover:bg-background-primary hover:text-text-primary'
              }`}
            >
              <BookOpen className="w-4 h-4 shrink-0 text-accent-memory" />
              <span>Memories</span>
            </button>
            
            <button
              onClick={() => navigate('/concepts')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                isSurfaceActive('concepts')
                  ? 'bg-accent-concept/10 text-accent-concept'
                  : 'text-text-secondary hover:bg-background-primary hover:text-text-primary'
              }`}
            >
              <Brain className="w-4 h-4 shrink-0 text-accent-concept" />
              <span>Concepts</span>
            </button>

            <button
              onClick={() => navigate('/graph')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                isSurfaceActive('graph')
                  ? 'bg-accent-concept/10 text-accent-concept'
                  : 'text-text-secondary hover:bg-background-primary hover:text-text-primary'
              }`}
            >
              <Network className="w-4 h-4 shrink-0 text-accent-concept" />
              <span>Graph Explorer</span>
            </button>
          </div>
        </div>

        {/* 2. SOURCES (PROVIDERS) */}
        <div className="space-y-1.5">
          <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-2.5">
            Sources
          </h4>
          <div className="space-y-0.5">
            {/* Obsidian */}
            <div className="group/src flex items-center justify-between w-full rounded-lg hover:bg-background-primary transition-all">
              <button
                onClick={() => navigate('/memories?source=markdown')}
                className={`flex-1 flex items-center space-x-3 px-3 py-2 text-xs font-semibold transition-all cursor-pointer text-left ${
                  isSurfaceActive('memories', 'markdown')
                    ? 'text-accent-memory font-bold'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <FileText className="w-4 h-4 shrink-0 text-accent-memory" />
                <span className="truncate">Obsidian Note</span>
              </button>
              <span className="text-[10px] text-text-secondary/60 mr-2 shrink-0 font-medium">
                {stats?.by_source?.markdown || 0} notes
              </span>
            </div>

            {/* YouTube */}
            <div className="group/src flex items-center justify-between w-full rounded-lg hover:bg-background-primary transition-all">
              <button
                onClick={() => navigate('/memories?source=youtube')}
                className={`flex-1 flex items-center space-x-3 px-3 py-2 text-xs font-semibold transition-all cursor-pointer text-left ${
                  isSurfaceActive('memories', 'youtube')
                    ? 'text-accent-video font-bold'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <Video className="w-4 h-4 shrink-0 text-accent-video" />
                <span className="truncate">YouTube Capture</span>
              </button>
              <span className="text-[10px] text-text-secondary/60 mr-2 shrink-0 font-medium">
                {stats?.by_source?.youtube || 0} memories
              </span>
            </div>

            {/* GitHub */}
            <div className="group/src flex items-center justify-between w-full rounded-lg hover:bg-background-primary transition-all">
              <button
                onClick={() => navigate('/memories?source=github')}
                className={`flex-1 flex items-center space-x-3 px-3 py-2 text-xs font-semibold transition-all cursor-pointer text-left ${
                  isSurfaceActive('memories', 'github')
                    ? 'text-accent-concept font-bold'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <GitBranch className="w-4 h-4 shrink-0 text-accent-concept" />
                <span className="truncate">GitHub</span>
              </button>
              <span className="text-[10px] text-text-secondary/60 mr-2 shrink-0 font-medium">
                {stats?.by_source?.github || 0} repositories
              </span>
            </div>

            {/* Web */}
            <div className="group/src flex items-center justify-between w-full rounded-lg hover:bg-background-primary transition-all">
              <button
                onClick={() => navigate('/memories?source=web')}
                className={`flex-1 flex items-center space-x-3 px-3 py-2 text-xs font-semibold transition-all cursor-pointer text-left ${
                  isSurfaceActive('memories', 'web')
                    ? 'text-accent-memory font-bold'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <Globe className="w-4 h-4 shrink-0 text-accent-memory" />
                <span className="truncate">Web</span>
              </button>
              <span className="text-[10px] text-text-secondary/60 mr-2 shrink-0 font-medium">
                {stats?.by_source?.web || 0} resources
              </span>
            </div>

            {/* Future Providers (Calendar, Mail, Finance, Fitness) */}
            <div className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-text-secondary/40 select-none cursor-not-allowed">
              <div className="flex items-center space-x-3">
                <Calendar className="w-4 h-4 shrink-0" />
                <span>Calendar Sync</span>
              </div>
              <span className="text-[8px] font-bold bg-background-primary text-text-secondary/30 px-1.5 py-0.5 rounded border border-border-primary">
                Soon
              </span>
            </div>

            <div className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-text-secondary/40 select-none cursor-not-allowed">
              <div className="flex items-center space-x-3">
                <Mail className="w-4 h-4 shrink-0" />
                <span>Email Mailbox</span>
              </div>
              <span className="text-[8px] font-bold bg-background-primary text-text-secondary/30 px-1.5 py-0.5 rounded border border-border-primary">
                Soon
              </span>
            </div>

            <div className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-text-secondary/40 select-none cursor-not-allowed">
              <div className="flex items-center space-x-3">
                <DollarSign className="w-4 h-4 shrink-0" />
                <span>Finance Portal</span>
              </div>
              <span className="text-[8px] font-bold bg-background-primary text-text-secondary/30 px-1.5 py-0.5 rounded border border-border-primary">
                Soon
              </span>
            </div>

            <div className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-text-secondary/40 select-none cursor-not-allowed">
              <div className="flex items-center space-x-3">
                <Activity className="w-4 h-4 shrink-0" />
                <span>Fitness Metrics</span>
              </div>
              <span className="text-[8px] font-bold bg-background-primary text-text-secondary/30 px-1.5 py-0.5 rounded border border-border-primary">
                Soon
              </span>
            </div>
          </div>
        </div>

        {/* 3. RECENT ACTIVITY */}
        <div className="space-y-1.5">
          <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-2.5 flex items-center justify-between">
            <span>Recent Activity</span>
            {loadingRecents && <FolderSync className="w-3 h-3 animate-spin text-text-secondary/50" />}
          </h4>
          <div className="space-y-0.5 px-1.5">
            {recentItems.length > 0 ? (
              recentItems.map((item) => {
                const isActive = state.selectedObjectId === item.uuid;
                const isVideo = item.object_type.toLowerCase() === 'video';
                const activeClasses = isVideo 
                  ? 'text-accent-video bg-accent-video/5 font-bold' 
                  : 'text-accent-memory bg-accent-memory/5 font-bold';
                return (
                  <button
                    key={item.id}
                    onClick={() => navigate(`/memories/${item.uuid}`)}
                    className={`w-full flex items-center space-x-2 py-1 px-1 rounded-md text-[10px] font-medium text-left transition-all truncate block cursor-pointer ${
                      isActive 
                        ? activeClasses 
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {getMemoryIcon(item.object_type)}
                    <span className="truncate flex-1">{item.title}</span>
                  </button>
                );
              })
            ) : !loadingRecents ? (
              <span className="text-[10px] italic text-text-secondary/50 px-1">
                No recent memories.
              </span>
            ) : null}
          </div>
        </div>
      </div>

      {/* Theme Toggler Button */}
      <button
        onClick={() => setIsDark(!isDark)}
        className="flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-semibold text-text-secondary hover:bg-background-primary hover:text-text-primary transition-all border border-border-primary w-full justify-center cursor-pointer mt-4"
      >
        {isDark ? (
          <>
            <Sun className="w-4 h-4" />
            <span>Light Mode</span>
          </>
        ) : (
          <>
            <Moon className="w-4 h-4" />
            <span>Dark Mode</span>
          </>
        )}
      </button>
    </aside>
  );
};
