# Data dictionary, provenance and availability

Publisher: US Department of Transportation, Bureau of Transportation Statistics (BTS). Dataset: *Airline On-Time Statistics and Delay Causes*. Official page: https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp. Retrieved 3 November 2026 for January 2018–December 2025, all carriers and airports returned by the source.

Original CSV: `Airline_Delay_Cause.csv`. The unchanged original download archive is preserved as `bts_delay_causes_2018_2025.zip`; its exact server-provided filename, contained filenames, bytes, URL, date and SHA-256 hashes are in `raw/provenance.json`. The server's filename timestamp may use a different timezone from the local retrieval date. No immutable release/version ID was supplied. The ZIP also preserves BTS's original column-definition workbook. The CSV has 186,371 rows and 21 columns before cleaning.

Grain: **year-month × carrier × arrival airport**. No external joins are used. Internally, derived historical feature tables join on carrier, airport and exact shifted calendar month, with one-to-one validation.

| Original field | Type loaded | Meaning / unit | Available before target month? |
|---|---|---|---|
| year | Integer | Calendar year | Yes |
| month | Integer | Calendar month, 1–12 | Yes |
| carrier | String | Reporting carrier code | Entity identity; not directly modelled |
| carrier_name | String | Source carrier label; may change over time | Label; not modelled |
| airport | String | Arrival airport code | Entity identity; not directly modelled |
| airport_name | String | Airport label; may change over time | Label; not modelled |
| arr_flights | Float | Reported arriving/scheduled flight count in source scope | No, realized monthly count |
| arr_del15 | Float | Count of arrivals delayed at least 15 minutes | No, target numerator |
| carrier_ct | Float | Fractional delayed-flight attribution to air carrier | No |
| weather_ct | Float | Fractional delayed-flight attribution to extreme weather | No |
| nas_ct | Float | Fractional delayed-flight attribution to NAS | No |
| security_ct | Float | Fractional delayed-flight attribution to security | No |
| late_aircraft_ct | Float | Fractional delayed-flight attribution to late aircraft | No |
| arr_cancelled | Float | Cancellation count | No |
| arr_diverted | Float | Diversion count | No |
| arr_delay | Float | Total delay minutes for delayed arrivals | No |
| carrier_delay | Float | Air-carrier-attributed delay minutes | No |
| weather_delay | Float | Extreme-weather-attributed delay minutes | No |
| nas_delay | Float | NAS-attributed delay minutes | No |
| security_delay | Float | Security-attributed delay minutes | No |
| late_aircraft_delay | Float | Late-aircraft-attributed delay minutes | No |

Counts are kept as floating point to preserve source values and missingness. Fractional cause counts reflect prorated attribution, not fractional physical aircraft. Monthly volume is not a pre-decision feature. Current-month outcomes are used for descriptive analysis and evaluation only.

## Derived fields

| Field | Definition |
|---|---|
| date | First day of observation month; represents a monthly period, not a flight date |
| on_time | arr_flights − arr_del15 − arr_cancelled − arr_diverted |
| delay_rate | arr_del15 / arr_flights, fraction 0–1 |
| cancel_rate | arr_cancelled / arr_flights, fraction 0–1 |
| delay_burden | arr_delay / arr_flights, minutes per reported flight |
| cause_minutes_gap | arr_delay − sum of five cause-minute columns |
| month_sin, month_cos | Circular calendar-month encoding with period 12 |
| log_volume | log(1 + arr_flights), used only to construct historical volume |
| lag3_delay_rate, lag12_delay_rate | Same carrier-airport rate exactly 3 or 12 months earlier |
| lag3_cancel_rate | Cancellation share exactly 3 months earlier |
| lag3_delay_burden | Delay minutes per reported flight exactly 3 months earlier |
| lag3_log_volume | log(1 + flight volume) exactly 3 months earlier |

No satisfaction labels, passenger information, route origins, departure schedules, aircraft IDs, weather measurements or ticket revenues are present. Do not manufacture them or combine unrelated datasets to imply they were observed.

## Source conditions

The source makes its statistical raw data publicly downloadable. The download contains no dataset-specific license identifier or separate license text; this project does not invent one or apply the code license to the data. Preserve BTS attribution and source links, review applicable source terms for subsequent reuse, and do not imply BTS endorses this analysis. Original public statistical facts and project code have distinct provenance. No personal records or credentials are included.

Definitions: https://www.bts.gov/explore-topics-and-geography/topics/airline-time-performance-and-causes-flight-delays. BTS includes some non-extreme weather in NAS attribution; the weather field is not total weather impact. Source scope includes the reporting arrangements described on the official page from January 2018 onward. These aggregates cannot independently verify flight-level deduplication.
