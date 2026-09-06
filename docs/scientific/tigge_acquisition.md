# NCMRWF/TIGGE ECDS acquisition

ForecastGuard requests NCMRWF TIGGE perturbed forecasts through the official
`cdsapi` client and the `tigge-forecasts` ECDS dataset. Archive availability is
determined by ECDS; creating a request does not imply a forecast exists.

Configure credentials outside source control:

```text
ECDS_API_URL=<authorized ECDS API endpoint>
ECDS_API_KEY=<personal access token>
```

The standard `CDSAPI_URL` and `CDSAPI_KEY` names are accepted as fallbacks.
Accept the relevant dataset terms in the authorized ECDS account before a live
request can succeed.

Start with a dry run; it needs neither credentials nor network access:

```powershell
python -m scientific.ingestion.tigge --dry-run `
  --date 2025-09-01 --cycle 0 --lead 24 --variable tp `
  --members 1,2,3 --area 20,70,10,90
```

The request uses `origin=dems`, perturbed type `pf`, and exact requested
initialization, lead, members, and north/west/south/east area. Successful
retrieval writes a `<output>.request.json` sidecar with the request and
retrieval timestamp. An existing output is skipped only if its sidecar proves
it was created from the identical request; otherwise it is never overwritten.

Acquisition does not alter returned GRIB precipitation accumulation semantics.
Inspect returned metadata with the existing GRIB ingestion pipeline before any
forecast-observation pairing.
