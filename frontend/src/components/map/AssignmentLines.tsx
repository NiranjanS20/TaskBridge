import { memo } from 'react';
import { Polyline, Tooltip } from 'react-leaflet';

export interface AssignmentLine {
  task_id: string;
  volunteer_id: string;
  from: [number, number];
  to: [number, number];
}

interface Props {
  lines: AssignmentLine[];
}

function AssignmentLinesComponent({ lines }: Props) {
  return (
    <>
      {lines.map((line) => (
        <Polyline
          key={`${line.task_id}-${line.volunteer_id}`}
          positions={[line.from, line.to]}
          pathOptions={{ color: '#2563eb', weight: 2, opacity: 0.65 }}
        >
          <Tooltip>
            Assignment {line.volunteer_id.slice(0, 8)} → {line.task_id.slice(0, 8)}
          </Tooltip>
        </Polyline>
      ))}
    </>
  );
}

export const AssignmentLines = memo(AssignmentLinesComponent);
