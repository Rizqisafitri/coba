-- Step 2: Operationalize the Logic in SQL (STRICTLY FOLLOW REQUIREMENT)
-- Create talent_benchmarks table if not exists
CREATE TABLE IF NOT EXISTS talent_benchmarks (
    job_vacancy_id TEXT PRIMARY KEY,
    role_name TEXT,
    job_level TEXT,
    role_purpose TEXT,
    selected_talent_ids TEXT[],
    weights_config JSONB
);

-- Insert sample data
INSERT INTO talent_benchmarks (job_vacancy_id, role_name, job_level, role_purpose, selected_talent_ids, weights_config)
VALUES 
    ('VAC001', 'Data Analyst', 'III', 'Analyze data for insights', ARRAY['EMP001', 'EMP002'], 
    '{"TGV": {"Cognitive Complexity & Problem-Solving": 0.4, "Leadership & Influence": 0.3}, 
      "TV": {"IQ: Overall IQ Score": 0.6, "GTQ: Overall GTQ Score": 0.4}}'::JSONB)
ON CONFLICT (job_vacancy_id) DO NOTHING;
-- TV-TGV Mapping Table dengan scoring direction
DROP TABLE IF EXISTS tgv_tv_mapping;
CREATE TEMPORARY TABLE tgv_tv_mapping (
    tv_name TEXT,
    tgv_name TEXT,
    scoring_direction TEXT DEFAULT 'higher' -- 'higher' or 'lower'
);

INSERT INTO tgv_tv_mapping VALUES
    ('DISC: Steadiness', 'Adaptability & Stress Tolerance', 'higher'),
    ('PAPI Kostick: Papi_T', 'Adaptability & Stress Tolerance', 'lower'),
    ('PAPI Kostick: Papi_E', 'Adaptability & Stress Tolerance', 'lower'),
    ('CliftonStrengths: Adaptability', 'Adaptability & Stress Tolerance', 'higher'),
    ('GTQ: Overall GTQ Score', 'Cognitive Complexity & Problem-Solving', 'higher'),
    ('TIKI: Overall TIKI Score', 'Cognitive Complexity & Problem-Solving', 'higher'),
    ('IQ: Overall IQ Score', 'Cognitive Complexity & Problem-Solving', 'higher'),
    ('PAPI Kostick: Papi_I', 'Cognitive Complexity & Problem-Solving', 'higher'),
    ('CliftonStrengths: Connectedness', 'Cognitive Complexity & Problem-Solving', 'higher'),
    ('CliftonStrengths: Analytical', 'Cognitive Complexity & Problem-Solving', 'higher'),
    ('CliftonStrengths: Strategic', 'Cognitive Complexity & Problem-Solving', 'higher'),
    ('DISC: Compliance', 'Conscientiousness & Reliability', 'higher'),
    ('PAPI Kostick: Papi_C', 'Conscientiousness & Reliability', 'higher'),
    ('PAPI Kostick: Papi_D', 'Conscientiousness & Reliability', 'higher'),
    ('CliftonStrengths: Deliberative', 'Conscientiousness & Reliability', 'higher'),
    ('CliftonStrengths: Discipline', 'Conscientiousness & Reliability', 'higher'),
    ('MBTI: Intuition', 'Creativity & Innovation Orientation', 'higher'),
    ('PAPI Kostick: Papi_Z', 'Creativity & Innovation Orientation', 'higher'),
    ('CliftonStrengths: Futuristic', 'Creativity & Innovation Orientation', 'higher'),
    ('CliftonStrengths: Ideation', 'Creativity & Innovation Orientation', 'higher'),
    ('CliftonStrengths: Belief', 'Cultural & Values Urgency', 'higher'),
    ('MBTI: Extraversion', 'Leadership & Influence', 'higher'),
    ('MBTI: Introversion', 'Leadership & Influence', 'lower'),
    ('DISC: Dominance', 'Leadership & Influence', 'higher'),
    ('PAPI Kostick: Papi_L', 'Leadership & Influence', 'higher'),
    ('PAPI Kostick: Papi_P', 'Leadership & Influence', 'higher'),
    ('CliftonStrengths: Arranger', 'Leadership & Influence', 'higher'),
    ('CliftonStrengths: Command', 'Leadership & Influence', 'higher'),
    ('CliftonStrengths: Self-Assurance', 'Leadership & Influence', 'higher'),
    ('CliftonStrengths: Developer', 'Leadership & Influence', 'higher'),
    ('Pauli: Initial Performance', 'Motivation & Drive', 'higher'),
    ('PAPI Kostick: Papi_A', 'Motivation & Drive', 'higher'),
    ('CliftonStrengths: Achiever', 'Motivation & Drive', 'higher'),
    ('DISC: Influence', 'Social Orientation & Collaboration', 'higher'),
    ('PAPI Kostick: Papi_S', 'Social Orientation & Collaboration', 'higher'),
    ('CliftonStrengths: Communication', 'Social Orientation & Collaboration', 'higher'),
    ('CliftonStrengths: Woo', 'Social Orientation & Collaboration', 'higher'),
    ('CliftonStrengths: Relator', 'Social Orientation & Collaboration', 'higher');

-- Main query dengan calculation STRICTLY sesuai requirement
WITH 
-- CTE 0: Unnest selected_talent_ids
selected_talents AS (
    SELECT 
        tb.job_vacancy_id,
        unnest(tb.selected_talent_ids) AS employee_id
    FROM talent_benchmarks tb
),

-- CTE 1: Get scores for selected talents (benchmark employees)
selected_talent_scores AS (
    SELECT 
        st.job_vacancy_id,
        st.employee_id,
        tm.tv_name,
        tm.tgv_name,
        tm.scoring_direction,
        -- Calculate actual scores for benchmark talents
        CASE 
            -- DISC variables (binary: 100 if present, 0 if not)
            WHEN tm.tv_name = 'DISC: Steadiness' THEN 
                CASE WHEN pp.disc LIKE '%S%' THEN 100.0 ELSE 0.0 END
            WHEN tm.tv_name = 'DISC: Compliance' THEN 
                CASE WHEN pp.disc LIKE '%C%' THEN 100.0 ELSE 0.0 END
            WHEN tm.tv_name = 'DISC: Dominance' THEN 
                CASE WHEN pp.disc LIKE '%D%' THEN 100.0 ELSE 0.0 END
            WHEN tm.tv_name = 'DISC: Influence' THEN 
                CASE WHEN pp.disc LIKE '%I%' THEN 100.0 ELSE 0.0 END
            
            -- PAPI Kostick variables (scale: 0-10, convert to 0-100)
            WHEN tm.tv_name LIKE 'PAPI Kostick: Papi_%' THEN 
                COALESCE((SELECT score * 10 FROM papi_scores WHERE employee_id = st.employee_id AND scale_code = REPLACE(tm.tv_name, 'PAPI Kostick: ', '')), 50.0)
            
            -- Cognitive tests 
            WHEN tm.tv_name = 'IQ: Overall IQ Score' THEN 
                CASE WHEN pp.iq IS NOT NULL THEN GREATEST(0, LEAST(100, (pp.iq - 70) * 100 / 60)) ELSE 50.0 END
            WHEN tm.tv_name = 'GTQ: Overall GTQ Score' THEN 
                CASE WHEN pp.gtq IS NOT NULL THEN pp.gtq::NUMERIC * 10 ELSE 50.0 END
            WHEN tm.tv_name = 'TIKI: Overall TIKI Score' THEN 
                CASE WHEN pp.tiki IS NOT NULL THEN pp.tiki::NUMERIC * 10 ELSE 50.0 END
            WHEN tm.tv_name = 'Pauli: Initial Performance' THEN 
                CASE WHEN pp.pauli IS NOT NULL THEN GREATEST(0, LEAST(100, pp.pauli)) ELSE 50.0 END
            
            -- MBTI variables (binary: 100 if trait present, 0 if not)
            WHEN tm.tv_name = 'MBTI: Intuition' THEN 
                CASE WHEN pp.mbti LIKE '%N%' THEN 100.0 ELSE 0.0 END
            WHEN tm.tv_name = 'MBTI: Extraversion' THEN 
                CASE WHEN pp.mbti LIKE 'E%' THEN 100.0 ELSE 0.0 END
            WHEN tm.tv_name = 'MBTI: Introversion' THEN 
                CASE WHEN pp.mbti LIKE 'I%' THEN 100.0 ELSE 0.0 END
            
            -- CliftonStrengths variables (binary: 100 if in top 5, 0 if not)
            WHEN tm.tv_name LIKE 'CliftonStrengths:%' THEN 
                CASE WHEN EXISTS (
                    SELECT 1 FROM strengths s 
                    WHERE s.employee_id = st.employee_id 
                    AND s.theme = REPLACE(tm.tv_name, 'CliftonStrengths: ', '')
                    AND s.rank <= 5
                ) THEN 100.0 ELSE 0.0 END
                
            ELSE 50.0
        END AS score
    FROM selected_talents st
    JOIN tgv_tv_mapping tm ON true
    LEFT JOIN profiles_psych pp ON st.employee_id = pp.employee_id
    WHERE st.employee_id IS NOT NULL
),

-- CTE 2: Baseline Aggregation (median of selected talent scores)
baseline_agg AS (
    SELECT 
        job_vacancy_id,
        tv_name,
        tgv_name,
        scoring_direction,
        -- Use median as required
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score) AS baseline_score,
        COUNT(*) AS sample_size
    FROM selected_talent_scores
    WHERE score IS NOT NULL
    GROUP BY job_vacancy_id, tv_name, tgv_name, scoring_direction
    HAVING COUNT(*) >= 1
),

-- CTE 3: TV Match Rate - STRICTLY FOLLOW REQUIREMENT
tv_match AS (
    SELECT 
        e.employee_id,
        e.directorate_id,
        e.position_id,
        e.grade_id,
        ba.job_vacancy_id,
        ba.tgv_name,
        ba.tv_name,
        ba.scoring_direction,
        ba.baseline_score,
        
        -- User score calculation (for all employees being evaluated)
        CASE 
            WHEN ba.tv_name = 'DISC: Steadiness' THEN 
                CASE WHEN pp.disc LIKE '%S%' THEN 100.0 ELSE 0.0 END
            WHEN ba.tv_name = 'DISC: Compliance' THEN 
                CASE WHEN pp.disc LIKE '%C%' THEN 100.0 ELSE 0.0 END
            WHEN ba.tv_name = 'DISC: Dominance' THEN 
                CASE WHEN pp.disc LIKE '%D%' THEN 100.0 ELSE 0.0 END
            WHEN ba.tv_name = 'DISC: Influence' THEN 
                CASE WHEN pp.disc LIKE '%I%' THEN 100.0 ELSE 0.0 END
            WHEN ba.tv_name LIKE 'PAPI Kostick: Papi_%' THEN 
                COALESCE((SELECT score * 10 FROM papi_scores WHERE employee_id = e.employee_id AND scale_code = REPLACE(ba.tv_name, 'PAPI Kostick: ', '')), 50.0)
            WHEN ba.tv_name = 'IQ: Overall IQ Score' THEN 
                CASE WHEN pp.iq IS NOT NULL THEN GREATEST(0, LEAST(100, (pp.iq - 70) * 100 / 60)) ELSE 50.0 END
            WHEN ba.tv_name = 'GTQ: Overall GTQ Score' THEN 
                CASE WHEN pp.gtq IS NOT NULL THEN pp.gtq::NUMERIC * 10 ELSE 50.0 END
            WHEN ba.tv_name = 'TIKI: Overall TIKI Score' THEN 
                CASE WHEN pp.tiki IS NOT NULL THEN pp.tiki::NUMERIC * 10 ELSE 50.0 END
            WHEN ba.tv_name = 'Pauli: Initial Performance' THEN 
                CASE WHEN pp.pauli IS NOT NULL THEN GREATEST(0, LEAST(100, pp.pauli)) ELSE 50.0 END
            WHEN ba.tv_name = 'MBTI: Intuition' THEN 
                CASE WHEN pp.mbti LIKE '%N%' THEN 100.0 ELSE 0.0 END
            WHEN ba.tv_name = 'MBTI: Extraversion' THEN 
                CASE WHEN pp.mbti LIKE 'E%' THEN 100.0 ELSE 0.0 END
            WHEN ba.tv_name = 'MBTI: Introversion' THEN 
                CASE WHEN pp.mbti LIKE 'I%' THEN 100.0 ELSE 0.0 END
            WHEN ba.tv_name LIKE 'CliftonStrengths:%' THEN 
                CASE WHEN EXISTS (
                    SELECT 1 FROM strengths s 
                    WHERE s.employee_id = e.employee_id 
                    AND s.theme = REPLACE(ba.tv_name, 'CliftonStrengths: ', '')
                    AND s.rank <= 5
                ) THEN 100.0 ELSE 0.0 END
            ELSE 50.0
        END AS user_score,
        
        -- ✅ STRICTLY FOLLOW REQUIREMENT: TV Match Rate Calculation
        CASE 
            -- For non-numeric/categorical variables: exact match = 100%, no match = 0%
            WHEN ba.tv_name LIKE 'DISC:%' OR ba.tv_name LIKE 'MBTI:%' OR ba.tv_name LIKE 'CliftonStrengths:%' THEN
                CASE 
                    -- Exact match logic
                    WHEN (ba.tv_name = 'DISC: Steadiness' AND pp.disc LIKE '%S%') OR
                         (ba.tv_name = 'DISC: Compliance' AND pp.disc LIKE '%C%') OR
                         (ba.tv_name = 'DISC: Dominance' AND pp.disc LIKE '%D%') OR
                         (ba.tv_name = 'DISC: Influence' AND pp.disc LIKE '%I%') OR
                         (ba.tv_name = 'MBTI: Intuition' AND pp.mbti LIKE '%N%') OR
                         (ba.tv_name = 'MBTI: Extraversion' AND pp.mbti LIKE 'E%') OR
                         (ba.tv_name = 'MBTI: Introversion' AND pp.mbti LIKE 'I%') OR
                         (ba.tv_name LIKE 'CliftonStrengths:%' AND EXISTS (
                            SELECT 1 FROM strengths s 
                            WHERE s.employee_id = e.employee_id 
                            AND s.theme = REPLACE(ba.tv_name, 'CliftonStrengths: ', '')
                            AND s.rank <= 5
                         ))
                    THEN 100.0
                    ELSE 0.0
                END
            
            -- For numeric variables: direct ratio comparison
            WHEN ba.baseline_score > 0 THEN
                CASE 
                    -- If scoring direction is "lower is better", invert the ratio
                    WHEN ba.scoring_direction = 'lower' THEN
                        GREATEST(0, LEAST(100, 
                            ((2 * ba.baseline_score - 
                                CASE 
                                    WHEN ba.tv_name LIKE 'PAPI Kostick: Papi_%' THEN 
                                        COALESCE((SELECT score * 10 FROM papi_scores WHERE employee_id = e.employee_id AND scale_code = REPLACE(ba.tv_name, 'PAPI Kostick: ', '')), 50.0)
                                    WHEN ba.tv_name = 'IQ: Overall IQ Score' THEN 
                                        CASE WHEN pp.iq IS NOT NULL THEN GREATEST(0, LEAST(100, (pp.iq - 70) * 100 / 60)) ELSE 50.0 END
                                    WHEN ba.tv_name = 'GTQ: Overall GTQ Score' THEN 
                                        CASE WHEN pp.gtq IS NOT NULL THEN pp.gtq::NUMERIC * 10 ELSE 50.0 END
                                    WHEN ba.tv_name = 'TIKI: Overall TIKI Score' THEN 
                                        CASE WHEN pp.tiki IS NOT NULL THEN pp.tiki::NUMERIC * 10 ELSE 50.0 END
                                    WHEN ba.tv_name = 'Pauli: Initial Performance' THEN 
                                        CASE WHEN pp.pauli IS NOT NULL THEN GREATEST(0, LEAST(100, pp.pauli)) ELSE 50.0 END
                                    ELSE 50.0
                                END
                            ) / ba.baseline_score) * 100
                        ))
                    -- Else normal ratio (higher is better)
                    ELSE
                        GREATEST(0, LEAST(100, 
                            (
                                CASE 
                                    WHEN ba.tv_name LIKE 'PAPI Kostick: Papi_%' THEN 
                                        COALESCE((SELECT score * 10 FROM papi_scores WHERE employee_id = e.employee_id AND scale_code = REPLACE(ba.tv_name, 'PAPI Kostick: ', '')), 50.0)
                                    WHEN ba.tv_name = 'IQ: Overall IQ Score' THEN 
                                        CASE WHEN pp.iq IS NOT NULL THEN GREATEST(0, LEAST(100, (pp.iq - 70) * 100 / 60)) ELSE 50.0 END
                                    WHEN ba.tv_name = 'GTQ: Overall GTQ Score' THEN 
                                        CASE WHEN pp.gtq IS NOT NULL THEN pp.gtq::NUMERIC * 10 ELSE 50.0 END
                                    WHEN ba.tv_name = 'TIKI: Overall TIKI Score' THEN 
                                        CASE WHEN pp.tiki IS NOT NULL THEN pp.tiki::NUMERIC * 10 ELSE 50.0 END
                                    WHEN ba.tv_name = 'Pauli: Initial Performance' THEN 
                                        CASE WHEN pp.pauli IS NOT NULL THEN GREATEST(0, LEAST(100, pp.pauli)) ELSE 50.0 END
                                    ELSE 50.0
                                END / ba.baseline_score
                            ) * 100
                        ))
                END
            
            -- Fallback for zero baseline (shouldn't happen with proper data)
            ELSE 0.0
        END AS tv_match_rate
    FROM employees e
    INNER JOIN profiles_psych pp ON e.employee_id = pp.employee_id
    CROSS JOIN baseline_agg ba
    WHERE ba.baseline_score IS NOT NULL
),

-- CTE 4: TGV Match Rate - Average TV match rates with custom weights
tgv_match AS (
    SELECT 
        tm.employee_id,
        tm.directorate_id,
        tm.position_id,
        tm.grade_id,
        tm.job_vacancy_id,
        tm.tgv_name,
        -- Apply equal or custom TV weights if provided
        CASE 
            WHEN SUM(COALESCE((tb.weights_config->'TV'->>tm.tv_name)::NUMERIC, 1.0)) > 0 THEN
                SUM(COALESCE((tb.weights_config->'TV'->>tm.tv_name)::NUMERIC, 1.0) * tm.tv_match_rate) / 
                SUM(COALESCE((tb.weights_config->'TV'->>tm.tv_name)::NUMERIC, 1.0))
            ELSE
                AVG(tm.tv_match_rate)  -- Equal weights fallback
        END AS tgv_match_rate
    FROM tv_match tm
    JOIN talent_benchmarks tb ON tm.job_vacancy_id = tb.job_vacancy_id
    WHERE tm.tv_match_rate IS NOT NULL
    GROUP BY tm.employee_id, tm.directorate_id, tm.position_id, tm.grade_id, tm.job_vacancy_id, tm.tgv_name
),

-- CTE 5: Final Match Rate - Weighted average across all TGVs
final_match AS (
    SELECT 
        tm.employee_id,
        tm.directorate_id,
        tm.position_id,
        tm.grade_id,
        tm.job_vacancy_id,
        -- Apply equal or custom TGV weights from weights_config
        CASE 
            WHEN SUM(COALESCE((tb.weights_config->'TGV'->>tm.tgv_name)::NUMERIC, 1.0)) > 0 THEN
                SUM(COALESCE((tb.weights_config->'TGV'->>tm.tgv_name)::NUMERIC, 1.0) * tm.tgv_match_rate) / 
                SUM(COALESCE((tb.weights_config->'TGV'->>tm.tgv_name)::NUMERIC, 1.0))
            ELSE
                AVG(tm.tgv_match_rate)  -- Equal weights fallback
        END AS final_match_rate
    FROM tgv_match tm
    JOIN talent_benchmarks tb ON tm.job_vacancy_id = tb.job_vacancy_id
    GROUP BY tm.employee_id, tm.directorate_id, tm.position_id, tm.grade_id, tm.job_vacancy_id
)

-- Final output
SELECT 
    fm.employee_id,
    dir.name as directorate,
    pos.name as role,
    grd.name as grade,
    tm.tgv_name,
    tv_m.tv_name,
    ROUND(tv_m.baseline_score::numeric, 2) as baseline_score,
    ROUND(tv_m.user_score::numeric, 2) as user_score,
    ROUND(tv_m.tv_match_rate::numeric, 2) as tv_match_rate,
    ROUND(tm.tgv_match_rate::numeric, 2) as tgv_match_rate,
    ROUND(fm.final_match_rate::numeric, 2) as final_match_rate
FROM final_match fm
JOIN employees e ON fm.employee_id = e.employee_id
JOIN talent_benchmarks tb ON fm.job_vacancy_id = tb.job_vacancy_id
LEFT JOIN tgv_match tm ON fm.employee_id = tm.employee_id AND fm.job_vacancy_id = tm.job_vacancy_id
LEFT JOIN tv_match tv_m ON tm.employee_id = tv_m.employee_id AND tm.job_vacancy_id = tv_m.job_vacancy_id AND tm.tgv_name = tv_m.tgv_name
LEFT JOIN dim_directorates dir ON fm.directorate_id = dir.directorate_id
LEFT JOIN dim_positions pos ON fm.position_id = pos.position_id
LEFT JOIN dim_grades grd ON fm.grade_id = grd.grade_id
WHERE fm.final_match_rate IS NOT NULL
ORDER BY 
    fm.job_vacancy_id, 
    fm.final_match_rate DESC, 
    fm.employee_id, 
    tm.tgv_name,
    tv_m.tv_name;