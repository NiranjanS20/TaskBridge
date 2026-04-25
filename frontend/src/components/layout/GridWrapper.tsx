import React from 'react';
import { cn } from '@/lib/utils';

export interface GridWrapperProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function GridWrapper({ children, className, ...props }: GridWrapperProps) {
  return (
    <div
      className={cn('grid grid-cols-12 gap-6 pb-12', className)}
      {...props}
    >
      {children}
    </div>
  );
}
