import React from 'react';
import { WorkspaceRouteSync } from '../services/workspaceState';
import { AssistantPane } from './AssistantPane';

export const WorkspaceLayout: React.FC = () => {
  return (
    <div className="h-screen h-[100dvh] w-full overflow-hidden flex bg-background-primary text-text-primary">
      <WorkspaceRouteSync />
      {/* Full-viewport AssistantPane + WorkspaceCanvas */}
      <AssistantPane className="w-full h-full flex-1" />
    </div>
  );
};
