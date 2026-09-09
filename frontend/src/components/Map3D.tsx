import React, { useEffect, useRef, useState, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import { CanonicalRegionalAssessment, CanonicalReliabilityState } from "../types/dashboard";
import { VERIFIED_DATASET_RECORDS, projectGeoToSvg } from "../data/casesData";
import southAsiaBorders from "../data/south_asia_borders.json";

interface Map3DProps {
  assessments?: CanonicalRegionalAssessment[];
  selectedRegionId?: string;
  onSelectRegion?: (regionId: string) => void;
  selectedCoordinates?: { lat: number; lon: number } | null;
  onCoordinateSelect?: (coords: { lat: number; lon: number; locationName?: string }) => void;
  activeCaseId?: string;
  activeLeadHour?: number;
  showCycloneTrack?: boolean;
}

interface RegionPolygonDef {
  region_id: string;
  name: string;
  short_label: string;
  center_lat: number;
  center_lon: number;
  coords: [number, number][]; // [lat, lon]
}

const REGION_POLYGONS: RegionPolygonDef[] = [
  {
    region_id: "MAR_BOB",
    name: "Bay of Bengal Basin",
    short_label: "Bay of Bengal",
    center_lat: 15.2,
    center_lon: 88.0,
    coords: [
      [8.0, 80.0],
      [15.0, 80.0],
      [21.0, 86.5],
      [22.5, 91.0],
      [20.0, 94.0],
      [14.0, 95.0],
      [8.0, 93.0],
    ],
  },
  {
    region_id: "MAR_AS",
    name: "Arabian Sea Basin",
    short_label: "Arabian Sea",
    center_lat: 16.0,
    center_lon: 65.0,
    coords: [
      [8.0, 55.0],
      [16.0, 55.0],
      [24.5, 62.0],
      [24.0, 69.0],
      [20.0, 72.5],
      [12.0, 74.0],
      [8.0, 74.0],
    ],
  },
  {
    region_id: "IND_ENE",
    name: "East & Northeast India",
    short_label: "East & NE India",
    center_lat: 24.5,
    center_lon: 89.5,
    coords: [
      [20.0, 83.0],
      [26.0, 83.0],
      [27.5, 88.0],
      [29.0, 94.0],
      [27.0, 97.0],
      [23.0, 93.0],
      [21.5, 87.0],
    ],
  },
  {
    region_id: "IND_SOU",
    name: "South Peninsular India",
    short_label: "South Peninsula",
    center_lat: 13.5,
    center_lon: 78.5,
    coords: [
      [8.0, 77.0],
      [11.0, 75.0],
      [15.0, 74.0],
      [18.5, 78.0],
      [18.0, 83.5],
      [13.5, 80.5],
      [9.0, 79.5],
    ],
  },
  {
    region_id: "IND_CEN",
    name: "Central India",
    short_label: "Central India",
    center_lat: 22.0,
    center_lon: 79.5,
    coords: [
      [18.0, 73.0],
      [23.0, 73.0],
      [26.0, 78.0],
      [25.5, 84.5],
      [21.5, 86.0],
      [18.5, 80.0],
    ],
  },
  {
    region_id: "IND_WST",
    name: "West Coast & Gujarat",
    short_label: "West Coast / Gujarat",
    center_lat: 21.5,
    center_lon: 71.5,
    coords: [
      [17.5, 73.0],
      [20.0, 72.5],
      [23.5, 68.0],
      [25.0, 71.0],
      [24.0, 74.5],
      [19.0, 74.0],
    ],
  },
  {
    region_id: "IND_NW",
    name: "Northwest India",
    short_label: "Northwest India",
    center_lat: 30.0,
    center_lon: 74.5,
    coords: [
      [24.0, 68.0],
      [28.0, 69.0],
      [34.0, 73.5],
      [36.0, 77.0],
      [31.0, 80.5],
      [26.0, 78.5],
      [24.0, 73.0],
    ],
  },
];

const RELIABILITY_COLOR_MAP: Record<CanonicalReliabilityState, { fill: string; stroke: string }> = {
  STABLE: { fill: "rgba(34, 197, 94, 0.22)", stroke: "#22c55e" },
  WATCH: { fill: "rgba(245, 158, 11, 0.26)", stroke: "#f59e0b" },
  HIGH_RISK: { fill: "rgba(239, 68, 68, 0.32)", stroke: "#ef4444" },
  DEGRADING: { fill: "rgba(239, 68, 68, 0.28)", stroke: "#f87171" },
  INSUFFICIENT_EVIDENCE: { fill: "rgba(100, 116, 139, 0.16)", stroke: "#64748b" },
};

function detectWebGLSupport(): boolean {
  if (typeof window === "undefined") return false;
  // In automated testing environments (Playwright/CDP without hardware GPU), avoid WebGL lockup:
  if (window.navigator.webdriver) return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch (e) {
    return false;
  }
}

const CARTO_DARK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    "carto-dark": {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
    },
  },
  layers: [
    {
      id: "carto-dark-base",
      type: "raster",
      source: "carto-dark",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

function polygonToSvgPath(coords: [number, number][]): string {
  if (coords.length === 0) return "";
  const points = coords.map(([lat, lon]) => projectGeoToSvg(lat, lon));
  return "M " + points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" L ") + " Z";
}

export const Map3D: React.FC<Map3DProps> = ({
  assessments = [],
  selectedRegionId = "MAR_BOB",
  onSelectRegion,
  selectedCoordinates,
  onCoordinateSelect,
  activeCaseId = "MIDHILI_00Z",
  activeLeadHour = 24,
  showCycloneTrack = true,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const pinMarkerRef = useRef<maplibregl.Marker | null>(null);

  const [hasWebGL, setHasWebGL] = useState<boolean>(() => detectWebGLSupport());
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [currentPitch, setCurrentPitch] = useState<number>(35);
  const [activePreset, setActivePreset] = useState<string>("south-asia");

  // Helper to build GeoJSON from predefined analytical regions
  const buildRegionsGeoJSON = useCallback((): GeoJSON.FeatureCollection => {
    const features: GeoJSON.Feature[] = REGION_POLYGONS.map((region) => {
      const assessment = assessments.find((a) => a.region_id === region.region_id);
      const state = assessment?.reliability_state || "INSUFFICIENT_EVIDENCE";
      const isSelected = region.region_id === selectedRegionId;
      const colors = RELIABILITY_COLOR_MAP[state] || RELIABILITY_COLOR_MAP.INSUFFICIENT_EVIDENCE;

      const ring = region.coords.map(([lat, lon]) => [lon, lat]);
      ring.push(ring[0]);

      return {
        type: "Feature",
        id: region.region_id,
        properties: {
          region_id: region.region_id,
          name: region.name,
          short_label: region.short_label,
          state,
          isSelected,
          fillColor: isSelected ? "rgba(245, 158, 11, 0.40)" : colors.fill,
          strokeColor: isSelected ? "#FBBF24" : colors.stroke,
          lineWidth: isSelected ? 3 : 1.5,
        },
        geometry: {
          type: "Polygon",
          coordinates: [ring],
        },
      };
    });

    return { type: "FeatureCollection", features };
  }, [assessments, selectedRegionId]);

  // Helper to build GeoJSON for cyclone tracks & cone
  const buildCycloneTrackGeoJSON = useCallback((): {
    track: GeoJSON.FeatureCollection;
    cone: GeoJSON.FeatureCollection;
    points: GeoJSON.FeatureCollection;
  } => {
    const stormRecords = VERIFIED_DATASET_RECORDS.filter(
      (r) => r.cycle_label === activeCaseId || r.storm_id?.includes(activeCaseId.replace("_00Z", "").replace("_12Z", ""))
    ).sort((a, b) => a.forecast_lead_hours - b.forecast_lead_hours);

    const trackPoints: [number, number][] = [];
    const conePointsUpper: [number, number][] = [];
    const conePointsLower: [number, number][] = [];
    const pointFeatures: GeoJSON.Feature[] = [];

    stormRecords.forEach((record) => {
      const lon = record.forecast_lon;
      const lat = record.forecast_lat;
      trackPoints.push([lon, lat]);

      const spreadDeg = Math.max(0.3, (record.ensemble_spread_km || 50) / 111.0);
      conePointsUpper.push([lon, lat + spreadDeg]);
      conePointsLower.unshift([lon, lat - spreadDeg]);

      const isCurrentLead = record.forecast_lead_hours === activeLeadHour;

      pointFeatures.push({
        type: "Feature",
        properties: {
          lead_label: `+${record.forecast_lead_hours}h`,
          lead_hours: record.forecast_lead_hours,
          isCurrentLead,
          track_error_km: record.track_error_km,
          spread_km: record.ensemble_spread_km,
          bust_label: record.bust_label,
        },
        geometry: {
          type: "Point",
          coordinates: [lon, lat],
        },
      });
    });

    const trackFeature: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features:
        trackPoints.length > 1
          ? [
              {
                type: "Feature",
                properties: { caseId: activeCaseId },
                geometry: {
                  type: "LineString",
                  coordinates: trackPoints,
                },
              },
            ]
          : [],
    };

    const conePolygon =
      conePointsUpper.length > 1 && conePointsLower.length > 1
        ? [[...conePointsUpper, ...conePointsLower, conePointsUpper[0]]]
        : [];

    const coneFeature: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features:
        conePolygon.length > 0
          ? [
              {
                type: "Feature",
                properties: { caseId: activeCaseId },
                geometry: {
                  type: "Polygon",
                  coordinates: conePolygon,
                },
              },
            ]
          : [],
    };

    return {
      track: trackFeature,
      cone: coneFeature,
      points: { type: "FeatureCollection", features: pointFeatures },
    };
  }, [activeCaseId, activeLeadHour]);

  // WebGL Map Initialization (when WebGL is supported)
  useEffect(() => {
    if (!hasWebGL || !mapContainerRef.current) return;

    try {
      const map = new maplibregl.Map({
        container: mapContainerRef.current,
        style: CARTO_DARK_STYLE,
        center: [82.0, 18.0],
        zoom: 4.3,
        pitch: 35,
        bearing: 0,
        maxPitch: 65,
        attributionControl: false,
      });

      mapRef.current = map;

      map.addControl(new maplibregl.NavigationControl({ showCompass: true, showZoom: true }), "top-right");

      map.on("load", () => {
        // Analytical Region Layers
        map.addSource("fg-regions", {
          type: "geojson",
          data: buildRegionsGeoJSON(),
        });

        map.addLayer({
          id: "fg-regions-fill",
          type: "fill",
          source: "fg-regions",
          paint: {
            "fill-color": ["get", "fillColor"],
            "fill-opacity": 0.5,
          },
        });

        map.addLayer({
          id: "fg-regions-line",
          type: "line",
          source: "fg-regions",
          paint: {
            "line-color": ["get", "strokeColor"],
            "line-width": ["get", "lineWidth"],
            "line-opacity": 0.9,
          },
        });

        // Cyclone Layers
        const cycloneData = buildCycloneTrackGeoJSON();

        map.addSource("fg-cyclone-cone", {
          type: "geojson",
          data: cycloneData.cone,
        });

        map.addLayer({
          id: "fg-cyclone-cone-fill",
          type: "fill",
          source: "fg-cyclone-cone",
          paint: {
            "fill-color": "#F59E0B",
            "fill-opacity": 0.15,
          },
        });

        map.addLayer({
          id: "fg-cyclone-cone-line",
          type: "line",
          source: "fg-cyclone-cone",
          paint: {
            "line-color": "#F59E0B",
            "line-width": 1.2,
            "line-dasharray": [2, 2],
            "line-opacity": 0.5,
          },
        });

        map.addSource("fg-cyclone-track", {
          type: "geojson",
          data: cycloneData.track,
        });

        map.addLayer({
          id: "fg-cyclone-track-line",
          type: "line",
          source: "fg-cyclone-track",
          paint: {
            "line-color": "#FBBF24",
            "line-width": 3,
            "line-opacity": 0.85,
          },
        });

        map.addSource("fg-cyclone-points", {
          type: "geojson",
          data: cycloneData.points,
        });

        map.addLayer({
          id: "fg-cyclone-points-circle",
          type: "circle",
          source: "fg-cyclone-points",
          paint: {
            "circle-radius": [
              "case",
              ["boolean", ["get", "isCurrentLead"], false],
              7,
              4,
            ],
            "circle-color": [
              "case",
              ["boolean", ["get", "isCurrentLead"], false],
              "#EF4444",
              "#FBBF24",
            ],
            "circle-stroke-color": "#FFFFFF",
            "circle-stroke-width": 1.5,
          },
        });

        // Region Click Interaction
        map.on("click", "fg-regions-fill", (e: any) => {
          if (e.features && e.features[0]) {
            const regionId = e.features[0].properties?.region_id;
            if (regionId && onSelectRegion) {
              onSelectRegion(regionId);
            }
          }
        });

        map.on("mouseenter", "fg-regions-fill", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "fg-regions-fill", () => {
          map.getCanvas().style.cursor = "";
        });
      });

      // General Map Click for Coordinate Selection
      map.on("click", (e: any) => {
        const { lng, lat } = e.lngLat;
        const formattedLat = Math.round(lat * 1000) / 1000;
        const formattedLon = Math.round(lng * 1000) / 1000;

        if (onCoordinateSelect) {
          onCoordinateSelect({
            lat: formattedLat,
            lon: formattedLon,
            locationName: `Custom Coordinates (${formattedLat > 0 ? formattedLat + "°N" : -formattedLat + "°S"}, ${formattedLon > 0 ? formattedLon + "°E" : -formattedLon + "°W"})`,
          });
        }
      });

      map.on("mousemove", (e: any) => {
        setCursorCoords({
          lat: Math.round(e.lngLat.lat * 100) / 100,
          lon: Math.round(e.lngLat.lng * 100) / 100,
        });
      });

      const canvas = map.getCanvas();
      const handleMouseLeave = () => setCursorCoords(null);
      canvas.addEventListener("mouseleave", handleMouseLeave);

      map.on("pitch", () => {
        setCurrentPitch(Math.round(map.getPitch()));
      });

      return () => {
        canvas.removeEventListener("mouseleave", handleMouseLeave);
        map.remove();
        mapRef.current = null;
      };
    } catch (err) {
      // Graceful fallback to SVG renderer if WebGL encounters issues
      setHasWebGL(false);
    }
  }, [hasWebGL]);

  // Update Regions Layer Data when assessments change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const source = map.getSource("fg-regions") as maplibregl.GeoJSONSource;
    if (source) {
      source.setData(buildRegionsGeoJSON());
    }
  }, [buildRegionsGeoJSON]);

  // Update Cyclone Track Data when case changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const cycloneData = buildCycloneTrackGeoJSON();

    const trackSource = map.getSource("fg-cyclone-track") as maplibregl.GeoJSONSource;
    if (trackSource) trackSource.setData(cycloneData.track);

    const coneSource = map.getSource("fg-cyclone-cone") as maplibregl.GeoJSONSource;
    if (coneSource) coneSource.setData(cycloneData.cone);

    const pointsSource = map.getSource("fg-cyclone-points") as maplibregl.GeoJSONSource;
    if (pointsSource) pointsSource.setData(cycloneData.points);
  }, [buildCycloneTrackGeoJSON]);

  // Update Pin Marker on Coordinate Select
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (!selectedCoordinates) {
      if (pinMarkerRef.current) {
        pinMarkerRef.current.remove();
        pinMarkerRef.current = null;
      }
      return;
    }

    if (!pinMarkerRef.current) {
      const el = document.createElement("div");
      el.className = "fg-3d-pin-marker";
      el.innerHTML = `
        <div class="pin-pulse"></div>
        <div class="pin-dot"></div>
      `;
      pinMarkerRef.current = new maplibregl.Marker({ element: el, anchor: "center" })
        .setLngLat([selectedCoordinates.lon, selectedCoordinates.lat])
        .addTo(map);
    } else {
      pinMarkerRef.current.setLngLat([selectedCoordinates.lon, selectedCoordinates.lat]);
    }
  }, [selectedCoordinates]);

  // Preset Views
  const flyToPreset = (presetKey: string) => {
    setActivePreset(presetKey);
    const map = mapRef.current;
    if (!map) return;

    switch (presetKey) {
      case "south-asia":
        map.flyTo({ center: [82.0, 18.0], zoom: 4.3, pitch: 35, bearing: 0, essential: true });
        break;
      case "bay-of-bengal":
        map.flyTo({ center: [88.5, 16.5], zoom: 5.4, pitch: 45, bearing: 10, essential: true });
        break;
      case "arabian-sea":
        map.flyTo({ center: [67.0, 18.5], zoom: 5.3, pitch: 45, bearing: -10, essential: true });
        break;
      case "globe":
        map.flyTo({ center: [78.0, 15.0], zoom: 2.8, pitch: 20, bearing: 0, essential: true });
        break;
    }
  };

  const togglePitch3D = () => {
    const nextPitch = currentPitch > 20 ? 0 : 50;
    setCurrentPitch(nextPitch);
    const map = mapRef.current;
    if (map) {
      map.easeTo({ pitch: nextPitch, duration: 600 });
    }
  };

  // SVG Fallback Track records
  const stormRecords = VERIFIED_DATASET_RECORDS.filter(
    (r) => r.cycle_label === activeCaseId || r.storm_id?.includes(activeCaseId.replace("_00Z", "").replace("_12Z", ""))
  ).sort((a, b) => a.forecast_lead_hours - b.forecast_lead_hours);

  return (
    <div className="fg-3d-map-wrapper relative w-full h-full min-h-[420px] overflow-hidden bg-[#0A1017] rounded-xl border border-border/40 shadow-2xl">
      {hasWebGL ? (
        /* Real WebGL Map Container */
        <div ref={mapContainerRef} className="w-full h-full absolute inset-0" />
      ) : (
        /* Vector SVG Fallback with CSS 3D Tilt Perspective */
        <div
          className="w-full h-full absolute inset-0 flex items-center justify-center p-2"
          style={{
            perspective: "1000px",
          }}
        >
          <svg
            viewBox="0 0 880 540"
            className="w-full h-full max-h-full transition-transform duration-500 ease-out cursor-crosshair"
            style={{
              transform: currentPitch > 20 ? `rotateX(${Math.min(currentPitch, 45)}deg) scale(0.96)` : "none",
              transformOrigin: "center 70%",
            }}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const svgX = ((e.clientX - rect.left) / rect.width) * 880;
              const svgY = ((e.clientY - rect.top) / rect.height) * 540;
              // Approximate inverse projection: lon = 84.2 + (x - 503)/12.4, lat = 10.5 - (y - 469)/18.8
              const calcLon = Math.round((84.2 + (svgX - 503) / 12.4) * 10) / 10;
              const calcLat = Math.round((10.5 - (svgY - 469) / 18.8) * 10) / 10;
              if (onCoordinateSelect) {
                onCoordinateSelect({
                  lat: calcLat,
                  lon: calcLon,
                  locationName: `Custom Coordinates (${calcLat}°N, ${calcLon}°E)`,
                });
              }
            }}
            onMouseMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const svgX = ((e.clientX - rect.left) / rect.width) * 880;
              const svgY = ((e.clientY - rect.top) / rect.height) * 540;
              const calcLon = Math.round((84.2 + (svgX - 503) / 12.4) * 10) / 10;
              const calcLat = Math.round((10.5 - (svgY - 469) / 18.8) * 10) / 10;
              setCursorCoords({ lat: calcLat, lon: calcLon });
            }}
            onMouseLeave={() => setCursorCoords(null)}
          >
            <defs>
              <pattern id="grid-pattern-3d" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="0.8" />
              </pattern>
            </defs>

            {/* Background Grid */}
            <rect width="880" height="540" fill="#0A1017" />
            <rect width="880" height="540" fill="url(#grid-pattern-3d)" />

            {/* South Asia Coastlines */}
            {southAsiaBorders && Array.isArray((southAsiaBorders as any).features) && (
              <g className="coastline-features" opacity="0.35">
                {(southAsiaBorders as any).features.map((feat: any, idx: number) => {
                  if (feat.geometry?.type === "Polygon") {
                    const ring = feat.geometry.coordinates[0];
                    const pts = ring.map(([lon, lat]: [number, number]) => projectGeoToSvg(lat, lon));
                    const d = "M " + pts.map((p: any) => `${p.x},${p.y}`).join(" L ") + " Z";
                    return <path key={idx} d={d} fill="none" stroke="#64748b" strokeWidth="0.8" />;
                  }
                  return null;
                })}
              </g>
            )}

            {/* Analytical Region Polygons */}
            {REGION_POLYGONS.map((region) => {
              const assessment = assessments.find((a) => a.region_id === region.region_id);
              const state = assessment?.reliability_state || "INSUFFICIENT_EVIDENCE";
              const isSelected = region.region_id === selectedRegionId;
              const colors = RELIABILITY_COLOR_MAP[state] || RELIABILITY_COLOR_MAP.INSUFFICIENT_EVIDENCE;
              const pathD = polygonToSvgPath(region.coords);
              const center = projectGeoToSvg(region.center_lat, region.center_lon);

              return (
                <g
                  key={region.region_id}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSelectRegion) onSelectRegion(region.region_id);
                  }}
                  className="cursor-pointer transition-opacity hover:opacity-90"
                >
                  <path
                    d={pathD}
                    fill={isSelected ? "rgba(245, 158, 11, 0.35)" : colors.fill}
                    stroke={isSelected ? "#FBBF24" : colors.stroke}
                    strokeWidth={isSelected ? 2.5 : 1.2}
                  />
                  <text
                    x={center.x}
                    y={center.y}
                    fill="#F1F5F9"
                    fontSize="10"
                    fontFamily="monospace"
                    fontWeight="bold"
                    textAnchor="middle"
                    pointerEvents="none"
                  >
                    {region.short_label}
                  </text>
                </g>
              );
            })}

            {/* Cyclone Tracks and Points */}
            {showCycloneTrack && stormRecords.length > 1 && (
              <g className="cyclone-track-overlay">
                {/* Track Line */}
                <path
                  d={
                    "M " +
                    stormRecords
                      .map((r) => {
                        const p = projectGeoToSvg(r.forecast_lat, r.forecast_lon);
                        return `${p.x},${p.y}`;
                      })
                      .join(" L ")
                  }
                  fill="none"
                  stroke="#FBBF24"
                  strokeWidth="3"
                  strokeDasharray="4 2"
                  opacity="0.9"
                />

                {/* Track Fix Dots */}
                {stormRecords.map((r) => {
                  const p = projectGeoToSvg(r.forecast_lat, r.forecast_lon);
                  const isCur = r.forecast_lead_hours === activeLeadHour;
                  return (
                    <circle
                      key={r.forecast_lead_hours}
                      cx={p.x}
                      cy={p.y}
                      r={isCur ? 6 : 3.5}
                      fill={isCur ? "#EF4444" : "#FBBF24"}
                      stroke="#FFFFFF"
                      strokeWidth={1.5}
                    />
                  );
                })}
              </g>
            )}

            {/* Selected Coordinates Pin Marker */}
            {selectedCoordinates && (
              <g
                transform={`translate(${projectGeoToSvg(selectedCoordinates.lat, selectedCoordinates.lon).x}, ${
                  projectGeoToSvg(selectedCoordinates.lat, selectedCoordinates.lon).y
                })`}
              >
                <circle r="14" fill="rgba(245, 184, 61, 0.3)" className="animate-ping" />
                <circle r="6" fill="#F5B83D" stroke="#FFFFFF" strokeWidth="2" />
              </g>
            )}
          </svg>
        </div>
      )}

      {/* Top Controls Overlay: Presets & 3D Tilt */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-1.5 bg-[#0C131B]/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 shadow-lg text-xs">
        <span className="text-[10px] font-mono text-muted uppercase tracking-wider mr-1">PRESET:</span>
        <button
          type="button"
          onClick={() => flyToPreset("south-asia")}
          className={`px-2.5 py-1 rounded transition-all font-mono text-[11px] ${
            activePreset === "south-asia"
              ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 font-semibold"
              : "text-slate-300 hover:text-white hover:bg-white/5"
          }`}
        >
          South Asia
        </button>
        <button
          type="button"
          onClick={() => flyToPreset("bay-of-bengal")}
          className={`px-2.5 py-1 rounded transition-all font-mono text-[11px] ${
            activePreset === "bay-of-bengal"
              ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 font-semibold"
              : "text-slate-300 hover:text-white hover:bg-white/5"
          }`}
        >
          Bay of Bengal
        </button>
        <button
          type="button"
          onClick={() => flyToPreset("arabian-sea")}
          className={`px-2.5 py-1 rounded transition-all font-mono text-[11px] ${
            activePreset === "arabian-sea"
              ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 font-semibold"
              : "text-slate-300 hover:text-white hover:bg-white/5"
          }`}
        >
          Arabian Sea
        </button>
        <button
          type="button"
          onClick={() => flyToPreset("globe")}
          className={`px-2.5 py-1 rounded transition-all font-mono text-[11px] ${
            activePreset === "globe"
              ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 font-semibold"
              : "text-slate-300 hover:text-white hover:bg-white/5"
          }`}
        >
          Synoptic
        </button>

        <div className="h-4 w-px bg-white/10 mx-1" />

        {/* 3D Tilt Toggle */}
        <button
          type="button"
          onClick={togglePitch3D}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono text-slate-200 transition-all"
          title="Toggle 3D perspective / Flat 2D view"
        >
          <span className="text-amber-400 font-bold">3D</span>
          <span>{currentPitch > 20 ? `${currentPitch}° Tilt` : "Flat 2D"}</span>
        </button>
      </div>

      {/* Real-time Cursor Lat/Lon HUD Inspector */}
      <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2 bg-[#0C131B]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 text-[11px] font-mono text-slate-300 pointer-events-none shadow-md">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        {cursorCoords ? (
          <span>
            {cursorCoords.lat >= 0 ? `${cursorCoords.lat.toFixed(2)}°N` : `${(-cursorCoords.lat).toFixed(2)}°S`}
            {"  "}
            {cursorCoords.lon >= 0 ? `${cursorCoords.lon.toFixed(2)}°E` : `${(-cursorCoords.lon).toFixed(2)}°W`}
          </span>
        ) : (
          <span className="text-slate-400">Click anywhere to pin live forecast coordinates</span>
        )}
      </div>

      {/* Operational Map Legend Overlay (Bottom Right) */}
      <div className="absolute bottom-3 right-3 z-10 flex items-center gap-3 bg-[#0C131B]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 text-[10px] font-mono text-slate-300 shadow-md">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span>STABLE</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-400" />
          <span>WATCH</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          <span>HIGH RISK</span>
        </div>
        {showCycloneTrack && (
          <div className="flex items-center gap-1 border-l border-white/10 pl-2">
            <span className="w-3 h-0.5 bg-amber-400" />
            <span>NEPS TRACK</span>
          </div>
        )}
      </div>
    </div>
  );
};
