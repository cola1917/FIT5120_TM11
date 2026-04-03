-- Query Nutrition Information for a Specific Food (cn_code = 1001)
-- This query retrieves all nutrients for a food item with complete details

SELECT 
    f.cn_code,
    f.descriptor AS food_name,
    f.brand_name,
    nd.nutrient_code,
    nd.nutrient_description AS nutrient_name,
    nd.nutrient_unit,
    nv.nutrient_value,
    nv.source_code,
    CASE 
        WHEN nv.source_code = 1 THEN 'Analyzed'
        WHEN nv.source_code = 3 THEN 'Calculated'
        ELSE 'Unknown'
    END AS source_type,
    nv.value_type_code,
    nv.per_unit
FROM cn_nutval nv
JOIN cn_nutdes nd ON nv.nutrient_code = nd.nutrient_code
JOIN cn_fdes f ON nv.cn_code = f.cn_code
WHERE nv.cn_code = 1001
ORDER BY nd.nutrient_code;


-- Alternative: Simple Query (just nutrition values without joins)
-- SELECT 
--     cn_code,
--     nutrient_code,
--     nutrient_value,
--     source_code,
--     value_type_code,
--     per_unit
-- FROM cn_nutval
-- WHERE cn_code = 1001
-- ORDER BY nutrient_code;


-- Query with aggregation: Get average nutrient value (if multiple records)
-- SELECT 
--     f.cn_code,
--     f.descriptor AS food_name,
--     nd.nutrient_code,
--     nd.nutrient_description AS nutrient_name,
--     ROUND(AVG(nv.nutrient_value)::numeric, 2) AS average_nutrient_value,
--     nd.nutrient_unit
-- FROM cn_nutval nv
-- JOIN cn_nutdes nd ON nv.nutrient_code = nd.nutrient_code
-- JOIN cn_fdes f ON nv.cn_code = f.cn_code
-- WHERE nv.cn_code = 1001
-- GROUP BY f.cn_code, f.descriptor, nd.nutrient_code, nd.nutrient_description, nd.nutrient_unit
-- ORDER BY nd.nutrient_code;


-- Query with all food details: comprehensive view
-- SELECT 
--     f.cn_code,
--     f.gtin,
--     f.descriptor AS food_name,
--     f.brand_name,
--     f.brand_owner_name,
--     f.form_of_food,
--     f.health_grade,
--     f.hcl_compliant,
--     f.is_halal_auto,
--     nd.nutrient_code,
--     nd.nutrient_description AS nutrient_name,
--     nd.nutrient_unit,
--     nv.nutrient_value,
--     nv.source_code
-- FROM cn_fdes f
-- LEFT JOIN cn_nutval nv ON f.cn_code = nv.cn_code
-- LEFT JOIN cn_nutdes nd ON nv.nutrient_code = nd.nutrient_code
-- WHERE f.cn_code = 1001
-- ORDER BY nd.nutrient_code;
