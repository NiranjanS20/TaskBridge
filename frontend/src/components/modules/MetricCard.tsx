import { CardWrapper } from '@/components/ui/CardWrapper';
import { cn } from '@/lib/utils';

export interface MetricCardProps {
  title: string;
  icon: string;
  iconColorClass?: string;
  mainValue: string | number;
  primarySubValue: string | number;
  primarySubLabel: string;
  primarySubColorClass?: string;
  secondarySubValue: string | number;
  secondarySubLabel: string;
  variant?: 'default' | 'error';
}

export function MetricCard({
  title,
  icon,
  iconColorClass = 'text-primary',
  mainValue,
  primarySubValue,
  primarySubLabel,
  primarySubColorClass = 'text-primary',
  secondarySubValue,
  secondarySubLabel,
  variant = 'default'
}: MetricCardProps) {
  const isError = variant === 'error';

  return (
    <CardWrapper variant={variant}>
      <div className={cn("flex items-center gap-2 mb-4", !isError && "text-on-surface")}>
        <span className={cn("material-symbols-outlined text-[24px]", !isError && iconColorClass)}>
          {icon}
        </span>
        <h3 className={cn("text-title-md font-semibold", !isError && "text-on-surface")}>
          {title}
        </h3>
      </div>
      
      <div className={cn("flex items-end justify-between", !isError && "text-on-surface")}>
        <p className="text-headline text-4xl font-extrabold">
          {mainValue}
        </p>
        <div className={cn("text-sm font-medium text-right", !isError && "text-on-surface-variant")}>
          <p className={isError ? "font-bold" : ""}>
            <span className={!isError ? primarySubColorClass : ""}>{primarySubValue}</span> {primarySubLabel}
          </p>
          <p>{secondarySubValue} {secondarySubLabel}</p>
        </div>
      </div>
    </CardWrapper>
  );
}
