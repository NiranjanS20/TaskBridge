import React from 'react';
import { cn } from '@/lib/utils';

export interface CardWrapperProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'error';
  interactive?: boolean;
}

export function CardWrapper({ 
  children, 
  className, 
  variant = 'default',
  interactive = true,
  ...props 
}: CardWrapperProps) {
  return (
    <div 
      className={cn(
        "rounded-xl p-6 flex flex-col justify-between transition-all duration-400 ease-out will-change-transform",
        interactive && "hover:-translate-y-1 hover:shadow-[0_20px_40px_-12px_rgba(0,0,0,0.1)]",
        variant === 'default' && "bg-surface-container-lowest ambient-shadow",
        variant === 'error' && "bg-error-container border border-error/20 text-on-error-container shadow-[0_8px_32px_rgba(186,26,26,0.1)]",
        className
      )} 
      {...props}
    >
      {children}
    </div>
  );
}
