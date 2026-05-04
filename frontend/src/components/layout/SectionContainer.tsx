import React from 'react';
import { cn } from '@/lib/utils';

export interface SectionContainerProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  as?: React.ElementType;
}

export function SectionContainer({
  children,
  className,
  as: Component = 'main',
  ...props
}: SectionContainerProps) {
  return (
    <Component
      className={cn(
        'ml-64 mt-16 p-8 w-full h-[calc(100vh-4rem)] overflow-y-auto overflow-x-hidden bg-surface',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
