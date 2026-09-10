/**
 * Preset canonical multi-lead forecast payloads for testing and operational demonstration.
 * Fully valid ISO-8601 timestamps, explicit physical units, and zero future observation leakage.
 */

import { MultiLeadForecastInput, EnsembleMemberInput } from "../types/timeline";

function generateEnsemble(
  centerLat: number,
  centerLon: number,
  spreadDeg: number,
  memberCount: number = 11,
  baseMslp: number = 998.0
): EnsembleMemberInput[] {
  const members: EnsembleMemberInput[] = [];
  for (let i = 0; i < memberCount; i++) {
    const angle = (2 * Math.PI * i) / memberCount;
    const r = spreadDeg * (0.4 + 0.6 * Math.sin(i * 2.5 + 1.2));
    const dLat = r * Math.cos(angle);
    const dLon = (r * Math.sin(angle)) / Math.cos((centerLat * Math.PI) / 180);
    members.push({
      member_id: i + 1,
      latitude: Number((centerLat + dLat).toFixed(4)),
      longitude: Number((centerLon + dLon).toFixed(4)),
      central_pressure_hpa: Number((baseMslp + (i % 5) * 1.2 - 2.5).toFixed(1)),
    });
  }
  return members;
}

// 1. Preset: Cyclone Midhili Multi-Lead (D+1 to D+5)
export const PRESET_MIDHILI_MULTI_LEAD: MultiLeadForecastInput = {
  forecast_source: "NCMRWF TIGGE",
  model: "NCMRWF_NEPS",
  forecast_cycle: "2023-11-15T00:00:00Z",
  variable: "Mean Sea Level Pressure (msl)",
  units: "hPa",
  region: "MAR_BOB",
  leads: [
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 24,
      valid_time: "2023-11-16T00:00:00Z",
      latitude: 14.5,
      longitude: 87.0,
      region: "MAR_BOB",
      units: "hPa",
      value: 998.2,
      deterministic_lat: 14.6,
      deterministic_lon: 87.1,
      ensemble_members: generateEnsemble(14.5, 87.0, 0.35, 11, 998.0),
    },
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 48,
      valid_time: "2023-11-17T00:00:00Z",
      latitude: 17.8,
      longitude: 88.5,
      region: "MAR_BOB",
      units: "hPa",
      value: 992.5,
      deterministic_lat: 18.0,
      deterministic_lon: 88.7,
      ensemble_members: generateEnsemble(17.8, 88.5, 0.55, 11, 992.0),
    },
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 72,
      valid_time: "2023-11-18T00:00:00Z",
      latitude: 21.2,
      longitude: 90.2,
      region: "MAR_BOB",
      units: "hPa",
      value: 996.0,
      deterministic_lat: 21.5,
      deterministic_lon: 90.6,
      ensemble_members: generateEnsemble(21.2, 90.2, 0.85, 11, 996.0),
    },
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 96,
      valid_time: "2023-11-19T00:00:00Z",
      latitude: 23.8,
      longitude: 91.8,
      region: "MAR_BOB",
      units: "hPa",
      value: 1002.0,
      deterministic_lat: 24.1,
      deterministic_lon: 92.2,
      ensemble_members: generateEnsemble(23.8, 91.8, 1.25, 11, 1002.0),
    },
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 120,
      valid_time: "2023-11-20T00:00:00Z",
      latitude: 25.5,
      longitude: 93.0,
      region: "MAR_BOB",
      units: "hPa",
      value: 1006.5,
      deterministic_lat: 25.9,
      deterministic_lon: 93.5,
      ensemble_members: generateEnsemble(25.5, 93.0, 1.70, 11, 1006.0),
    },
  ],
};

// 2. Preset: 10-Day Medium-Range Sequence (D+1 to D+10)
export const PRESET_10DAY_EXTENDED: MultiLeadForecastInput = {
  forecast_source: "NCMRWF TIGGE",
  model: "NCMRWF_NEPS",
  forecast_cycle: "2023-12-01T00:00:00Z",
  variable: "Mean Sea Level Pressure (msl)",
  units: "hPa",
  region: "MAR_BOB",
  leads: Array.from({ length: 10 }, (_, idx) => {
    const day = idx + 1;
    const hours = day * 24;
    const lat = 10.0 + idx * 1.5;
    const lon = 84.0 + idx * 0.8;
    const spread = 0.3 + idx * 0.22;
    const validDate = new Date(Date.UTC(2023, 11, 1 + day, 0, 0, 0)).toISOString();
    return {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-12-01T00:00:00Z",
      lead_hours: hours,
      valid_time: validDate,
      latitude: Number(lat.toFixed(2)),
      longitude: Number(lon.toFixed(2)),
      region: "MAR_BOB",
      units: "hPa",
      value: 1000 - idx * 2,
      deterministic_lat: Number((lat + 0.15 * idx).toFixed(2)),
      deterministic_lon: Number((lon + 0.12 * idx).toFixed(2)),
      ensemble_members: generateEnsemble(lat, lon, spread, 11, 1000 - idx * 2),
    };
  }),
};

// 3. Preset: Partial Ensemble Coverage (6 members - DATA DEGRADED)
export const PRESET_DEGRADED_ENSEMBLE: MultiLeadForecastInput = {
  forecast_source: "NCMRWF TIGGE",
  model: "NCMRWF_NEPS",
  forecast_cycle: "2023-11-15T00:00:00Z",
  variable: "Mean Sea Level Pressure (msl)",
  units: "hPa",
  region: "MAR_BOB",
  leads: [
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 24,
      valid_time: "2023-11-16T00:00:00Z",
      latitude: 14.5,
      longitude: 87.0,
      region: "MAR_BOB",
      units: "hPa",
      ensemble_members: generateEnsemble(14.5, 87.0, 0.4, 6, 998.0),
    },
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 48,
      valid_time: "2023-11-17T00:00:00Z",
      latitude: 17.8,
      longitude: 88.5,
      region: "MAR_BOB",
      units: "hPa",
      ensemble_members: generateEnsemble(17.8, 88.5, 0.7, 6, 992.0),
    },
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 72,
      valid_time: "2023-11-18T00:00:00Z",
      latitude: 21.2,
      longitude: 90.2,
      region: "MAR_BOB",
      units: "hPa",
      ensemble_members: generateEnsemble(21.2, 90.2, 1.1, 6, 996.0),
    },
  ],
};

// 4. Preset: Insufficient Telemetry Fail-Safe (< 5 members - DATA INSUFFICIENT)
export const PRESET_INSUFFICIENT_TELEMETRY: MultiLeadForecastInput = {
  forecast_source: "NCMRWF TIGGE",
  model: "NCMRWF_NEPS",
  forecast_cycle: "2023-11-15T00:00:00Z",
  variable: "Mean Sea Level Pressure (msl)",
  units: "hPa",
  region: "MAR_BOB",
  leads: [
    {
      forecast_source: "NCMRWF TIGGE",
      model: "NCMRWF_NEPS",
      forecast_cycle: "2023-11-15T00:00:00Z",
      lead_hours: 24,
      valid_time: "2023-11-16T00:00:00Z",
      latitude: 14.5,
      longitude: 87.0,
      region: "MAR_BOB",
      units: "hPa",
      ensemble_members: generateEnsemble(14.5, 87.0, 0.4, 3, 998.0),
    },
  ],
};

export const TIMELINE_PRESETS = [
  { id: "midhili_d1_d5", name: "Cyclone Midhili (D+1 to D+5)", data: PRESET_MIDHILI_MULTI_LEAD },
  { id: "extended_10day", name: "10-Day Medium-Range (D+1 to D+10 Full)", data: PRESET_10DAY_EXTENDED },
  { id: "degraded_coverage", name: "Degraded Coverage (6 members, D+1..D+3)", data: PRESET_DEGRADED_ENSEMBLE },
  { id: "insufficient_failsafe", name: "Insufficient Data Fail-Safe (3 members)", data: PRESET_INSUFFICIENT_TELEMETRY },
];
