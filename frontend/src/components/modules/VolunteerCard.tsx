import { CardWrapper } from '@/components/ui/CardWrapper';
import { cn } from '@/lib/utils';

export interface VolunteerCardProps {
  name: string;
  role: string;
  location: string;
  avatarUrl: string;
  status: 'deployed' | 'standby' | 'rest';
  burnoutRisk: number; // 0 to 100
}

export function VolunteerCard({ name, role, location, avatarUrl, status, burnoutRisk }: VolunteerCardProps) {
  const isHighRisk = burnoutRisk >= 80;
  
  const getStatusStyle = () => {
    switch(status) {
      case 'deployed': return 'bg-tertiary-container/40 text-tertiary-fixed font-bold border-tertiary-border';
      case 'standby': return 'bg-secondary-container/40 text-secondary border-secondary/20';
      case 'rest': return 'bg-surface-container-highest text-on-surface-variant border-outline-variant/30';
    }
  };

  return (
    <CardWrapper className="col-span-12 md:col-span-6 lg:col-span-4 justify-start gap-4">
      <div className="flex items-start gap-4">
        <div className="relative">
          <img src={avatarUrl} alt={name} className="w-12 h-12 rounded-full object-cover border-2 border-surface-container-highest" />
          <span className={cn("absolute bottom-0 right-0 w-3.5 h-3.5 rounded-full border-2 border-surface-container-lowest", 
            status === 'deployed' ? 'bg-tertiary-fixed' : 
            status === 'standby' ? 'bg-secondary' : 'bg-outline-variant'
          )}></span>
        </div>
        <div className="flex-1">
          <h3 className="text-title-md font-bold text-on-surface leading-tight">{name}</h3>
          <p className="text-sm font-medium text-on-surface-variant flex items-center gap-1 mt-0.5">
            <span className="material-symbols-outlined text-[14px]">badge</span> {role}
          </p>
        </div>
        <span className={cn("px-2 py-0.5 rounded text-[10px] uppercase tracking-wider border font-bold", getStatusStyle())}>
          {status}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-1.5 text-sm text-on-surface-variant font-medium">
        <span className="material-symbols-outlined text-[16px]">location_on</span>
        {location}
      </div>

      <div className="mt-auto border-t border-surface-container-highest pt-4">
        <div className="flex justify-between items-end mb-1">
          <span className="text-label-sm text-xs font-bold uppercase tracking-widest flex items-center gap-1 text-on-surface-variant">
            <span className="material-symbols-outlined text-[14px]">psychology</span> Fatigue Risk
          </span>
          <span className={cn("text-xs font-extrabold", isHighRisk ? "text-error" : "text-primary")}>
            {burnoutRisk}%
          </span>
        </div>
        <div className="w-full bg-surface-container-highest rounded-full h-1.5">
          <div 
            className={cn("h-1.5 rounded-full transition-all", isHighRisk ? "bg-error" : "bg-primary")} 
            style={{ width: `${burnoutRisk}%` }}
          ></div>
        </div>
        {isHighRisk && (
           <p className="text-[10px] uppercase font-bold tracking-widest text-error mt-2.5 flex items-center gap-1">
             <span className="material-symbols-outlined text-[14px]">warning</span> Rotation Recommended
           </p>
        )}
      </div>
    </CardWrapper>
  );
}
