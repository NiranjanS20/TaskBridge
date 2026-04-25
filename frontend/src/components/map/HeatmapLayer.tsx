import { memo, useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';

export interface HeatPoint {
  latitude: number;
  longitude: number;
  risk_score: number;
}

interface Props {
  points: HeatPoint[];
}

function HeatmapLayerComponent({ points }: Props) {
  const map = useMap();

  useEffect(() => {
    if (!points.length) return;
    const heat = (L as any).heatLayer(
      points.map((p) => [p.latitude, p.longitude, p.risk_score]),
      { radius: 25, blur: 20, maxZoom: 12 }
    );
    heat.addTo(map);
    return () => {
      map.removeLayer(heat);
    };
  }, [map, points]);

  return null;
}

export const HeatmapLayer = memo(HeatmapLayerComponent);
