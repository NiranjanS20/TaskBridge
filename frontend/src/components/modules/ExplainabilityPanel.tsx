import React from 'react';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { cn } from '@/lib/utils';

export interface ExplainabilityPanelRootProps {
  children: React.ReactNode;
  className?: string;
}

function Root({ children, className }: ExplainabilityPanelRootProps) {
  return (
    <CardWrapper className={cn("flex flex-col", className)}>
      {children}
    </CardWrapper>
  );
}

export interface ExplainabilityHeaderProps {
  title?: string;
  subtitle?: string;
}

function Header({ title = "Allocation Rationale", subtitle = "Why this resource was selected" }: ExplainabilityHeaderProps) {
  return (
    <div className="flex justify-between items-start border-b border-surface-container-highest pb-4 mb-4">
      <div>
        <h3 className="text-title-md font-semibold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">psychology</span>
          {title}
        </h3>
        <p className="text-sm text-on-surface-variant mt-1">{subtitle}</p>
      </div>
      <span className="bg-primary-container text-primary px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider">
        AI Match
      </span>
    </div>
  );
}

export interface ExplainabilityFactorProps {
  label: string;
  value: string;
  impact: 'high' | 'medium' | 'low';
  icon: string;
}

function Factor({ label, value, impact, icon }: ExplainabilityFactorProps) {
  const getImpactColor = () => {
    switch (impact) {
      case 'high': return 'text-primary bg-primary-fixed border-primary/20';
      case 'medium': return 'text-secondary bg-secondary-container border-secondary/20';
      case 'low': return 'text-on-surface-variant bg-surface-container-high border-outline/20';
      default: return 'text-on-surface-variant bg-surface-container border-outline/20';
    }
  };

  const getImpactBarWidth = () => {
    switch(impact) {
      case 'high': return '90%';
      case 'medium': return '60%';
      case 'low': return '30%';
      default: return '0%';
    }
  }

  const getImpactBarColor = () => {
     switch (impact) {
      case 'high': return 'bg-primary';
      case 'medium': return 'bg-secondary';
      case 'low': return 'bg-outline-variant';
      default: return 'bg-outline';
    }
  }

  return (
    <div className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/30 flex items-center gap-3">
      <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0 border", getImpactColor())}>
        <span className="material-symbols-outlined text-[16px]">{icon}</span>
      </div>
      <div className="flex-1">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-bold text-on-surface">{label}</span>
          <span className="text-xs font-bold text-on-surface-variant">{value}</span>
        </div>
        <div className="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
          <div className={cn("h-1.5 rounded-full transition-all", getImpactBarColor())} style={{ width: getImpactBarWidth() }}></div>
        </div>
      </div>
    </div>
  );
}

export interface ExplainabilitySummaryProps {
  children: React.ReactNode;
}

function Summary({ children }: ExplainabilitySummaryProps) {
  return (
    <div className="mt-4 bg-secondary-container/30 border border-secondary/20 p-3 rounded-lg text-sm text-on-surface leading-relaxed relative overflow-hidden">
      <div className="absolute top-0 left-0 w-1 h-full bg-secondary"></div>
      {children}
    </div>
  );
}

export const ExplainabilityPanel = {
  Root,
  Header,
  Factor,
  Summary
};
