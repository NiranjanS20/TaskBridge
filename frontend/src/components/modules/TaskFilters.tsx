import { CardWrapper } from '@/components/ui/CardWrapper';

export function TaskFilters() {
  return (
    <CardWrapper className="col-span-12 p-3 flex-row items-center gap-4">
      <div className="flex-1 max-w-sm relative">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
          search
        </span>
        <input 
          type="text" 
          placeholder="Filter tasks by destination or id..."
          className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary rounded-t-lg pl-10 pr-4 py-2 text-sm text-on-surface placeholder-on-surface-variant focus:ring-0 focus:ring-opacity-0 transition-all focus-within:ring-2 focus-within:ring-primary-container focus-within:ring-opacity-20"
        />
      </div>
      <div className="hidden md:flex items-center gap-2 border-l border-outline-variant/30 pl-4 h-full">
        <button className="bg-primary-fixed text-primary px-3 py-1.5 rounded-lg text-sm font-bold">All Tasks</button>
        <button className="text-on-surface-variant hover:bg-surface-container-high px-3 py-1.5 rounded-lg text-sm font-medium transition-colors">Critical</button>
        <button className="text-on-surface-variant hover:bg-surface-container-high px-3 py-1.5 rounded-lg text-sm font-medium transition-colors">Active</button>
        <button className="text-on-surface-variant hover:bg-surface-container-high px-3 py-1.5 rounded-lg text-sm font-medium transition-colors">Pending</button>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <button className="text-on-surface-variant hover:bg-surface-container-high p-1.5 rounded-lg transition-colors flex items-center">
            <span className="material-symbols-outlined text-[20px]">filter_list</span>
        </button>
      </div>
    </CardWrapper>
  );
}
