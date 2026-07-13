import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { WorkspaceLayout } from './components/WorkspaceLayout';
import { WorkspaceProvider } from './services/workspaceState';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <WorkspaceProvider>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<WorkspaceLayout />} />
            <Route path="memories" element={<WorkspaceLayout />} />
            <Route path="memories/:uuid" element={<WorkspaceLayout />} />
            <Route path="concepts" element={<WorkspaceLayout />} />
            <Route path="concepts/:name" element={<WorkspaceLayout />} />
            <Route path="graph" element={<WorkspaceLayout />} />
            <Route path="graph/:name" element={<WorkspaceLayout />} />
            <Route path="assistant" element={<WorkspaceLayout />} />
          </Route>
        </Routes>
      </WorkspaceProvider>
    </BrowserRouter>
  );
};

export default App;

