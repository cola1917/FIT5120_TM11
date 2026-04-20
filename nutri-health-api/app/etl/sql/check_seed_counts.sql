-- Seed verification script for CN catalog tables.
-- Run with:
-- docker compose exec -T db psql -U nutrihealth -d nutrihealth -f - < app/etl/sql/check_seed_counts.sql

WITH expected AS (
    SELECT *
    FROM (VALUES
        ('daily_healthy_challenge'::text, 16::bigint),
        ('cn_ctgnme'::text, 25::bigint),
        ('cn_gpcnme'::text, 131::bigint),
        ('cn_nutdes'::text, 19::bigint),
        ('cn_fdes'::text, 9202::bigint),
        ('cn_nutval'::text, 174838::bigint),
        ('cn_wght'::text, 15271::bigint),
        ('cn_food_tags'::text, 15258::bigint),
        ('remote_alternative'::text, 13017::bigint)
    ) AS t(table_name, expected_rows)
),
actual AS (
    SELECT 'daily_healthy_challenge'::text AS table_name, COUNT(*)::bigint AS actual_rows FROM daily_healthy_challenge
    UNION ALL
    SELECT 'cn_ctgnme'::text AS table_name, COUNT(*)::bigint AS actual_rows FROM cn_ctgnme
    UNION ALL SELECT 'cn_gpcnme', COUNT(*)::bigint FROM cn_gpcnme
    UNION ALL SELECT 'cn_nutdes', COUNT(*)::bigint FROM cn_nutdes
    UNION ALL SELECT 'cn_fdes', COUNT(*)::bigint FROM cn_fdes
    UNION ALL SELECT 'cn_nutval', COUNT(*)::bigint FROM cn_nutval
    UNION ALL SELECT 'cn_wght', COUNT(*)::bigint FROM cn_wght
    UNION ALL SELECT 'cn_food_tags', COUNT(*)::bigint FROM cn_food_tags
    UNION ALL SELECT 'remote_alternative', COUNT(*)::bigint FROM remote_alternative
)
SELECT
    e.table_name,
    e.expected_rows,
    a.actual_rows,
    (a.actual_rows - e.expected_rows) AS diff_rows,
    CASE WHEN a.actual_rows = e.expected_rows THEN 'OK' ELSE 'MISMATCH' END AS status
FROM expected e
LEFT JOIN actual a USING (table_name)
ORDER BY e.table_name;

-- Key integrity checks.
SELECT 'cn_fdes null cn_code' AS check_name, COUNT(*) AS issue_count
FROM cn_fdes
WHERE cn_code IS NULL
UNION ALL
SELECT 'cn_fdes duplicate non-null gtin', COUNT(*)
FROM (
    SELECT gtin
    FROM cn_fdes
    WHERE gtin IS NOT NULL AND gtin <> ''
    GROUP BY gtin
    HAVING COUNT(*) > 1
) dup
UNION ALL
SELECT 'cn_nutval missing parent cn_fdes', COUNT(*)
FROM cn_nutval n
LEFT JOIN cn_fdes f ON f.cn_code = n.cn_code
WHERE f.cn_code IS NULL
UNION ALL
SELECT 'cn_wght missing parent cn_fdes', COUNT(*)
FROM cn_wght w
LEFT JOIN cn_fdes f ON f.cn_code = w.cn_code
WHERE f.cn_code IS NULL
UNION ALL
SELECT 'cn_food_tags missing parent cn_fdes', COUNT(*)
FROM cn_food_tags t
LEFT JOIN cn_fdes f ON f.cn_code = t.cn_code
WHERE f.cn_code IS NULL
UNION ALL
SELECT 'remote_alternative broken original_cn_code', COUNT(*)
FROM remote_alternative r
LEFT JOIN cn_fdes f ON f.cn_code = r.original_cn_code
WHERE f.cn_code IS NULL
UNION ALL
SELECT 'remote_alternative broken suggested_cn_code', COUNT(*)
FROM remote_alternative r
LEFT JOIN cn_fdes f ON f.cn_code = r.suggested_cn_code
WHERE f.cn_code IS NULL;
