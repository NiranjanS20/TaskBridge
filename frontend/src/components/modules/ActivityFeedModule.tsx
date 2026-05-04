import React from 'react';
import { CardWrapper } from '@/components/ui/CardWrapper';
import { cn } from '@/lib/utils';

export interface ActivityFeedRootProps {
  children: React.ReactNode;
  title?: string;
  onViewAll?: () => void;
  className?: string;
}

function Root({ 
  children, 
  title = "Real-time Activity Feed", 
  onViewAll,
  className 
}: ActivityFeedRootProps) {
  return (
    <CardWrapper className={cn("col-span-12 lg:col-span-4 h-[400px] justify-start", className)}>
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-title-md font-semibold text-on-surface">{title}</h3>
        <button 
          onClick={onViewAll}
          className="text-primary hover:text-primary-container text-sm font-medium transition-colors"
        >
          View All
        </button>
      </div>
      <div className="flex-1 overflow-y-auto pr-2 space-y-5">
        {children}
      </div>
    </CardWrapper>
  );
}

export interface ActivityFeedItemProps {
  icon: string;
  iconColorClass: string;
  iconBgClass: string;
  title: React.ReactNode;
  timestamp: string;
}

function Item({ 
  icon, 
  iconColorClass, 
  iconBgClass, 
  title, 
  timestamp 
}: ActivityFeedItemProps) {
  return (
    <div className="flex gap-4">
      <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0", iconBgClass)}>
        <span className={cn("material-symbols-outlined text-[16px]", iconColorClass)}>
          {icon}
        </span>
      </div>
      <div>
        <p className="text-body text-sm text-on-surface">{title}</p>
        <p className="text-label-sm text-xs text-on-surface-variant mt-1 uppercase tracking-widest">
          {timestamp}
        </p>
      </div>
    </div>
  );
}

export const ActivityFeed = {
  Root,
  Item
};
