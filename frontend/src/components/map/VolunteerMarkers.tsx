import { memo } from 'react';
import { Marker, Popup } from 'react-leaflet';

export interface VolunteerPoint {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  status?: string;
  burnout_score?: number;
}

interface Props {
  volunteers: VolunteerPoint[];
}

function VolunteerMarkersComponent({ volunteers }: Props) {
  return (
    <>
      {volunteers.map((volunteer) => (
        <Marker key={`vol-${volunteer.id}`} position={[volunteer.latitude, volunteer.longitude]}>
          <Popup>
            <div className="text-sm">
              <div className="font-semibold">{volunteer.name}</div>
              <div>Status: {volunteer.status ?? 'unknown'}</div>
              <div>Burnout: {((volunteer.burnout_score ?? 0) * 100).toFixed(1)}%</div>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export const VolunteerMarkers = memo(VolunteerMarkersComponent);
