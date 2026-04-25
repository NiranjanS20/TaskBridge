import React from 'react';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { cn } from '@/lib/utils';

export interface UrgencyChartRootProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
}

function Root({ 
  children, 
  title = "Urgency Distribution", 
  subtitle = "Breakdown of active tasks",
  className 
}: UrgencyChartRootProps) {
  return (
    <CardWrapper className={cn("col-span-12 lg:col-span-4", className)}>
      <div>
        <h3 className="text-title-md font-semibold mb-1 text-on-surface">{title}</h3>
        <p className="text-on-surface-variant text-sm mb-6">{subtitle}</p>
      </div>
      <div className="space-y-4">
        {children}
      </div>
    </CardWrapper>
  );
}

export interface UrgencyChartBarProps {
  label: string;
  count: number;
  percentage: number;
  variant: 'critical' | 'urgent' | 'standard' | 'low';
}

function Bar({ label, count, percentage, variant }: UrgencyChartBarProps) {
  const getVariants = () => {
    switch (variant) {
      case 'critical': return { bg: 'bg-error', text: 'text-error' };
      case 'urgent': return { bg: 'bg-secondary', text: 'text-secondary' };
      case 'low': return { bg: 'bg-tertiary', text: 'text-tertiary' };
      case 'standard': 
      default: 
        return { bg: 'bg-primary', text: 'text-primary' };
    }
  };

  const v = getVariants();

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className={cn("font-bold", v.text)}>{label}</span>
        <span className="font-medium text-on-surface">{count}</span>
      </div>
      <div className="w-full bg-surface-container-highest rounded-full h-2">
        <div className={cn("h-2 rounded-full", v.bg)} style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
}

export const UrgencyChart = {
  Root,
  Bar
};
