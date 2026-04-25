import React from 'react';
import { CardWrapper } from '@/components/ui/CardWrapper';

// --- Root --- 
export interface VASPanelRootProps {
  children: React.ReactNode;
}
function Root({ children }: VASPanelRootProps) {
  return (
    <CardWrapper className="col-span-12 lg:col-span-8 relative group overflow-hidden">
      {/* Decorative Background Gradient */}
      <div className="absolute -right-20 -top-20 w-64 h-64 bg-primary-fixed-dim/30 rounded-full blur-3xl group-hover:bg-primary-fixed-dim/40 transition-colors"></div>
      
      {children}
    </CardWrapper>
  );
}

// --- Header ---
export interface VASPanelHeaderProps {
  title: string;
  subtitle: string;
  efficiencyScore: number;
}
function Header({ title, subtitle, efficiencyScore }: VASPanelHeaderProps) {
  return (
    <div className="relative z-10 flex justify-between items-start mb-8">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
          <h3 className="text-title-md font-semibold text-on-surface">{title}</h3>
        </div>
        <p className="text-body text-sm text-on-surface-variant">{subtitle}</p>
      </div>
      
      <div className="bg-tertiary-container text-tertiary-fixed px-3 py-1 rounded-full text-label-sm font-bold tracking-widest uppercase flex items-center gap-1">
        <span className="material-symbols-outlined text-[14px]">
          {efficiencyScore >= 90 ? 'trending_up' : 'trending_flat'}
        </span>
        {efficiencyScore}% Efficiency
      </div>
    </div>
  );
}

// --- MetricsGrid ---
export interface VASPanelMetricsGridProps {
  children: React.ReactNode;
}
function MetricsGrid({ children }: VASPanelMetricsGridProps) {
  return (
    <div className="relative z-10 grid grid-cols-3 gap-4 mt-auto">
      {children}
    </div>
  );
}

// --- Metric ---
export interface VASPanelMetricProps {
  label: string;
  value: string | number;
  unit?: string;
  valueColorClass?: string;
}
function Metric({ label, value, unit, valueColorClass = "text-on-surface" }: VASPanelMetricProps) {
  return (
    <div className="bg-surface-container-low rounded-lg p-4">
      <p className="text-label text-xs uppercase tracking-[0.05em] font-bold text-on-surface-variant mb-1">
        {label}
      </p>
      <p className={`text-headline text-2xl font-bold ${valueColorClass}`}>
        {value}
        {unit && <span className="text-lg text-on-surface-variant font-medium">{unit}</span>}
      </p>
    </div>
  );
}

export const VASPanel = {
  Root,
  Header,
  MetricsGrid,
  Metric
};
