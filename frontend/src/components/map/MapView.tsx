import { memo, useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';

import { TaskMarkers, TaskPoint } from '@/components/map/TaskMarkers';
import { VolunteerMarkers, VolunteerPoint } from '@/components/map/VolunteerMarkers';
import { HeatPoint, HeatmapLayer } from '@/components/map/HeatmapLayer';
import { AssignmentLine, AssignmentLines } from '@/components/map/AssignmentLines';

interface Props {
  tasks: TaskPoint[];
  volunteers: VolunteerPoint[];
  heat: HeatPoint[];
  lines: AssignmentLine[];
  center?: [number, number];
}

function RecenterMap({ center }: { center: [number, number] }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);

  return null;
}

function MapViewComponent({
  tasks,
  volunteers,
  heat,
  lines,
  center,
}: Props) {
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);

  useEffect(() => {
    if (!navigator.geolocation) {
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation([position.coords.latitude, position.coords.longitude]);
      },
      () => {
        setUserLocation(null);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  const safeTasks = useMemo(() => tasks.filter((t) => Number.isFinite(t.latitude) && Number.isFinite(t.longitude)), [tasks]);
  const safeVolunteers = useMemo(
    () => volunteers.filter((v) => Number.isFinite(v.latitude) && Number.isFinite(v.longitude)),
    [volunteers]
  );

  const computedCenter = useMemo<[number, number]>(() => {
    if (center) {
      return center;
    }
    if (userLocation) {
      return userLocation;
    }

    const points = [...safeTasks, ...safeVolunteers];
    if (!points.length) {
      return [20.5937, 78.9629];
    }

    const avgLat = points.reduce((sum, point) => sum + point.latitude, 0) / points.length;
    const avgLng = points.reduce((sum, point) => sum + point.longitude, 0) / points.length;
    return [avgLat, avgLng];
  }, [center, safeTasks, safeVolunteers, userLocation]);

  return (
    <MapContainer center={computedCenter} zoom={10} scrollWheelZoom className="h-[420px] w-full rounded-xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <RecenterMap center={computedCenter} />
      <HeatmapLayer points={heat} />
      <AssignmentLines lines={lines} />
      <MarkerClusterGroup chunkedLoading>
        <TaskMarkers tasks={safeTasks} />
        <VolunteerMarkers volunteers={safeVolunteers} />
      </MarkerClusterGroup>
    </MapContainer>
  );
}

export const MapView = memo(MapViewComponent);
