import React from 'react';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { cn } from '@/lib/utils';

export interface MapMarkerProps {
  top: string;
  left: string;
  variant?: 'primary' | 'secondary' | 'error';
  pingDuration?: string;
  sizeClass?: string;
  pingSizeClass?: string;
}

export function MapMarker({
  top,
  left,
  variant = 'primary',
  pingDuration,
  sizeClass = 'h-3 w-3',
  pingSizeClass = 'h-8 w-8'
}: MapMarkerProps) {
  const getBgClass = () => {
    switch(variant) {
      case 'error': return 'bg-error';
      case 'secondary': return 'bg-secondary-container';
      default: return 'bg-primary';
    }
  };

  const bgClass = getBgClass();

  return (
    <div className="absolute" style={{ top, left }}>
      <div className="relative flex items-center justify-center">
        {variant !== 'primary' && (
          <span 
            className={cn("animate-ping absolute inline-flex rounded-full opacity-40", pingSizeClass, bgClass)}
            style={pingDuration ? { animationDuration: pingDuration } : undefined}
          />
        )}
        <span className={cn("relative inline-flex rounded-full", sizeClass, bgClass)} />
      </div>
    </div>
  );
}

export interface MapModuleProps {
  children?: React.ReactNode;
}

export function MapModule({ children }: MapModuleProps) {
  return (
    <CardWrapper className="col-span-12 lg:col-span-8 p-0 overflow-hidden relative min-h-[400px]">
      <div className="absolute top-6 left-6 z-10 glass-panel px-4 py-3 rounded-lg border border-outline-variant/10 shadow-sm">
        <h3 className="text-title-md font-semibold text-on-surface">Live Crisis Zones</h3>
        <p className="text-label text-xs uppercase tracking-[0.05em] font-bold text-on-surface-variant mt-1 flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px] text-secondary">my_location</span>
          Tracking 12 regions
        </p>
      </div>

      <div className="w-full h-full bg-surface-container-low relative flex items-center justify-center">
        <img 
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuDnT7ck8YKCef0EggMnkLf4e1C7N6szCASnF_ujRGbxhias2wgtH9dvnCP1gjTNigr0_-5gKrU7d7Yn5gw0uCQUsYZPoxhKmYSYv9fUxkYVdttd8qozFVPBQsSx7dzFYyvZC92p_sOGFaOFSYglLLLkAcOBkHReVKJeX6bMUQTkzSp_JRU7PSg3GHoLlTyAtpz39TGd6aetBCHx6H6GllZ-toCH971_RI6n4L7dxMJy2Yun-gGfBYHUAmNwMmG6TAnkl6y7fjxRgej2"
          alt="Map visualization"
          className="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-luminosity"
        />
        <div className="absolute inset-0 bg-primary/5 mix-blend-multiply"></div>
        
        {children}
      </div>
    </CardWrapper>
  );
}
