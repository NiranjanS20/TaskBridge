import { CardWrapper } from '@/components/ui/CardWrapper';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface Props {
  workload: Array<{ volunteer_id: string; tasks: number }>;
  burnout: Array<{ burnout_score: number; count: number }>;
}

export function Charts({ workload, burnout }: Props) {
  return (
    <>
      <CardWrapper className="col-span-12 lg:col-span-8 h-[360px]">
        <h3 className="text-lg font-semibold text-on-surface mb-4">Workload Distribution</h3>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={workload}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="volunteer_id" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="tasks" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardWrapper>

      <CardWrapper className="col-span-12 lg:col-span-4 h-[360px]">
        <h3 className="text-lg font-semibold text-on-surface mb-4">Burnout Distribution</h3>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={burnout}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="burnout_score" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#f97316" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardWrapper>
    </>
  );
}
