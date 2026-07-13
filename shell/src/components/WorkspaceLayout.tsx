import React, { useState, useEffect } from 'react';
import { useWorkspace, WorkspaceRouteSync } from '../services/workspaceState';
import { NavigationTree } from './NavigationTree';
import { WorkspacePane } from './WorkspacePane';
import { AssistantPane } from './AssistantPane';
import { Menu, MessageSquare, BookOpen, X, PanelRightClose, PanelRight } from 'lucide-react';

export const WorkspaceLayout: React.FC = () => {
  const { state, toggleAssistant } = useWorkspace();
  const [mobileTab, setMobileTab] = useState<'workspace' | 'assistant'>('workspace');
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [windowWidth, setWindowWidth] = useState<number>(window.innerWidth);
  const [assistantWidth, setAssistantWidth] = useState<number>(() => {
    const saved = localStorage.getItem('deepcore_assistant_width');
    return saved ? parseInt(saved, 10) : 360;
  });

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = assistantWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = startX - moveEvent.clientX;
      const newWidth = Math.max(280, Math.min(600, startWidth + deltaX));
      setAssistantWidth(newWidth);
      localStorage.setItem('deepcore_assistant_width', newWidth.toString());
    };

    const handleMouseUp = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Auto-focus the workspace tab on mobile when an item is selected
  useEffect(() => {
    if (state.selectedObjectId || state.selectedConcept) {
      setMobileTab('workspace');
    }
  }, [state.selectedObjectId, state.selectedConcept]);

  // Clean modal navigation toggle helper
  const handleMobileNavClick = () => {
    setMobileMenuOpen(false);
  };

  const isMobile = windowWidth < 768;

  // 1. MOBILE RENDERING BRANCH (< 768px)
  if (isMobile) {
    return (
      <div className="h-screen w-screen overflow-hidden flex flex-col bg-background-primary text-text-primary">
        <WorkspaceRouteSync />
        {/* Mobile Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-border-primary bg-surface-card shrink-0 z-20">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-1.5 rounded-lg border border-border-primary text-text-secondary bg-surface-card hover:text-text-primary cursor-pointer"
          >
            <Menu className="w-5 h-5" />
          </button>

          <span className="font-extrabold text-base tracking-tight text-text-primary">DeepCore</span>

          <button
            onClick={() => setMobileTab('assistant')}
            className={`p-1.5 rounded-lg border text-text-secondary bg-surface-card hover:text-text-primary cursor-pointer ${
              mobileTab === 'assistant' ? 'border-accent-assistant text-accent-assistant bg-accent-assistant/5' : 'border-border-primary'
            }`}
          >
            <MessageSquare className="w-5 h-5" />
          </button>
        </header>

        {/* Mobile Viewport Panes Content Area (Only ONE pane exists in DOM at a time) */}
        <div className="flex-1 min-h-0 w-full overflow-hidden">
          {mobileTab === 'workspace' && <WorkspacePane className="w-full h-full overflow-y-auto" />}
          {mobileTab === 'assistant' && <AssistantPane className="w-full h-full" />}
        </div>

        {/* Mobile Bottom Navigation Tab Bar */}
        <nav className="flex border-t border-border-primary bg-surface-card py-2 justify-around shrink-0 z-20 shadow-lg shadow-black/5">
          <button
            onClick={() => setMobileTab('workspace')}
            className={`flex flex-col items-center py-1.5 px-4 rounded-xl text-[10px] font-bold transition-all cursor-pointer ${
              mobileTab === 'workspace' ? 'text-accent-primary' : 'text-text-secondary'
            }`}
          >
            <BookOpen className="w-5 h-5" />
            <span className="mt-1">Workspace</span>
          </button>

          <button
            onClick={() => setMobileTab('assistant')}
            className={`flex flex-col items-center py-1.5 px-4 rounded-xl text-[10px] font-bold transition-all cursor-pointer ${
              mobileTab === 'assistant' ? 'text-accent-assistant' : 'text-text-secondary'
            }`}
          >
            <MessageSquare className="w-5 h-5" />
            <span className="mt-1">Assistant</span>
          </button>
        </nav>

        {/* Mobile NavigationTree Drawer Sheet (Slide-in Modal Overlay) */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-30 flex">
            {/* Backdrop blur element */}
            <div
              className="fixed inset-0 bg-black/40 backdrop-blur-xs"
              onClick={() => setMobileMenuOpen(false)}
            />
            {/* Drawer layout */}
            <div className="relative flex flex-col w-64 max-w-xs h-full bg-surface-card border-r border-border-primary shadow-xl animate-slide-right">
              {/* Close Button */}
              <div className="absolute top-3.5 right-3.5 z-40">
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1 rounded-lg text-text-secondary hover:text-text-primary hover:bg-background-primary cursor-pointer border border-border-primary"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 h-full flex flex-col" onClick={handleMobileNavClick}>
                <NavigationTree className="w-full" />
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 2. DESKTOP/TABLET RENDERING BRANCH (>= 768px)
  return (
    <div className="h-screen w-screen overflow-hidden flex bg-background-primary text-text-primary">
      <WorkspaceRouteSync />
      {/* Navigation Tree Column (Pane 1) */}
      <NavigationTree className="w-[240px] flex-shrink-0" />

      {/* Workspace Pane Column Container (Pane 2) */}
      <div className="flex-1 min-w-0 h-full relative flex flex-col">
        {/* Context Assistant toggle button hovering in top-right of main content area */}
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={toggleAssistant}
            title={state.assistantVisible ? "Collapse Assistant" : "Expand Assistant"}
            className="p-2 rounded-xl border border-border-primary/80 bg-surface-card/90 shadow-sm text-text-secondary hover:text-text-primary hover:bg-background-primary transition-all cursor-pointer"
          >
            {state.assistantVisible ? <PanelRightClose className="w-4 h-4" /> : <PanelRight className="w-4 h-4" />}
          </button>
        </div>
        <WorkspacePane className="flex-1 min-w-0 overflow-y-auto" />
      </div>

      {/* Assistant Pane Column (Pane 3) */}
      {state.assistantVisible && (
        <div style={{ width: `${assistantWidth}px` }} className="flex-shrink-0 relative h-full flex select-none">
          {/* Draggable Resizer handle */}
          <div
            onMouseDown={handleMouseDown}
            className="absolute top-0 left-0 -ml-1 w-2 h-full cursor-col-resize hover:bg-accent-assistant/20 active:bg-accent-assistant/40 transition-colors z-30"
          />
          <AssistantPane className="w-full h-full" />
        </div>
      )}
    </div>
  );
};
