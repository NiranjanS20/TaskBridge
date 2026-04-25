import { CardWrapper } from '@/components/ui/CardWrapper';
import { cn } from '@/lib/utils';

export interface TaskCardProps {
  title: string;
  location: string;
  priority: 'critical' | 'urgent' | 'standard' | 'low';
  status: 'active' | 'pending';
  assignees: string[]; 
  timeAgo: string;
}

export function TaskCard({ title, location, priority, status, assignees, timeAgo }: TaskCardProps) {
  const getPriorityStyle = () => {
    switch(priority) {
      case 'critical': return 'bg-error text-on-error';
      case 'urgent': return 'bg-secondary text-on-secondary';
      case 'low': return 'bg-tertiary-container text-tertiary-fixed';
      default: return 'bg-primary text-on-primary';
    }
  };

  return (
    <CardWrapper className="col-span-12 md:col-span-6 lg:col-span-4 justify-start gap-4">
      <div className="flex justify-between items-start">
        <div>
          <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider", getPriorityStyle())}>
            {priority}
          </span>
          <h3 className="text-title-md font-semibold text-on-surface mt-2 leading-tight">{title}</h3>
        </div>
        <button className="text-on-surface-variant hover:text-primary transition-colors">
          <span className="material-symbols-outlined text-[20px]">more_vert</span>
        </button>
      </div>
      
      <div className="flex items-center gap-1.5 text-sm text-on-surface-variant font-medium">
        <span className="material-symbols-outlined text-[16px]">location_on</span>
        {location}
      </div>

      <div className="mt-auto border-t border-surface-container-highest pt-4 flex justify-between items-center">
        {/* Assignment Indicators */}
        <div className="flex -space-x-2">
          {assignees.map((src, i) => (
            <img 
              key={i} 
              src={src} 
              className="w-8 h-8 rounded-full border-2 border-surface-container-lowest object-cover" 
              alt="Assignee"
            />
          ))}
          {assignees.length === 0 && (
            <div className="w-8 h-8 rounded-full border-2 border-dashed border-outline-variant/60 bg-surface-container-highest flex items-center justify-center text-on-surface-variant text-xs font-bold">
              +
            </div>
          )}
        </div>

        <div className="text-right">
          <p className="text-sm font-bold text-on-surface capitalize flex items-center gap-1 justify-end">
             {status === 'active' && <span className="w-2 h-2 rounded-full bg-tertiary-fixed-dim animate-pulse"></span>}
             {status === 'pending' && <span className="w-2 h-2 rounded-full bg-secondary-container"></span>}
             {status}
          </p>
          <p className="text-label-sm text-xs text-on-surface-variant uppercase tracking-widest mt-0.5">{timeAgo}</p>
        </div>
      </div>
    </CardWrapper>
  );
}
