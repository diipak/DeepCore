import React, { useEffect, useState, useRef } from 'react';
import { useWorkspace } from '../services/workspaceState';
import { useLocation } from 'react-router-dom';
import { 
  MessageSquare, 
  Sparkles, 
  Brain, 
  FileText, 
  Clock, 
  Link as LinkIcon, 
  AlertTriangle, 
  Send, 
  Compass,
  CheckCircle,
  Mic,
  Square,
  Volume2
} from 'lucide-react';
import { api } from '../services/api';
import type { ConversationState, ThinkingModeDescriptor } from '../services/api';
import { PresenceAvatar, type PresenceState } from './PresenceAvatar';
import { WorkspaceCanvas } from './WorkspaceCanvas';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export const AssistantPane: React.FC<{ className?: string }> = ({ className }) => {
  const { state } = useWorkspace();
  const location = useLocation();
  
  const [modes, setModes] = useState<ThinkingModeDescriptor[]>([]);
  const [session, setSession] = useState<ConversationState | null>(null);
  const [starting, setStarting] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);
  const [inputValue, setInputValue] = useState<string>('');
  
  // Phase 4 Presence & Historical Evidence Selection State
  const [presence, setPresence] = useState<PresenceState>('idle');
  const [recordingDuration, setRecordingDuration] = useState<number>(0);
  const [lastSpokenAudio, setLastSpokenAudio] = useState<string | null>(null);
  const [selectedMessageUuid, setSelectedMessageUuid] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<'chat' | 'canvas'>('chat');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const currentAudioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Derive active message for WorkspaceCanvas
  const selectedMessage = session?.messages?.find((m) => m.uuid === selectedMessageUuid) || null;
  const latestAssistantMessage = session?.messages
    ?.filter((m) => m.role === 'assistant')
    ?.slice(-1)[0] || null;
  const activeEvidenceCount = (selectedMessage || latestAssistantMessage)?.evidence?.length || 0;

  const startVoiceRecording = async () => {
    if (presence !== 'idle' && presence !== 'speaking') return;
    if (currentAudioPlayerRef.current) {
      currentAudioPlayerRef.current.pause();
    }

    // 1. Request microphone stream first with precise diagnostic error reporting
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err: any) {
      console.error("Microphone access error:", err);
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        alert(
          "Microphone permission denied.\n\n" +
          "1. Ensure Microphone is allowed for this site in your browser address bar.\n" +
          "2. On macOS, ensure your browser has permission in System Settings > Privacy & Security > Microphone."
        );
      } else if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
        alert("No microphone input device was detected on your system.");
      } else if (err?.name === 'NotReadableError' || err?.name === 'TrackStartError') {
        alert("Microphone is currently in use by another application or hardware device.");
      } else {
        alert(`Microphone access unavailable: ${err?.message || err?.name || 'unknown error'}`);
      }
      setPresence('idle');
      return;
    }

    // 2. Ensure active conversation session
    let activeSession = session;
    if (!activeSession) {
      setStarting(true);
      try {
        activeSession = await api.startThinkingSession("CONTINUE_THINKING", state.selectedObjectId || undefined);
        setSession(activeSession);
      } catch (err: any) {
        console.error("Session initialization error:", err);
        alert("Failed to initialize conversation session.\n\nPlease verify that DeepCore backend is running (services start / port 8000).");
        stream.getTracks().forEach((track) => track.stop());
        setPresence('idle');
        setStarting(false);
        return;
      } finally {
        setStarting(false);
      }
    }

    // 3. Initialize and start MediaRecorder
    try {
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (audioBlob.size < 500) {
          setPresence('idle');
          return;
        }
        await handleSendAudio(activeSession!.session_uuid, audioBlob);
      };

      recorder.start(100);
      setPresence('listening');
      setRecordingDuration(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("MediaRecorder start error:", err);
      stream.getTracks().forEach((track) => track.stop());
      alert("Failed to initialize audio recorder.");
      setPresence('idle');
    }
  };

  const stopVoiceRecording = () => {
    if (presence !== 'listening') return;
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setPresence('thinking');
  };

  const handleSendAudio = async (sessionUuid: string, audioBlob: Blob) => {
    setPresence('thinking');
    try {
      const { audioBlob: replyBlob } = await api.postConversationAudio(sessionUuid, audioBlob);

      // Refresh conversation state to fetch the grounded assistant reply & evidence
      const updated = await api.restoreConversation(sessionUuid);
      setSession(updated);

      // Play the returned audio reply
      if (replyBlob && replyBlob.size > 44) {
        const audioUrl = URL.createObjectURL(replyBlob);
        setLastSpokenAudio(audioUrl);
        playAudio(audioUrl);
      } else {
        setPresence('idle');
      }
    } catch (err) {
      console.error("Voice processing error:", err);
      alert("Voice processing failed. See console for details.");
      setPresence('idle');
    }
  };

  const playAudio = (url: string) => {
    if (currentAudioPlayerRef.current) {
      currentAudioPlayerRef.current.pause();
    }
    const audio = new Audio(url);
    currentAudioPlayerRef.current = audio;
    setPresence('speaking');
    audio.onended = () => setPresence('idle');
    audio.onerror = () => setPresence('idle');
    audio.play().catch((e) => {
      console.warn("Autoplay blocked or audio playback error:", e);
      setPresence('idle');
    });
  };

  // Fetch Available Thinking Modes
  useEffect(() => {
    const fetchModes = async () => {
      try {
        const res = await api.getThinkingModes();
        setModes(res);
      } catch (err) {
        console.error("Failed to load thinking modes:", err);
      }
    };
    fetchModes();
  }, []);

  // Parse prompt from query parameters (e.g. from Thinking Guides on Home screen)
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const promptParam = params.get('prompt');
    
    if (promptParam && modes.length > 0 && !session && !starting) {
      const autoStart = async () => {
        setStarting(true);
        try {
          const res = await api.startThinkingSession("CONTINUE_THINKING", state.selectedObjectId || undefined);
          const updated = await api.continueConversation(res.session_uuid, promptParam);
          setSession(updated);
        } catch (err) {
          console.error("Failed to autostart prompt session:", err);
        } finally {
          setStarting(false);
        }
      };
      autoStart();
    }
  }, [location.search, modes, session, starting, state.selectedObjectId]);

  const handleStartSession = async (modeId: string) => {
    setStarting(true);
    try {
      const res = await api.startThinkingSession(modeId, state.selectedObjectId || undefined);
      setSession(res);
    } catch (err) {
      console.error("Failed to start thinking session:", err);
      alert("Failed to initialize thinking session.");
    } finally {
      setStarting(false);
    }
  };

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session?.messages, sending]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || sending || starting) return;

    const userText = inputValue;
    setInputValue('');
    setSending(true);
    setPresence('thinking');
    try {
      let activeSession = session;
      if (!activeSession) {
        setStarting(true);
        activeSession = await api.startThinkingSession("CONTINUE_THINKING", state.selectedObjectId || undefined);
        setSession(activeSession);
        setStarting(false);
      }
      const res = await api.continueConversation(activeSession.session_uuid, userText);
      setSession(res);

      // Transition to speaking briefly when response lands, then back to idle
      setPresence('speaking');
      setTimeout(() => {
        setPresence('idle');
      }, 1500);
    } catch (err) {
      console.error("Failed to send message:", err);
      alert("Failed to process reply.");
      setPresence('idle');
    } finally {
      setSending(false);
      setStarting(false);
    }
  };

  const renderModeIcon = (iconName: string) => {
    switch (iconName) {
      case 'Brain': return <Brain className="w-4 h-4 text-accent-concept" />;
      case 'Clock': return <Clock className="w-4 h-4 text-accent-video" />;
      case 'Link': return <LinkIcon className="w-4 h-4 text-accent-concept" />;
      case 'AlertTriangle': return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      default: return <FileText className="w-4 h-4 text-accent-memory" />;
    }
  };

  // Render full Markdown with table/list/code support and deepcore:// citation link translation
  const renderAssistantContent = (text: string) => {
    return (
      <div className="prose dark:prose-invert max-w-none text-text-primary select-text text-[11px] leading-relaxed break-words">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ href, children }) => {
              if (href && href.startsWith('deepcore://')) {
                return (
                  <span 
                    className="px-1.5 py-0.5 rounded bg-accent-assistant/10 border border-accent-assistant/20 text-[10px] font-bold text-accent-assistant select-all inline-block mx-0.5 cursor-default"
                    title={`Provenanced resource: ${href}`}
                  >
                    {children}
                  </span>
                );
              }
              return (
                <a 
                  href={href} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-accent-assistant underline hover:text-accent-assistant/80"
                >
                  {children}
                </a>
              );
            },
            p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
            ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
            li: ({ children }) => <li className="leading-relaxed">{children}</li>,
            code: ({ className, children }) => {
              const isInline = !className || !className.includes('language-');
              if (isInline) {
                return (
                  <code className="px-1.5 py-0.5 rounded bg-background-primary/80 border border-border-primary/60 font-mono text-[10px] text-text-primary">
                    {children}
                  </code>
                );
              }
              return (
                <div className="my-2 border border-border-primary/80 rounded-xl overflow-hidden shadow-inner">
                  <pre className="p-3 font-mono text-[10.5px] bg-background-primary/90 overflow-x-auto text-text-primary leading-normal">
                    <code>{children}</code>
                  </pre>
                </div>
              );
            },
            table: ({ children }) => (
              <div className="overflow-x-auto w-full border border-border-primary/60 rounded-xl my-2 bg-surface-card/40">
                <table className="w-full border-collapse text-[10.5px] text-left">
                  {children}
                </table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="bg-background-primary/60 border-b border-border-primary/60 font-bold text-[10px] text-text-secondary uppercase">
                {children}
              </thead>
            ),
            th: ({ children }) => <th className="px-3 py-1.5 font-bold text-text-primary">{children}</th>,
            td: ({ children }) => <td className="px-3 py-2 text-text-secondary border-t border-border-primary/40">{children}</td>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-accent-assistant/50 pl-3 my-2 text-text-secondary italic">
                {children}
              </blockquote>
            ),
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <aside className={`h-full bg-surface-card/65 backdrop-blur-md border-l border-border-primary flex flex-col select-none overflow-hidden ${className || ''}`}>
      {/* Pane Header */}
      <div className="p-3 md:p-3.5 border-b border-border-primary flex items-center justify-between shrink-0 bg-surface-card/40 gap-2">
        <div className="flex items-center space-x-2 shrink-0">
          <MessageSquare className="w-4 h-4 text-accent-assistant" />
          <h3 className="font-extrabold text-xs sm:text-sm tracking-tight text-text-primary">
            AI Assistant
          </h3>
        </div>

        {/* Mobile Segmented Toggle (Chat vs Canvas) */}
        <div className="flex md:hidden items-center bg-background-primary/70 p-0.5 rounded-xl border border-border-primary text-xs font-semibold shrink-0">
          <button
            type="button"
            onClick={() => setMobileTab('chat')}
            className={`px-3 py-1 rounded-lg transition-all cursor-pointer flex items-center space-x-1.5 ${
              mobileTab === 'chat'
                ? 'bg-accent-assistant text-white shadow-xs'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Chat</span>
          </button>
          <button
            type="button"
            onClick={() => setMobileTab('canvas')}
            className={`px-3 py-1 rounded-lg transition-all cursor-pointer flex items-center space-x-1.5 ${
              mobileTab === 'canvas'
                ? 'bg-accent-assistant text-white shadow-xs'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Canvas</span>
            {activeEvidenceCount > 0 && (
              <span className={`text-[9px] px-1.5 py-0.2 rounded-full font-bold ${
                mobileTab === 'canvas' ? 'bg-white/25 text-white' : 'bg-accent-assistant/20 text-accent-assistant'
              }`}>
                {activeEvidenceCount}
              </span>
            )}
          </button>
        </div>

        {/* Desktop Session Mode Indicator */}
        <div className="hidden md:flex items-center">
          {session ? (
            <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/10">
              <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
              <span className="capitalize">{session.active_thinking_mode.toLowerCase().replace('_', ' ')}</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-accent-assistant/10 text-accent-assistant border border-accent-assistant/10">
              <span className="w-1 h-1 rounded-full bg-accent-assistant animate-pulse" />
              <span>Select Mode</span>
            </span>
          )}
        </div>
      </div>

      {/* Dual-Pane Layout: Left = Avatar + Chat Thread; Right = Tabbed Workspace Canvas */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative">
        {/* LEFT COLUMN: Presence Avatar + Chat Thread + Input Footer */}
        <div className={`flex-1 flex-col min-w-0 w-full ${mobileTab === 'chat' ? 'flex' : 'hidden'} md:flex`}>
          {/* Presence Avatar Header */}
          <div className="p-3 border-b border-border-primary/60 bg-surface-card/30 flex items-center justify-between shrink-0">
            <PresenceAvatar
              presence={presence}
              recordingDuration={recordingDuration}
              onAvatarClick={presence === 'listening' ? stopVoiceRecording : startVoiceRecording}
              showDevSwitcher={true}
            />
            {lastSpokenAudio && (
              <button
                type="button"
                onClick={() => playAudio(lastSpokenAudio)}
                className="flex items-center space-x-1 text-[10px] font-semibold text-accent-assistant hover:text-accent-assistant/80 cursor-pointer shrink-0 ml-2"
                title="Replay last spoken audio response"
              >
                <Volume2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Replay</span>
              </button>
            )}
          </div>

          {/* Messages Thread (Always Visible) */}
          <div className="flex-1 overflow-y-auto p-3 min-h-0 space-y-3">
            {starting && (
              <div className="flex flex-col items-center justify-center py-20 space-y-4 animate-pulse">
                <Sparkles className="w-8 h-8 text-accent-assistant animate-spin" />
                <span className="text-xs text-text-secondary font-semibold">Initializing Thinking Session...</span>
              </div>
            )}

            {/* 1. STATE: SELECT THINKING MODE (No Session Active) */}
            {!session && !starting && (
              <div className="space-y-4 animate-fade-in py-1">
                <div className="p-3 rounded-xl bg-accent-assistant/5 border border-accent-assistant/15 text-accent-assistant flex items-start space-x-2.5">
                  <Compass className="w-4 h-4 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <h5 className="text-[10px] font-bold uppercase tracking-wider leading-none">Thinking Sessions</h5>
                    <p className="text-[10px] text-text-secondary leading-relaxed">
                      Start a guided session. The assistant consumes system awareness and workspace context packages.
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
                    Select Thinking Mode
                  </h4>
                  <div className="space-y-1.5">
                    {modes.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => handleStartSession(m.id)}
                        className="w-full p-2.5 rounded-xl border border-border-primary hover:border-accent-assistant/30 bg-surface-card hover:bg-background-primary/30 text-left transition-all duration-150 flex items-start space-x-2.5 cursor-pointer group"
                      >
                        <div className="p-1.5 rounded-lg bg-background-primary group-hover:bg-surface-card border border-border-primary/60 shrink-0">
                          {renderModeIcon(m.icon)}
                        </div>
                        <div className="space-y-0.5 min-w-0">
                          <h5 className="text-[11px] font-bold text-text-primary group-hover:text-accent-assistant transition-colors">
                            {m.name}
                          </h5>
                          <p className="text-[9.5px] text-text-secondary leading-normal line-clamp-2">
                            {m.description}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 2. STATE: ACTIVE CONVERSATION SESSION */}
            {session && !starting && (
              <div className="space-y-3 animate-fade-in pb-2">
                {/* Active Session Context Bar */}
                <div className="p-2.5 rounded-xl border border-border-primary/80 bg-background-primary/20 text-[10px] text-text-secondary space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-text-primary/70 uppercase tracking-wider text-[9px]">Session Context</span>
                    <span className="font-mono text-[8.5px] text-text-secondary/70">Context Package active</span>
                  </div>
                  <div className="flex justify-between items-center text-text-primary font-medium text-[9.5px]">
                    <span>Focus items: <span className="font-bold">{session.context_package.focus_count}</span></span>
                    <span>Observations: <span className="font-bold">{session.context_package.observations_count}</span></span>
                  </div>
                </div>

                {/* Messages Thread */}
                <div className="space-y-3">
                  {session.messages.map((msg) => {
                    const isAssistant = msg.role === 'assistant';
                    const isExplicitlySelected = selectedMessageUuid === msg.uuid;
                    const isDefaultActive = !selectedMessageUuid && latestAssistantMessage?.uuid === msg.uuid;
                    const isInspected = isAssistant && (isExplicitlySelected || isDefaultActive);

                    const containerClass = isAssistant ? 'justify-start' : 'justify-end';
                    const bubbleClass = isAssistant 
                      ? `bg-background-primary/40 border-border-primary text-text-primary rounded-br-2xl rounded-tr-2xl rounded-bl-xs transition-all ${
                          isInspected ? 'ring-2 ring-accent-assistant/50 border-accent-assistant/30' : 'hover:border-accent-assistant/30'
                        } cursor-pointer` 
                      : 'bg-accent-assistant text-white border-transparent rounded-bl-2xl rounded-tl-2xl rounded-br-xs';

                    return (
                      <div key={msg.uuid} className={`flex ${containerClass} animate-fade-in`}>
                        <div 
                          className={`max-w-[90%] space-y-1 ${isAssistant ? 'cursor-pointer' : ''}`}
                          onClick={() => {
                            if (isAssistant) {
                              setSelectedMessageUuid(msg.uuid);
                            }
                          }}
                        >
                          {/* Message Bubble */}
                          <div className={`p-3 rounded-2xl border text-[11px] leading-relaxed select-text font-medium ${bubbleClass}`}>
                            {isAssistant ? renderAssistantContent(msg.content) : msg.content}

                            {/* Evidence Citation Indicator Footer */}
                            {isAssistant && msg.evidence && msg.evidence.length > 0 && (
                              <div className="mt-2 pt-1.5 border-t border-border-primary/40 flex items-center justify-between text-[9.5px]">
                                <span className="flex items-center space-x-1 text-emerald-400 font-semibold">
                                  <CheckCircle className="w-3 h-3" />
                                  <span>{msg.evidence.length} citation{msg.evidence.length > 1 ? 's' : ''}</span>
                                </span>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedMessageUuid(msg.uuid);
                                    setMobileTab('canvas');
                                  }}
                                  className={`text-[9px] font-bold transition-colors cursor-pointer py-0.5 px-1.5 rounded-md hover:bg-accent-assistant/10 ${
                                    isInspected ? 'text-accent-assistant' : 'text-text-secondary/80 hover:text-accent-assistant'
                                  }`}
                                >
                                  {isInspected ? 'Canvas Active ➔' : 'Inspect in Canvas ➔'}
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {/* Lightweight typing indicator bubble when sending is true */}
                  {sending && (
                    <div className="flex justify-start animate-fade-in">
                      <div className="p-3 rounded-2xl rounded-bl-xs bg-background-primary/40 border border-border-primary text-text-secondary flex items-center space-x-1.5 shadow-xs">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-assistant animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-assistant animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-assistant animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              </div>
            )}
          </div>

          {/* Left Pane Footer: Voice-First Conversational Action Bar + Secondary Text Input */}
          <div className="p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] border-t border-border-primary shrink-0 bg-surface-card/40 space-y-2.5">
            {/* 1. PRIMARY CONVERSATIONAL VOICE CAPSULE */}
            {presence === 'idle' && (
              <button
                type="button"
                onClick={startVoiceRecording}
                disabled={starting}
                className="w-full min-h-[48px] py-2.5 px-3.5 rounded-2xl bg-surface-card/60 hover:bg-surface-card/90 dark:bg-slate-900/60 dark:hover:bg-slate-900/80 border border-white/15 hover:border-accent-assistant/40 backdrop-blur-xl flex items-center justify-between transition-all group shadow-sm cursor-pointer"
                title="Click to start hands-free voice conversation"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-accent-assistant/10 group-hover:bg-accent-assistant/20 border border-accent-assistant/20 flex items-center justify-center text-accent-assistant transition-colors shrink-0">
                    <Mic className="w-4 h-4" />
                  </div>
                  <div className="text-left truncate">
                    <div className="text-xs font-bold text-text-primary group-hover:text-accent-assistant transition-colors">
                      Tap to Speak
                    </div>
                    <div className="text-[9.5px] text-text-secondary truncate">
                      Conversational voice mode with live spoken reply
                    </div>
                  </div>
                </div>
                <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-background-primary/60 border border-border-primary text-text-secondary shrink-0 ml-2">
                  Voice Primary
                </span>
              </button>
            )}

            {presence === 'listening' && (
              <button
                type="button"
                onClick={stopVoiceRecording}
                className="w-full min-h-[48px] py-2.5 px-3.5 rounded-2xl bg-rose-500/15 border border-rose-500/40 backdrop-blur-xl flex items-center justify-between transition-all shadow-md shadow-rose-500/10 cursor-pointer animate-pulse"
                title="Click to stop recording and synthesize reply"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-rose-500 text-white flex items-center justify-center shadow-xs shrink-0">
                    <Square className="w-3.5 h-3.5" />
                  </div>
                  <div className="text-left truncate">
                    <div className="text-xs font-bold text-rose-400">
                      Listening ({recordingDuration}s)...
                    </div>
                    <div className="text-[9.5px] text-text-secondary truncate">
                      Tap to finish speaking & synthesize reply
                    </div>
                  </div>
                </div>
                {/* Real-time sound wave bars */}
                <div className="flex items-center space-x-1 shrink-0 ml-2">
                  <span className="w-1 h-3 bg-rose-400 rounded-full animate-pulse" />
                  <span className="w-1 h-5 bg-rose-400 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                  <span className="w-1 h-4 bg-rose-400 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                  <span className="w-1 h-2 bg-rose-400 rounded-full animate-pulse" style={{ animationDelay: '450ms' }} />
                </div>
              </button>
            )}

            {presence === 'thinking' && (
              <div className="w-full min-h-[48px] py-2.5 px-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 backdrop-blur-xl flex items-center justify-between shadow-xs">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center shrink-0">
                    <Sparkles className="w-4 h-4 animate-spin" />
                  </div>
                  <div className="text-left truncate">
                    <div className="text-xs font-bold text-amber-400">
                      Thinking & Grounding...
                    </div>
                    <div className="text-[9.5px] text-text-secondary truncate">
                      Transcribing speech, retrieving context & synthesizing
                    </div>
                  </div>
                </div>
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping shrink-0 ml-2" />
              </div>
            )}

            {presence === 'speaking' && (
              <div className="w-full min-h-[48px] py-2.5 px-3.5 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 backdrop-blur-xl flex items-center justify-between shadow-xs">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center shrink-0">
                    <Volume2 className="w-4 h-4 animate-pulse" />
                  </div>
                  <div className="text-left truncate">
                    <div className="text-xs font-bold text-cyan-400">
                      Speaking Response...
                    </div>
                    <div className="text-[9.5px] text-text-secondary truncate">
                      Audio output stream active
                    </div>
                  </div>
                </div>
                {lastSpokenAudio && (
                  <button
                    type="button"
                    onClick={() => playAudio(lastSpokenAudio)}
                    className="text-[10px] font-bold text-cyan-400 hover:text-cyan-300 underline cursor-pointer shrink-0 ml-2"
                  >
                    Replay
                  </button>
                )}
              </div>
            )}

            {/* 2. SECONDARY TEXT INPUT (Progressive Disclosure) */}
            <form onSubmit={handleSendMessage} className="flex items-center space-x-2 pt-0.5">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={sending || starting || presence === 'listening' || presence === 'thinking'}
                placeholder={presence === 'listening' ? 'Listening to voice...' : 'Or type a message to DeepCore...'}
                className="flex-1 min-h-[44px] px-3.5 py-2 rounded-xl border border-border-primary/80 bg-background-primary/30 text-xs font-medium text-text-primary placeholder-text-secondary/70 focus:outline-none focus:border-accent-assistant/60 transition-all"
              />
              <button
                type="submit"
                disabled={sending || starting || !inputValue.trim() || presence === 'listening'}
                className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl bg-accent-assistant hover:bg-accent-assistant/95 text-white flex items-center justify-center transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shrink-0 shadow-xs"
                title="Send text message"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* RIGHT COLUMN: Tabbed Workspace Canvas (Persistent on desktop, toggleable on mobile) */}
        <div className={`h-full flex-col w-full md:w-[42%] md:min-w-[280px] md:max-w-[560px] shrink-0 ${mobileTab === 'canvas' ? 'flex' : 'hidden'} md:flex`}>
          <WorkspaceCanvas
            session={session}
            selectedMessage={selectedMessage}
            onResetToLatest={() => setSelectedMessageUuid(null)}
            onBackToChat={() => setMobileTab('chat')}
          />
        </div>
      </div>
    </aside>
  );
};
