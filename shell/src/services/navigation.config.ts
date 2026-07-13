export interface NavItemConfig {
  id: string;
  label: string;
  icon: string;
  path: string;
}

export interface NavGroupConfig {
  id: string;
  label: string;
  items: NavItemConfig[];
}

export const navigationConfig: NavGroupConfig[] = [
  {
    id: 'knowledge',
    label: 'Knowledge',
    items: [
      { id: 'memories', label: 'Memories', icon: 'BookOpen', path: '/memories' },
      { id: 'notes', label: 'Notes', icon: 'FileText', path: '/memories?type=note' },
      { id: 'videos', label: 'Videos', icon: 'Video', path: '/memories?type=video' },
      { id: 'concepts', label: 'Concepts', icon: 'Brain', path: '/concepts' }
    ]
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      { id: 'graph', label: 'Graph Explorer', icon: 'Network', path: '/graph' },
      { id: 'assistant', label: 'Assistant', icon: 'MessageSquare', path: '/assistant' }
    ]
  },
  {
    id: 'extensions',
    label: 'Extensions',
    items: [] // reserved space for future plug-in hooks
  }
];
