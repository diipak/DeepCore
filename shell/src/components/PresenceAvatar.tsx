import React, { useState } from 'react';

export type PresenceState = 'idle' | 'listening' | 'thinking' | 'speaking';
export type AvatarSize = 'sm' | 'md' | 'lg';

interface PresenceAvatarProps {
  presence: PresenceState;
  recordingDuration?: number;
  onAvatarClick?: () => void;
  onStateSelect?: (state: PresenceState) => void;
  size?: AvatarSize;
  showDevSwitcher?: boolean;
  className?: string;
}

export const PresenceAvatar: React.FC<PresenceAvatarProps> = ({
  presence: controlledPresence,
  recordingDuration = 0,
  onAvatarClick,
  onStateSelect,
  size = 'md',
  showDevSwitcher = false,
  className = '',
}) => {
  // Local state override for interactive dev testing if switcher is clicked
  const [internalOverride, setInternalOverride] = useState<PresenceState | null>(null);
  const activePresence = internalOverride ?? controlledPresence;

  const handleStateClick = (state: PresenceState) => {
    setInternalOverride(state);
    onStateSelect?.(state);
  };

  // Sizing definitions
  const sizeConfig = {
    sm: {
      chassis: 'w-10 h-10',
      svg: 'w-7 h-7',
      pupilRadius: 3.5,
      mouthStroke: 2.2,
      haloInset: '-inset-1',
      fontSizeTitle: 'text-[11px]',
      fontSizeBadge: 'text-[8px]',
      fontSizeDesc: 'text-[9px]',
    },
    md: {
      chassis: 'w-16 h-16 sm:w-18 sm:h-18',
      svg: 'w-12 h-12 sm:w-13 sm:h-13',
      pupilRadius: 4.2,
      mouthStroke: 2.6,
      haloInset: '-inset-1.5',
      fontSizeTitle: 'text-xs sm:text-sm',
      fontSizeBadge: 'text-[9px]',
      fontSizeDesc: 'text-[10px]',
    },
    lg: {
      chassis: 'w-24 h-24 sm:w-28 sm:h-28',
      svg: 'w-18 h-18 sm:w-20 sm:h-20',
      pupilRadius: 5.0,
      mouthStroke: 3.2,
      haloInset: '-inset-2',
      fontSizeTitle: 'text-base',
      fontSizeBadge: 'text-[10px]',
      fontSizeDesc: 'text-xs',
    },
  }[size];

  // Theme configuration adhering to Apple Liquid Glass specs
  const getThemeConfig = () => {
    switch (activePresence) {
      case 'listening':
        return {
          glassBg: 'bg-rose-500/10 dark:bg-rose-950/30',
          chassisBorder: 'border-rose-400/40 dark:border-rose-500/30 shadow-lg shadow-rose-500/10',
          specularGlow: 'from-rose-400/20 via-transparent to-transparent',
          haloRing: 'border-rose-400/30 animate-ping',
          irisColor: '#fb7185',
          pupilColor: '#fda4af',
          mouthColor: '#fb7185',
          label: `LISTENING (${recordingDuration}s)`,
          badgeClass: 'bg-rose-500/15 text-rose-400 border-rose-500/25',
          glowShadow: '0 0 24px rgba(244, 63, 94, 0.25)',
        };
      case 'thinking':
        return {
          glassBg: 'bg-amber-500/10 dark:bg-amber-950/30',
          chassisBorder: 'border-amber-400/40 dark:border-amber-500/30 shadow-lg shadow-amber-500/10',
          specularGlow: 'from-amber-400/20 via-transparent to-transparent',
          haloRing: 'border-amber-400/40 animate-spin',
          irisColor: '#fbbf24',
          pupilColor: '#fef08a',
          mouthColor: '#f59e0b',
          label: 'THINKING (REASONING)',
          badgeClass: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
          glowShadow: '0 0 24px rgba(245, 158, 11, 0.25)',
        };
      case 'speaking':
        return {
          glassBg: 'bg-cyan-500/10 dark:bg-indigo-950/30',
          chassisBorder: 'border-cyan-400/50 dark:border-cyan-500/40 shadow-lg shadow-cyan-500/15',
          specularGlow: 'from-cyan-400/25 via-transparent to-transparent',
          haloRing: 'border-cyan-400/40 animate-pulse',
          irisColor: '#22d3ee',
          pupilColor: '#a5f3fc',
          mouthColor: '#06b6d4',
          label: 'SPEAKING',
          badgeClass: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/25',
          glowShadow: '0 0 28px rgba(6, 182, 212, 0.3)',
        };
      case 'idle':
      default:
        return {
          glassBg: 'bg-white/40 dark:bg-slate-900/60',
          chassisBorder: 'border-white/20 dark:border-white/10 hover:border-accent-assistant/40 shadow-md shadow-black/10',
          specularGlow: 'from-white/20 via-white/5 to-transparent dark:from-white/10 dark:via-transparent to-transparent',
          haloRing: 'border-white/20 dark:border-white/10',
          irisColor: '#94a3b8',
          pupilColor: '#cbd5e1',
          mouthColor: '#94a3b8',
          label: 'IDLE',
          badgeClass: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
          glowShadow: 'none',
        };
    }
  };

  const theme = getThemeConfig();

  return (
    <div className={`flex flex-col space-y-2 select-none ${className}`}>
      {/* Embedded Hardware-Accelerated Animation Stylesheet */}
      <style>{`
        @keyframes dc-blink {
          0%, 88%, 100% {
            transform: scaleY(1);
          }
          93% {
            transform: scaleY(0.08);
          }
        }

        @keyframes dc-saccade {
          0%, 100% {
            transform: translate3d(0, 0, 0);
          }
          15% {
            transform: translate3d(-4px, -1.5px, 0);
          }
          35% {
            transform: translate3d(-3.5px, -1px, 0);
          }
          55% {
            transform: translate3d(4.5px, -1px, 0);
          }
          75% {
            transform: translate3d(3px, 0px, 0);
          }
          90% {
            transform: translate3d(-1px, 0.5px, 0);
          }
        }

        @keyframes dc-speak-mouth {
          0%, 100% {
            transform: scaleY(1) scaleX(1);
          }
          20% {
            transform: scaleY(2.1) scaleX(0.92);
          }
          40% {
            transform: scaleY(0.9) scaleX(1.04);
          }
          65% {
            transform: scaleY(1.9) scaleX(0.95);
          }
          85% {
            transform: scaleY(1.2) scaleX(1.02);
          }
        }

        @keyframes dc-ripple-wave {
          0% {
            stroke-dashoffset: 0;
          }
          100% {
            stroke-dashoffset: -32;
          }
        }

        @keyframes dc-ambient-breathe {
          0%, 100% {
            transform: scale(1);
            opacity: 0.9;
          }
          50% {
            transform: scale(1.015);
            opacity: 1;
          }
        }

        .dc-animate-blink {
          transform-origin: center;
          animation: dc-blink 4.2s infinite cubic-bezier(0.4, 0, 0.2, 1);
          will-change: transform;
        }

        .dc-animate-saccade {
          animation: dc-saccade 3.4s infinite ease-in-out;
          will-change: transform;
        }

        .dc-animate-speak {
          transform-origin: 50px 65px;
          animation: dc-speak-mouth 0.45s infinite ease-in-out;
          will-change: transform;
        }

        .dc-animate-breathe {
          animation: dc-ambient-breathe 4s infinite ease-in-out;
        }
      `}</style>

      {/* Main Avatar & Metadata Row */}
      <div className="flex items-center space-x-3.5">
        {/* Liquid Glass Chassis */}
        <button
          type="button"
          onClick={onAvatarClick}
          title={
            activePresence === 'listening'
              ? 'Click to STOP recording'
              : activePresence === 'thinking'
              ? 'DeepCore is thinking...'
              : 'Click to SPEAK (Voice Trigger)'
          }
          className={`relative ${sizeConfig.chassis} rounded-full backdrop-blur-xl border flex items-center justify-center transition-all duration-300 cursor-pointer group shrink-0 ${theme.glassBg} ${theme.chassisBorder}`}
          style={{ boxShadow: theme.glowShadow }}
        >
          {/* Specular Rim Ambient Light (Apple Liquid Glass simulated gradient) */}
          <div
            className={`absolute inset-0 rounded-full bg-gradient-to-b ${theme.specularGlow} pointer-events-none`}
          />

          {/* Halo Ring for Active States */}
          {activePresence !== 'idle' && (
            <div
              className={`absolute ${sizeConfig.haloInset} rounded-full border pointer-events-none ${theme.haloRing}`}
            />
          )}

          {/* Liquid Glass Parametric SVG Face */}
          <svg
            viewBox="0 0 100 100"
            className={`${sizeConfig.svg} transition-colors duration-300 dc-animate-breathe`}
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Defs for soft glows and gradient curves */}
            <defs>
              <linearGradient id="dc-mouth-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor={theme.mouthColor} stopOpacity="0.8" />
                <stop offset="50%" stopColor={theme.pupilColor} stopOpacity="1" />
                <stop offset="100%" stopColor={theme.mouthColor} stopOpacity="0.8" />
              </linearGradient>
            </defs>

            {/* 1. STATE: IDLE */}
            {activePresence === 'idle' && (
              <>
                {/* Gentle Eyes with Natural Blinking */}
                <g className="dc-animate-blink">
                  {/* Left Eye */}
                  <circle cx="34" cy="42" r="5" fill={theme.irisColor} opacity="0.4" />
                  <circle cx="34" cy="42" r={sizeConfig.pupilRadius} fill={theme.pupilColor} />
                  <circle cx="36" cy="40" r="1.5" fill="#ffffff" opacity="0.85" />

                  {/* Right Eye */}
                  <circle cx="66" cy="42" r="5" fill={theme.irisColor} opacity="0.4" />
                  <circle cx="66" cy="42" r={sizeConfig.pupilRadius} fill={theme.pupilColor} />
                  <circle cx="68" cy="40" r="1.5" fill="#ffffff" opacity="0.85" />
                </g>

                {/* Calm Resting Arc */}
                <path
                  d="M 37 64 Q 50 71 63 64"
                  stroke={theme.mouthColor}
                  strokeWidth={sizeConfig.mouthStroke}
                  strokeLinecap="round"
                  opacity="0.85"
                />
              </>
            )}

            {/* 2. STATE: LISTENING */}
            {activePresence === 'listening' && (
              <>
                {/* Alert, Forward-Focused Dilated Eyes */}
                <g>
                  {/* Left Eye */}
                  <circle cx="33" cy="41" r="6" fill={theme.irisColor} opacity="0.3" />
                  <circle cx="33" cy="41" r="5" fill={theme.pupilColor} />
                  <circle cx="35.5" cy="38.5" r="2" fill="#ffffff" opacity="0.9" />

                  {/* Right Eye */}
                  <circle cx="67" cy="41" r="6" fill={theme.irisColor} opacity="0.3" />
                  <circle cx="67" cy="41" r="5" fill={theme.pupilColor} />
                  <circle cx="69.5" cy="38.5" r="2" fill="#ffffff" opacity="0.9" />
                </g>

                {/* Receptive Acoustic Listening Aperture */}
                <ellipse
                  cx="50"
                  cy="65"
                  rx="6.5"
                  ry="5"
                  fill="url(#dc-mouth-grad)"
                  opacity="0.9"
                />
              </>
            )}

            {/* 3. STATE: THINKING (Saccadic cognitive eye drift) */}
            {activePresence === 'thinking' && (
              <>
                {/* Eyes Glancing and Drifting Left-to-Right */}
                <g className="dc-animate-saccade">
                  {/* Left Eye (Thinking gaze) */}
                  <circle cx="35" cy="39" r="5.5" fill={theme.irisColor} opacity="0.3" />
                  <circle cx="35" cy="39" r={sizeConfig.pupilRadius} fill={theme.pupilColor} />
                  <circle cx="37" cy="37" r="1.6" fill="#ffffff" opacity="0.9" />

                  {/* Right Eye (Thinking gaze) */}
                  <circle cx="67" cy="39" r="5.5" fill={theme.irisColor} opacity="0.3" />
                  <circle cx="67" cy="39" r={sizeConfig.pupilRadius} fill={theme.pupilColor} />
                  <circle cx="69" cy="37" r="1.6" fill="#ffffff" opacity="0.9" />
                </g>

                {/* Cognitive Undulating Thought Ripple */}
                <path
                  d="M 36 65 Q 43 61 50 65 Q 57 69 64 65"
                  stroke={theme.mouthColor}
                  strokeWidth={sizeConfig.mouthStroke}
                  strokeLinecap="round"
                  opacity="0.9"
                />
              </>
            )}

            {/* 4. STATE: SPEAKING (Fluid vocal cadence wave) */}
            {activePresence === 'speaking' && (
              <>
                {/* Lively Expressive Eyes */}
                <g>
                  {/* Left Eye */}
                  <circle cx="34" cy="41" r="5.5" fill={theme.irisColor} opacity="0.35" />
                  <circle cx="34" cy="41" r={sizeConfig.pupilRadius} fill={theme.pupilColor} />
                  <circle cx="36" cy="39" r="1.8" fill="#ffffff" opacity="0.95" />

                  {/* Right Eye */}
                  <circle cx="66" cy="41" r="5.5" fill={theme.irisColor} opacity="0.35" />
                  <circle cx="66" cy="41" r={sizeConfig.pupilRadius} fill={theme.pupilColor} />
                  <circle cx="68" cy="39" r="1.8" fill="#ffffff" opacity="0.95" />
                </g>

                {/* Harmonic Speaking Viseme Cadence Wave */}
                <g className="dc-animate-speak">
                  <path
                    d="M 35 65 Q 42 74 50 65 Q 58 56 65 65 Q 50 71 35 65 Z"
                    fill="url(#dc-mouth-grad)"
                    opacity="0.9"
                  />
                </g>
              </>
            )}
          </svg>

          {/* Hover interactive overlay */}
          <div className="absolute inset-0 rounded-full bg-white/0 group-hover:bg-white/5 transition-colors" />
        </button>

        {/* State Badge & Metadata */}
        <div className="space-y-1 min-w-0">
          <div className="flex items-center space-x-2">
            <span className={`${sizeConfig.fontSizeTitle} font-extrabold text-text-primary tracking-tight`}>
              DeepCore
            </span>
            <span
              className={`px-2 py-0.5 rounded-full ${sizeConfig.fontSizeBadge} font-extrabold uppercase tracking-wider border ${theme.badgeClass}`}
            >
              {theme.label}
            </span>
          </div>
          <p className={`${sizeConfig.fontSizeDesc} text-text-secondary truncate`}>
            {activePresence === 'listening'
              ? 'Listening to microphone... click to stop'
              : activePresence === 'thinking'
              ? 'Grounding context and synthesizing...'
              : activePresence === 'speaking'
              ? 'Speaking reply aloud...'
              : 'Click face or mic to speak'}
          </p>
        </div>
      </div>

      {/* Optional Interactive Dev State-Switcher Bar */}
      {showDevSwitcher && (
        <div className="hidden sm:flex items-center space-x-1 pt-1">
          <span className="text-[9px] font-bold text-text-secondary/70 uppercase tracking-widest mr-1">
            State:
          </span>
          {(['idle', 'listening', 'thinking', 'speaking'] as PresenceState[]).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => handleStateClick(st)}
              className={`px-2 py-0.5 rounded-md text-[9px] font-bold transition-all cursor-pointer ${
                activePresence === st
                  ? 'bg-accent-assistant text-white shadow-xs'
                  : 'bg-surface-card hover:bg-background-primary text-text-secondary border border-border-primary/60'
              }`}
            >
              {st}
            </button>
          ))}
          {internalOverride && (
            <button
              type="button"
              onClick={() => setInternalOverride(null)}
              className="text-[8.5px] text-text-secondary/60 hover:text-rose-400 ml-1 underline cursor-pointer"
            >
              Reset
            </button>
          )}
        </div>
      )}
    </div>
  );
};
