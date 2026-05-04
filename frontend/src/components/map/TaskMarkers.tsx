import { memo } from 'react';
import { Marker, Popup } from 'react-leaflet';

export interface TaskPoint {
  id: string;
  title: string;
  latitude: number;
  longitude: number;
  urgency?: number;
  status?: string;
}

interface Props {
  tasks: TaskPoint[];
}

function TaskMarkersComponent({ tasks }: Props) {
  return (
    <>
      {tasks.map((task) => (
        <Marker key={`task-${task.id}`} position={[task.latitude, task.longitude]}>
          <Popup>
            <div className="text-sm">
              <div className="font-semibold">{task.title}</div>
              <div>Status: {task.status ?? 'unknown'}</div>
              <div>Urgency: {task.urgency ?? '-'}</div>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export const TaskMarkers = memo(TaskMarkersComponent);
