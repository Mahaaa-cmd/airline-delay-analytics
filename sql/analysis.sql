-- Grain: one month x carrier x arrival airport. Never average row rates.
SELECT year, month, SUM(arr_flights) AS reported_flights,
       100.0 * SUM(arr_del15) / NULLIF(SUM(arr_flights), 0) AS late_arrival_pct,
       100.0 * SUM(arr_cancelled) / NULLIF(SUM(arr_flights), 0) AS cancellation_pct
FROM delays GROUP BY year, month ORDER BY year, month;

SELECT carrier, SUM(arr_flights) AS reported_flights,
       100.0 * SUM(arr_del15) / NULLIF(SUM(arr_flights), 0) AS late_arrival_pct
FROM delays GROUP BY carrier HAVING SUM(arr_flights) >= 10000
ORDER BY late_arrival_pct DESC;

SELECT carrier, airport, SUM(arr_flights) AS reported_flights,
       SUM(arr_del15) AS delayed_arrivals,
       100.0 * SUM(arr_del15) / NULLIF(SUM(arr_flights), 0) AS late_arrival_pct
FROM delays WHERE year = 2025
GROUP BY carrier, airport HAVING SUM(arr_flights) >= 10000
ORDER BY delayed_arrivals DESC LIMIT 20;
