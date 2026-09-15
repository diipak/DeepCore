import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';

export interface WorkspaceState {
  activeSurface: 'home' | 'memories' | 'concepts' | 'graph' | 'assistant' | 'system' | 'platform';
  activeTypeFilter: string; // 'all', 'note', 'video', etc.
  activeSourceFilter: string | null;
  selectedObjectId: string | null;
  selectedConcept: string | null;
  assistantVisible: boolean;
}

interface WorkspaceContextType {
  state: WorkspaceState;
  setActiveSurface: (surface: WorkspaceState['activeSurface']) => void;
  setActiveTypeFilter: (type: string) => void;
  setActiveSourceFilter: (source: string | null) => void;
  setSelectedObjectId: (id: string | null) => void;
  setSelectedConcept: (conceptName: string | null) => void;
  setAssistantVisible: (visible: boolean) => void;
  toggleAssistant: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<WorkspaceState>({
    activeSurface: 'home',
    activeTypeFilter: 'all',
    activeSourceFilter: null,
    selectedObjectId: null,
    selectedConcept: null,
    assistantVisible: true
  });

  const setActiveSurface = useCallback((activeSurface: WorkspaceState['activeSurface']) => {
    setState(prev => prev.activeSurface === activeSurface ? prev : { ...prev, activeSurface });
  }, []);

  const setActiveTypeFilter = useCallback((activeTypeFilter: string) => {
    setState(prev => prev.activeTypeFilter === activeTypeFilter ? prev : { ...prev, activeTypeFilter });
  }, []);

  const setActiveSourceFilter = useCallback((activeSourceFilter: string | null) => {
    setState(prev => prev.activeSourceFilter === activeSourceFilter ? prev : { ...prev, activeSourceFilter });
  }, []);

  const setSelectedObjectId = useCallback((selectedObjectId: string | null) => {
    setState(prev => prev.selectedObjectId === selectedObjectId ? prev : { ...prev, selectedObjectId });
  }, []);

  const setSelectedConcept = useCallback((selectedConcept: string | null) => {
    setState(prev => prev.selectedConcept === selectedConcept ? prev : { ...prev, selectedConcept });
  }, []);

  const setAssistantVisible = useCallback((assistantVisible: boolean) => {
    setState(prev => prev.assistantVisible === assistantVisible ? prev : { ...prev, assistantVisible });
  }, []);

  const toggleAssistant = useCallback(() => {
    setState(prev => ({ ...prev, assistantVisible: !prev.assistantVisible }));
  }, []);

  return (
    <WorkspaceContext.Provider value={{ 
      state, 
      setActiveSurface, 
      setActiveTypeFilter, 
      setActiveSourceFilter,
      setSelectedObjectId, 
      setSelectedConcept, 
      setAssistantVisible, 
      toggleAssistant
    }}>
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};

// Route synchronization adapter for React Router (decoupled from hooks like useParams)
export const WorkspaceRouteSync: React.FC = () => {
  const location = useLocation();
  const { 
    setActiveSurface, 
    setActiveTypeFilter, 
    setActiveSourceFilter,
    setSelectedObjectId, 
    setSelectedConcept 
  } = useWorkspace();

  useEffect(() => {
    const pathname = location.pathname;
    const searchParams = new URLSearchParams(location.search);
    
    let activeSurface: WorkspaceState['activeSurface'] = 'home';
    let selectedObjectId: string | null = null;
    let selectedConcept: string | null = null;

    if (pathname === '/') {
      activeSurface = 'home';
    } else if (pathname.startsWith('/system')) {
      activeSurface = 'system';
    } else if (pathname.startsWith('/platform')) {
      activeSurface = 'platform';
    } else if (pathname.startsWith('/memories')) {
      activeSurface = 'memories';
      const parts = pathname.split('/');
      if (parts.length > 2 && parts[2]) {
        selectedObjectId = parts[2];
      }
    } else if (pathname.startsWith('/concepts')) {
      activeSurface = 'concepts';
      const parts = pathname.split('/');
      if (parts.length > 2 && parts[2]) {
        selectedConcept = decodeURIComponent(parts[2]);
      }
    } else if (pathname.startsWith('/graph')) {
      activeSurface = 'graph';
      const parts = pathname.split('/');
      if (parts.length > 2 && parts[2]) {
        selectedConcept = decodeURIComponent(parts[2]);
      }
    } else if (pathname.startsWith('/assistant')) {
      activeSurface = 'assistant';
    }

    const typeFilter = searchParams.get('type') || 'all';
    const sourceFilter = searchParams.get('source') || null;

    console.log("[WorkspaceRouteSync] pathname:", pathname);
    console.log("[WorkspaceRouteSync] extracted selectedObjectId:", selectedObjectId);
    console.log("[WorkspaceRouteSync] extracted selectedConcept:", selectedConcept);
    console.log("[WorkspaceRouteSync] activeSurface:", activeSurface);

    setActiveSurface(activeSurface);
    setActiveTypeFilter(typeFilter);
    setActiveSourceFilter(sourceFilter);
    setSelectedObjectId(selectedObjectId);
    setSelectedConcept(selectedConcept);
  }, [location.pathname, location.search, setActiveSurface, setActiveTypeFilter, setActiveSourceFilter, setSelectedObjectId, setSelectedConcept]);

  return null;
};
