import React from 'react';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { SectionContainer } from './SectionContainer';
import { ChatWidget } from '@/components/chat/ChatWidget';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="flex w-full h-screen bg-background text-on-surface antialiased overflow-hidden">
      <Sidebar />
      <TopNavbar />

      <SectionContainer>{children}</SectionContainer>
      <ChatWidget />
    </div>
  );
}
