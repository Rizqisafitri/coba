import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import uuid
from plotly.subplots import make_subplots
import numpy as np

# Initialize session state
if 'role_info_generated' not in st.session_state:
    st.session_state.role_info_generated = False
if 'job_details_generated' not in st.session_state:
    st.session_state.job_details_generated = False
if 'ai_job_profile' not in st.session_state:
    st.session_state.ai_job_profile = None
if 'ranked_talent' not in st.session_state:
    st.session_state.ranked_talent = None
if 'job_details' not in st.session_state:
    st.session_state.job_details = {
        'responsibilities': [""],
        'work_inputs': [""],
        'work_outputs': [""], 
        'qualifications': [""],
        'competencies': [""]
    }

# DB Connection
try:
    conn = psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"]
    )
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# Helper functions
def get_employee_options():
    try:
        query = """
        SELECT e.employee_id, e.fullname, p.name as position
        FROM employees e
        LEFT JOIN dim_positions p ON e.position_id = p.position_id
        WHERE e.fullname IS NOT NULL
        """
        df = pd.read_sql(query, conn)
        return [f"{row['fullname']} - {row['position']} ({row['employee_id']})" for _, row in df.iterrows()]
    except Exception as e:
        st.error(f"Error loading employees: {e}")
        return []

def extract_employee_ids(selections):
    return [sel.split('(')[-1].strip(')') for sel in selections]

# TGV Baseline Computation dengan mapping yang dikoreksi
def compute_tgv_baselines(benchmark_ids):
    """Compute TGV baselines menggunakan mapping 8 TGV dan 38 TV yang dikoreksi"""
    if not benchmark_ids:
        return {}
    
    query = """
    WITH employee_data AS (
        SELECT 
            e.employee_id,
            pp.disc,
            pp.mbti,
            pp.gtq,
            pp.tiki,
            pp.iq,
            pp.pauli,
            -- Get PAPI scores as key-value pairs
            MAX(CASE WHEN ps.scale_code = 'Papi_T' THEN ps.score::numeric ELSE NULL END) as papi_t,
            MAX(CASE WHEN ps.scale_code = 'Papi_E' THEN ps.score::numeric ELSE NULL END) as papi_e,
            MAX(CASE WHEN ps.scale_code = 'Papi_I' THEN ps.score::numeric ELSE NULL END) as papi_i,
            MAX(CASE WHEN ps.scale_code = 'Papi_C' THEN ps.score::numeric ELSE NULL END) as papi_c,
            MAX(CASE WHEN ps.scale_code = 'Papi_D' THEN ps.score::numeric ELSE NULL END) as papi_d,
            MAX(CASE WHEN ps.scale_code = 'Papi_Z' THEN ps.score::numeric ELSE NULL END) as papi_z,
            MAX(CASE WHEN ps.scale_code = 'Papi_L' THEN ps.score::numeric ELSE NULL END) as papi_l,
            MAX(CASE WHEN ps.scale_code = 'Papi_P' THEN ps.score::numeric ELSE NULL END) as papi_p,
            MAX(CASE WHEN ps.scale_code = 'Papi_A' THEN ps.score::numeric ELSE NULL END) as papi_a,
            MAX(CASE WHEN ps.scale_code = 'Papi_S' THEN ps.score::numeric ELSE NULL END) as papi_s,
            -- Get strengths as flags
            MAX(CASE WHEN s.theme = 'Adaptability' THEN 1 ELSE 0 END) as strength_adaptability,
            MAX(CASE WHEN s.theme = 'Connectedness' THEN 1 ELSE 0 END) as strength_connectedness,
            MAX(CASE WHEN s.theme = 'Analytical' THEN 1 ELSE 0 END) as strength_analytical,
            MAX(CASE WHEN s.theme = 'Strategic' THEN 1 ELSE 0 END) as strength_strategic,
            MAX(CASE WHEN s.theme = 'Deliberative' THEN 1 ELSE 0 END) as strength_deliberative,
            MAX(CASE WHEN s.theme = 'Discipline' THEN 1 ELSE 0 END) as strength_discipline,
            MAX(CASE WHEN s.theme = 'Futuristic' THEN 1 ELSE 0 END) as strength_futuristic,
            MAX(CASE WHEN s.theme = 'Ideation' THEN 1 ELSE 0 END) as strength_ideation,
            MAX(CASE WHEN s.theme = 'Belief' THEN 1 ELSE 0 END) as strength_belief,
            MAX(CASE WHEN s.theme = 'Arranger' THEN 1 ELSE 0 END) as strength_arranger,
            MAX(CASE WHEN s.theme = 'Command' THEN 1 ELSE 0 END) as strength_command,
            MAX(CASE WHEN s.theme = 'Self-Assurance' THEN 1 ELSE 0 END) as strength_self_assurance,
            MAX(CASE WHEN s.theme = 'Developer' THEN 1 ELSE 0 END) as strength_developer,
            MAX(CASE WHEN s.theme = 'Achiever' THEN 1 ELSE 0 END) as strength_achiever,
            MAX(CASE WHEN s.theme = 'Communication' THEN 1 ELSE 0 END) as strength_communication,
            MAX(CASE WHEN s.theme = 'Woo' THEN 1 ELSE 0 END) as strength_woo,
            MAX(CASE WHEN s.theme = 'Relator' THEN 1 ELSE 0 END) as strength_relator
        FROM employees e
        LEFT JOIN profiles_psych pp ON e.employee_id = pp.employee_id
        LEFT JOIN papi_scores ps ON e.employee_id = ps.employee_id
        LEFT JOIN strengths s ON e.employee_id = s.employee_id
        WHERE e.employee_id = ANY(%s)
        GROUP BY e.employee_id, pp.disc, pp.mbti, pp.gtq, pp.tiki, pp.iq, pp.pauli
    ),
    tgv_calculations AS (
        SELECT 
            employee_id,
            
            -- 1. Adaptability & Stress Tolerance (4 TV)
            (
                COALESCE((CASE WHEN disc = 'S' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_t/10, 0) +
                COALESCE(papi_e/10, 0) +
                COALESCE(strength_adaptability, 0)
            ) / 4 AS adaptability_stress,
            
            -- 2. Cognitive Complexity & Problem-Solving (7 TV)
            (
                COALESCE(gtq::numeric/100, 0) +
                COALESCE(tiki::numeric/100, 0) +
                COALESCE(iq::numeric/100, 0) +
                COALESCE(papi_i/10, 0) +
                COALESCE(strength_connectedness, 0) +
                COALESCE(strength_analytical, 0) +
                COALESCE(strength_strategic, 0)
            ) / 7 AS cognitive_complexity,
            
            -- 3. Conscientiousness & Reliability (5 TV)
            (
                COALESCE((CASE WHEN disc = 'C' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_c/10, 0) +
                COALESCE(papi_d/10, 0) +
                COALESCE(strength_deliberative, 0) +
                COALESCE(strength_discipline, 0)
            ) / 5 AS conscientiousness,
            
            -- 4. Creativity & Innovation Orientation (4 TV)
            (
                COALESCE((CASE WHEN mbti LIKE '%%N%%' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_z/10, 0) +
                COALESCE(strength_futuristic, 0) +
                COALESCE(strength_ideation, 0)
            ) / 4 AS creativity_innovation,
            
            -- 5. Cultural & Values Urgency (1 TV)
            COALESCE(strength_belief, 0) AS cultural_values,
            
            -- 6. Leadership & Influence (9 TV)
            (
                COALESCE((CASE WHEN mbti LIKE 'E%%' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE((CASE WHEN mbti LIKE 'I%%' THEN 0.5 ELSE 0.0 END), 0) +
                COALESCE((CASE WHEN disc = 'D' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_l/10, 0) +
                COALESCE(papi_p/10, 0) +
                COALESCE(strength_arranger, 0) +
                COALESCE(strength_command, 0) +
                COALESCE(strength_self_assurance, 0) +
                COALESCE(strength_developer, 0)
            ) / 9 AS leadership_influence,
            
            -- 7. Motivation & Drive (3 TV)
            (
                COALESCE(pauli::numeric/100, 0) +
                COALESCE(papi_a/10, 0) +
                COALESCE(strength_achiever, 0)
            ) / 3 AS motivation_drive,
            
            -- 8. Social Orientation & Collaboration (5 TV)
            (
                COALESCE((CASE WHEN disc = 'I' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_s/10, 0) +
                COALESCE(strength_communication, 0) +
                COALESCE(strength_woo, 0) +
                COALESCE(strength_relator, 0)
            ) / 5 AS social_orientation
            
        FROM employee_data
    )
    SELECT 
        AVG(adaptability_stress) as adaptability_stress,
        AVG(cognitive_complexity) as cognitive_complexity,
        AVG(conscientiousness) as conscientiousness,
        AVG(creativity_innovation) as creativity_innovation,
        AVG(cultural_values) as cultural_values,
        AVG(leadership_influence) as leadership_influence,
        AVG(motivation_drive) as motivation_drive,
        AVG(social_orientation) as social_orientation,
        COUNT(*) as benchmark_count
    FROM tgv_calculations
    """
    
    try:
        df = pd.read_sql(query, conn, params=(benchmark_ids,))
        if df.empty or df.isnull().all().all():
            st.warning("No psychometric data found for selected benchmarks")
            return {}
        
        baseline_dict = df.iloc[0].to_dict()
        return baseline_dict
        
    except Exception as e:
        st.error(f"Error computing TGV baselines: {e}")
        return {}

# Get ranked talent dengan mapping TGV yang dikoreksi - SEMUA EMPLOYEE
def get_ranked_talent_with_tv_tgv_details(baseline_dict):
    """Get ranked talent menggunakan mapping 8 TGV dan 38 TV yang dikoreksi untuk SEMUA EMPLOYEE"""
    if not baseline_dict:
        return pd.DataFrame()
    
    query = """
    WITH employee_data AS (
        SELECT 
            e.employee_id,
            e.fullname,
            p.name as position,
            d.name as department,
            div.name as division,
            dir.name as directorate,
            g.name as grade,
            pp.disc,
            pp.mbti,
            pp.gtq,
            pp.tiki,
            pp.iq,
            pp.pauli,
            -- Get PAPI scores as key-value pairs
            MAX(CASE WHEN ps.scale_code = 'Papi_T' THEN ps.score::numeric ELSE NULL END) as papi_t,
            MAX(CASE WHEN ps.scale_code = 'Papi_E' THEN ps.score::numeric ELSE NULL END) as papi_e,
            MAX(CASE WHEN ps.scale_code = 'Papi_I' THEN ps.score::numeric ELSE NULL END) as papi_i,
            MAX(CASE WHEN ps.scale_code = 'Papi_C' THEN ps.score::numeric ELSE NULL END) as papi_c,
            MAX(CASE WHEN ps.scale_code = 'Papi_D' THEN ps.score::numeric ELSE NULL END) as papi_d,
            MAX(CASE WHEN ps.scale_code = 'Papi_Z' THEN ps.score::numeric ELSE NULL END) as papi_z,
            MAX(CASE WHEN ps.scale_code = 'Papi_L' THEN ps.score::numeric ELSE NULL END) as papi_l,
            MAX(CASE WHEN ps.scale_code = 'Papi_P' THEN ps.score::numeric ELSE NULL END) as papi_p,
            MAX(CASE WHEN ps.scale_code = 'Papi_A' THEN ps.score::numeric ELSE NULL END) as papi_a,
            MAX(CASE WHEN ps.scale_code = 'Papi_S' THEN ps.score::numeric ELSE NULL END) as papi_s,
            -- Get strengths as flags
            MAX(CASE WHEN s.theme = 'Adaptability' THEN 1 ELSE 0 END) as strength_adaptability,
            MAX(CASE WHEN s.theme = 'Connectedness' THEN 1 ELSE 0 END) as strength_connectedness,
            MAX(CASE WHEN s.theme = 'Analytical' THEN 1 ELSE 0 END) as strength_analytical,
            MAX(CASE WHEN s.theme = 'Strategic' THEN 1 ELSE 0 END) as strength_strategic,
            MAX(CASE WHEN s.theme = 'Deliberative' THEN 1 ELSE 0 END) as strength_deliberative,
            MAX(CASE WHEN s.theme = 'Discipline' THEN 1 ELSE 0 END) as strength_discipline,
            MAX(CASE WHEN s.theme = 'Futuristic' THEN 1 ELSE 0 END) as strength_futuristic,
            MAX(CASE WHEN s.theme = 'Ideation' THEN 1 ELSE 0 END) as strength_ideation,
            MAX(CASE WHEN s.theme = 'Belief' THEN 1 ELSE 0 END) as strength_belief,
            MAX(CASE WHEN s.theme = 'Arranger' THEN 1 ELSE 0 END) as strength_arranger,
            MAX(CASE WHEN s.theme = 'Command' THEN 1 ELSE 0 END) as strength_command,
            MAX(CASE WHEN s.theme = 'Self-Assurance' THEN 1 ELSE 0 END) as strength_self_assurance,
            MAX(CASE WHEN s.theme = 'Developer' THEN 1 ELSE 0 END) as strength_developer,
            MAX(CASE WHEN s.theme = 'Achiever' THEN 1 ELSE 0 END) as strength_achiever,
            MAX(CASE WHEN s.theme = 'Communication' THEN 1 ELSE 0 END) as strength_communication,
            MAX(CASE WHEN s.theme = 'Woo' THEN 1 ELSE 0 END) as strength_woo,
            MAX(CASE WHEN s.theme = 'Relator' THEN 1 ELSE 0 END) as strength_relator,
            -- Strengths (Top 3)
            (SELECT STRING_AGG(theme, ', ' ORDER BY rank) 
             FROM strengths s2 
             WHERE s2.employee_id = e.employee_id AND s2.rank <= 3) as top_strengths,
            -- Performance Rating
            (SELECT rating FROM performance_yearly py 
             WHERE py.employee_id = e.employee_id 
             ORDER BY year DESC LIMIT 1) as latest_performance
        FROM employees e
        LEFT JOIN profiles_psych pp ON e.employee_id = pp.employee_id
        LEFT JOIN papi_scores ps ON e.employee_id = ps.employee_id
        LEFT JOIN strengths s ON e.employee_id = s.employee_id
        LEFT JOIN dim_positions p ON e.position_id = p.position_id
        LEFT JOIN dim_departments d ON e.department_id = d.department_id
        LEFT JOIN dim_divisions div ON e.division_id = div.division_id
        LEFT JOIN dim_directorates dir ON e.directorate_id = dir.directorate_id
        LEFT JOIN dim_grades g ON e.grade_id = g.grade_id
        WHERE e.fullname IS NOT NULL
        GROUP BY e.employee_id, e.fullname, p.name, d.name, div.name, dir.name, g.name, 
                 pp.disc, pp.mbti, pp.gtq, pp.tiki, pp.iq, pp.pauli
    ),
    tgv_calculations AS (
        SELECT 
            *,
            -- Calculate each TGV score menggunakan mapping yang dikoreksi
            -- 1. Adaptability & Stress Tolerance (4 TV)
            (
                COALESCE((CASE WHEN disc = 'S' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_t/10, 0) +
                COALESCE(papi_e/10, 0) +
                COALESCE(strength_adaptability, 0)
            ) / 4 AS tv_adaptability,
            
            -- 2. Cognitive Complexity & Problem-Solving (7 TV)
            (
                COALESCE(gtq::numeric/100, 0) +
                COALESCE(tiki::numeric/100, 0) +
                COALESCE(iq::numeric/100, 0) +
                COALESCE(papi_i/10, 0) +
                COALESCE(strength_connectedness, 0) +
                COALESCE(strength_analytical, 0) +
                COALESCE(strength_strategic, 0)
            ) / 7 AS tv_cognitive,
            
            -- 3. Conscientiousness & Reliability (5 TV)
            (
                COALESCE((CASE WHEN disc = 'C' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_c/10, 0) +
                COALESCE(papi_d/10, 0) +
                COALESCE(strength_deliberative, 0) +
                COALESCE(strength_discipline, 0)
            ) / 5 AS tv_conscientiousness,
            
            -- 4. Creativity & Innovation Orientation (4 TV)
            (
                COALESCE((CASE WHEN mbti LIKE '%%N%%' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_z/10, 0) +
                COALESCE(strength_futuristic, 0) +
                COALESCE(strength_ideation, 0)
            ) / 4 AS tv_creativity,
            
            -- 5. Cultural & Values Urgency (1 TV)
            COALESCE(strength_belief, 0) AS tv_cultural_values,
            
            -- 6. Leadership & Influence (9 TV)
            (
                COALESCE((CASE WHEN mbti LIKE 'E%%' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE((CASE WHEN mbti LIKE 'I%%' THEN 0.5 ELSE 0.0 END), 0) +
                COALESCE((CASE WHEN disc = 'D' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_l/10, 0) +
                COALESCE(papi_p/10, 0) +
                COALESCE(strength_arranger, 0) +
                COALESCE(strength_command, 0) +
                COALESCE(strength_self_assurance, 0) +
                COALESCE(strength_developer, 0)
            ) / 9 AS tv_leadership,
            
            -- 7. Motivation & Drive (3 TV)
            (
                COALESCE(pauli::numeric/100, 0) +
                COALESCE(papi_a/10, 0) +
                COALESCE(strength_achiever, 0)
            ) / 3 AS tv_motivation,
            
            -- 8. Social Orientation & Collaboration (5 TV)
            (
                COALESCE((CASE WHEN disc = 'I' THEN 1.0 ELSE 0.0 END), 0) +
                COALESCE(papi_s/10, 0) +
                COALESCE(strength_communication, 0) +
                COALESCE(strength_woo, 0) +
                COALESCE(strength_relator, 0)
            ) / 5 AS tv_social
            
        FROM employee_data
    ),
    match_calculations AS (
        SELECT *,
            -- Final Match Rate calculation menggunakan semua 8 TGV
            (1 - (SQRT(
                POW(COALESCE(tv_adaptability, 0) - %s, 2) + 
                POW(COALESCE(tv_cognitive, 0) - %s, 2) + 
                POW(COALESCE(tv_conscientiousness, 0) - %s, 2) + 
                POW(COALESCE(tv_creativity, 0) - %s, 2) + 
                POW(COALESCE(tv_cultural_values, 0) - %s, 2) + 
                POW(COALESCE(tv_leadership, 0) - %s, 2) + 
                POW(COALESCE(tv_motivation, 0) - %s, 2) + 
                POW(COALESCE(tv_social, 0) - %s, 2)
            ) / 8)) * 100 AS final_match_rate
        FROM tgv_calculations
    )
    SELECT * FROM match_calculations
    WHERE final_match_rate IS NOT NULL
    ORDER BY final_match_rate DESC
    """
    
    # Prepare parameters untuk 8 TGV
    tgv_keys = [
        'adaptability_stress', 'cognitive_complexity', 'conscientiousness',
        'creativity_innovation', 'cultural_values', 'leadership_influence', 
        'motivation_drive', 'social_orientation'
    ]
    params = [baseline_dict.get(key, 0) for key in tgv_keys]
    
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Error ranking employees with TGV mapping: {e}")
        return pd.DataFrame()

# AI Job Profile Generation
def generate_job_profile(role_name, job_level, role_purpose, benchmark_ids):
    try:
        api_key = st.secrets["openai"]["api_key"]
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "AI Talent Dashboard"
        }
        
        # Get benchmark employee details for context
        benchmark_context = ""
        if benchmark_ids:
            placeholders = ','.join(['%s'] * len(benchmark_ids))
            query = f"""
            SELECT e.fullname, p.name as position, d.name as department
            FROM employees e
            LEFT JOIN dim_positions p ON e.position_id = p.position_id
            LEFT JOIN dim_departments d ON e.department_id = d.department_id
            WHERE e.employee_id IN ({placeholders})
            """
            df = pd.read_sql(query, conn, params=benchmark_ids)
            if not df.empty:
                benchmark_context = "Benchmark employees:\n" + "\n".join(
                    [f"• {row['fullname']} - {row['position']} ({row['department']})" 
                     for _, row in df.iterrows()]
                )
        
        prompt = f"""
        Create a comprehensive job profile for a {role_name} position at {job_level} level.

        ROLE PURPOSE: {role_purpose}

        {benchmark_context}

        Format your response EXACTLY like this structure:

        Job requirements
        • [specific technical skill 1]
        • [specific technical skill 2] 
        • [specific tool or technology]
        • [required experience or qualification]

        Job description
        [1-2 sentences describing the role's core purpose and daily activities]

        Key competencies
        1. [Technical skill category]: [specific tools/technologies]
        2. [Analytical skill category]: [specific methodologies]
        3. [Business skill category]: [specific applications]
        4. [Soft skill category]: [specific behaviors]

        Be specific, practical, and focus on actionable skills for a {job_level} level {role_name}.
        """
        
        data = {
            "model": "anthropic/claude-3-haiku",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return content
        else:
            # Fallback template
            return f"""Job requirements
• Technical expertise in {role_name.lower()} domain
• Data analysis and interpretation skills  
• Problem-solving and critical thinking
• Communication and collaboration abilities

Job description
You will be responsible for {role_purpose.lower()} using technical skills and business acumen to drive data-informed decisions.

Key competencies
1. Technical: Relevant tools and technologies for {role_name}
2. Analytical: Data-driven decision making and insights generation
3. Business: Stakeholder management and requirement gathering
4. Soft skills: Team collaboration and communication"""
            
    except Exception as e:
        return f"AI generation failed: {e}"

# =============================================================================
# VISUALIZATION FUNCTIONS FOR TAB 1 - DASHBOARD COMPONENTS
# =============================================================================

def create_tgv_strengths_gaps_chart(rankings, baseline_dict):
    """Top Strengths & Gaps across TGVs - Bar Plot"""
    if len(rankings) == 0 or not baseline_dict:
        return go.Figure()
    
    top_candidate = rankings.iloc[0]
    
    # TGV mapping untuk display
    tgv_display_names = {
        'tv_cognitive': 'Cognitive Complexity',
        'tv_leadership': 'Leadership & Influence', 
        'tv_adaptability': 'Adaptability & Stress',
        'tv_motivation': 'Motivation & Drive',
        'tv_creativity': 'Creativity & Innovation',
        'tv_conscientiousness': 'Conscientiousness',
        'tv_social': 'Social Orientation',
        'tv_cultural_values': 'Cultural Values'
    }
    
    gap_data = []
    
    for tv_key, display_name in tgv_display_names.items():
        if tv_key in top_candidate:
            baseline_key = tv_key.replace('tv_', '')
            if baseline_key in baseline_dict:
                candidate_score = top_candidate[tv_key]
                baseline_score = baseline_dict[baseline_key]
                gap = candidate_score - baseline_score
                
                gap_data.append({
                    'TGV': display_name,
                    'Candidate_Score': candidate_score,
                    'Benchmark_Score': baseline_score,
                    'Gap': gap,
                    'Type': 'Strength' if gap > 0 else 'Gap'
                })
    
    if not gap_data:
        return go.Figure()
        
    df = pd.DataFrame(gap_data)
    
    fig = go.Figure()
    
    # Add benchmark bars
    fig.add_trace(go.Bar(
        name='Benchmark',
        x=df['TGV'],
        y=df['Benchmark_Score'],
        marker_color='lightblue',
        opacity=0.7,
        text=df['Benchmark_Score'].round(3),
        textposition='auto'
    ))
    
    # Add candidate bars
    fig.add_trace(go.Bar(
        name='Top Candidate',
        x=df['TGV'],
        y=df['Candidate_Score'],
        marker_color='lightcoral',
        opacity=0.7,
        text=df['Candidate_Score'].round(3),
        textposition='auto'
    ))
    
    fig.update_layout(
        title='Top Candidate vs Benchmark: TGV Comparison',
        xaxis_tickangle=-45,
        yaxis_title="Score",
        barmode='group',
        showlegend=True,
        height=500
    )
    
    return fig

def create_benchmark_comparison_radar(rankings, baseline_dict, top_n=3):
    """Benchmark vs Candidate Comparisons - Radar Chart"""
    if len(rankings) == 0 or not baseline_dict:
        return go.Figure()
    
    # Select top N candidates
    top_candidates = rankings.head(top_n)
    
    # TGV categories untuk radar chart
    radar_categories = [
        'Cognitive', 'Leadership', 'Adaptability', 
        'Motivation', 'Creativity', 'Conscientiousness'
    ]
    
    radar_keys = [
        'cognitive_complexity', 'leadership_influence', 'adaptability_stress',
        'motivation_drive', 'creativity_innovation', 'conscientiousness'
    ]
    
    fig = go.Figure()
    
    # Add benchmark trace
    benchmark_scores = [baseline_dict.get(key, 0) for key in radar_keys]
    fig.add_trace(go.Scatterpolar(
        r=benchmark_scores + [benchmark_scores[0]],
        theta=radar_categories + [radar_categories[0]],
        fill='toself',
        name='Benchmark Profile',
        line=dict(color='blue', width=3),
        opacity=0.3
    ))
    
    # Colors for top candidates
    colors = ['red', 'orange', 'green']
    
    # Add top candidates traces
    for i, (_, candidate) in enumerate(top_candidates.iterrows()):
        candidate_scores = []
        for key in radar_keys:
            candidate_key = f"tv_{key.split('_')[0]}"
            candidate_scores.append(candidate.get(candidate_key, 0))
        
        fig.add_trace(go.Scatterpolar(
            r=candidate_scores + [candidate_scores[0]],
            theta=radar_categories + [radar_categories[0]],
            fill='toself',
            name=f"{candidate['fullname']} ({candidate['final_match_rate']:.1f}%)",
            line=dict(color=colors[i], width=2),
            opacity=0.5
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=True,
        title="Benchmark vs Top Candidates - Radar Comparison",
        height=500
    )
    
    return fig

def create_tgv_heatmap_comparison(rankings, baseline_dict, top_n=5):
    """TGV Heatmap - Candidate vs Benchmark Comparison"""
    if len(rankings) == 0 or not baseline_dict:
        return go.Figure()
    
    top_candidates = rankings.head(top_n)
    
    # TGV mapping
    tgv_mapping = {
        'tv_cognitive': 'Cognitive',
        'tv_leadership': 'Leadership',
        'tv_adaptability': 'Adaptability',
        'tv_motivation': 'Motivation',
        'tv_creativity': 'Creativity',
        'tv_conscientiousness': 'Conscientiousness',
        'tv_social': 'Social',
        'tv_cultural_values': 'Cultural'
    }
    
    # Prepare data for heatmap
    candidates_data = []
    candidate_names = []
    
    for _, candidate in top_candidates.iterrows():
        candidate_scores = []
        for tv_key, tgv_name in tgv_mapping.items():
            if tv_key in candidate:
                baseline_key = tv_key.replace('tv_', '')
                baseline_score = baseline_dict.get(baseline_key, 0)
                candidate_score = candidate[tv_key]
                
                # Calculate gap percentage
                if baseline_score > 0:
                    gap_pct = ((candidate_score - baseline_score) / baseline_score) * 100
                else:
                    gap_pct = 0
                
                candidate_scores.append(gap_pct)
        
        candidates_data.append(candidate_scores)
        candidate_names.append(f"{candidate['fullname']} ({candidate['final_match_rate']:.1f}%)")
    
    if not candidates_data:
        return go.Figure()
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=candidates_data,
        x=list(tgv_mapping.values()),
        y=candidate_names,
        colorscale='RdBu',
        zmid=0,
        text=[[f"{val:.1f}%" for val in row] for row in candidates_data],
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverinfo="text",
        hovertemplate="Candidate: %{y}<br>TGV: %{x}<br>Gap: %{z:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        title='TGV Gap Analysis: Candidates vs Benchmark (%)',
        xaxis_title="Talent Group Variables (TGV)",
        yaxis_title="Top Candidates",
        height=400
    )
    
    return fig

def create_match_rate_distribution(rankings):
    """Match Rate Distribution - Histogram"""
    if len(rankings) == 0:
        return go.Figure()
    
    fig = px.histogram(
        rankings, 
        x='final_match_rate',
        title="Match Rate Distribution Across Candidates",
        nbins=20,
        color_discrete_sequence=['#1f77b4'],
        opacity=0.7
    )
    
    # Add vertical line for average
    avg_match_rate = rankings['final_match_rate'].mean()
    fig.add_vline(
        x=avg_match_rate, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"Avg: {avg_match_rate:.1f}%"
    )
    
    fig.update_layout(
        xaxis_title="Match Rate (%)",
        yaxis_title="Number of Candidates",
        showlegend=False,
        height=400
    )
    
    return fig

def create_tgv_correlation_heatmap(rankings):
    """TGV Correlation Matrix - Heatmap"""
    if len(rankings) == 0:
        return go.Figure()
    
    # Select TGV columns
    tgv_columns = [col for col in rankings.columns if col.startswith('tv_')]
    
    if len(tgv_columns) < 2:
        return go.Figure()
    
    # Calculate correlation matrix
    corr_matrix = rankings[tgv_columns].corr()
    
    # Rename columns for display
    display_names = {
        'tv_cognitive': 'Cognitive',
        'tv_leadership': 'Leadership',
        'tv_adaptability': 'Adaptability',
        'tv_motivation': 'Motivation',
        'tv_creativity': 'Creativity',
        'tv_conscientiousness': 'Conscientiousness',
        'tv_social': 'Social',
        'tv_cultural_values': 'Cultural'
    }
    
    corr_matrix_display = corr_matrix.rename(
        index=display_names, 
        columns=display_names
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix_display.values,
        x=corr_matrix_display.columns,
        y=corr_matrix_display.index,
        colorscale='RdBu',
        zmin=-1,
        zmax=1,
        text=corr_matrix_display.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 12},
        hoverinfo="text",
        hovertemplate="TGV1: %{y}<br>TGV2: %{x}<br>Correlation: %{z:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        title='TGV Correlation Matrix',
        xaxis_title="Talent Group Variables",
        yaxis_title="Talent Group Variables",
        height=500
    )
    
    return fig

def generate_detailed_insights(rankings, baseline_dict):
    """Generate Detailed Insights dengan Top Strengths & Gaps"""
    if len(rankings) == 0:
        return "No data available for insights."
    
    top_candidate = rankings.iloc[0]
    
    insights = []
    insights.append(f"## Detailed Analysis: {top_candidate['fullname']}")
    insights.append(f"**Overall Match Rate:** {top_candidate['final_match_rate']:.1f}%")
    insights.append(f"**Position:** {top_candidate.get('position', 'N/A')}")
    insights.append(f"**Department:** {top_candidate.get('department', 'N/A')}")
    insights.append("")
    
    # Top Strengths Analysis
    strengths = []
    gaps = []
    
    tgv_analysis = {
        'tv_cognitive': 'Cognitive Complexity',
        'tv_leadership': 'Leadership & Influence',
        'tv_adaptability': 'Adaptability & Stress Tolerance',
        'tv_motivation': 'Motivation & Drive',
        'tv_creativity': 'Creativity & Innovation',
        'tv_conscientiousness': 'Conscientiousness & Reliability'
    }
    
    for tv_key, tgv_name in tgv_analysis.items():
        if tv_key in top_candidate:
            baseline_key = tv_key.replace('tv_', '')
            if baseline_key in baseline_dict:
                gap = top_candidate[tv_key] - baseline_dict[baseline_key]
                if gap > 0.15:
                    strengths.append(f"**{tgv_name}**: +{gap:.3f} above benchmark")
                elif gap < -0.15:
                    gaps.append(f"**{tgv_name}**: {gap:.3f} below benchmark")
    
    if strengths:
        insights.append("### Top Strengths vs Benchmark:")
        insights.extend([f"• {strength}" for strength in strengths])
        insights.append("")
    
    if gaps:
        insights.append("### Development Areas:")
        insights.extend([f"• {gap}" for gap in gaps])
        insights.append("")
    
    # Behavioral Insights
    if 'top_strengths' in top_candidate and pd.notna(top_candidate['top_strengths']):
        insights.append("### Behavioral Strengths Profile:")
        insights.append(f"**Top CliftonStrengths:** {top_candidate['top_strengths']}")
        insights.append("")
    
    # Performance Context
    if 'latest_performance' in top_candidate and pd.notna(top_candidate['latest_performance']):
        insights.append("### Performance Context:")
        insights.append(f"**Latest Performance Rating:** {top_candidate['latest_performance']}")
        insights.append("")
    
    # Recommendation
    match_rate = top_candidate['final_match_rate']
    if match_rate >= 85:
        insights.append("### Recommendation: STRONG MATCH")
        insights.append("Excellent alignment with benchmark profiles across multiple TGVs.")
    elif match_rate >= 70:
        insights.append("### Recommendation: GOOD MATCH")
        insights.append("Solid alignment with key competencies, some development areas identified.")
    else:
        insights.append("### Recommendation: MODERATE MATCH")
        insights.append("Some alignment present but significant gaps require development.")
    
    return "\n".join(insights)

# NEW FUNCTION: Get Top TVs (Specific Assessments)
def get_top_tvs(candidate):
    """Get top 3 Talent Variables (specific assessments) for a candidate"""
    tv_scores = []
    
    # Cognitive assessments
    if pd.notna(candidate.get('gtq')) and candidate['gtq'] > 0:
        tv_scores.append(('GTQ', candidate['gtq']/100))
    if pd.notna(candidate.get('tiki')) and candidate['tiki'] > 0:
        tv_scores.append(('TIKI', candidate['tiki']/100))
    if pd.notna(candidate.get('iq')) and candidate['iq'] > 0:
        tv_scores.append(('IQ', candidate['iq']/100))
    if pd.notna(candidate.get('pauli')) and candidate['pauli'] > 0:
        tv_scores.append(('Pauli', candidate['pauli']/100))
    
    # DISC profile scores
    if pd.notna(candidate.get('disc')):
        disc = candidate['disc']
        if 'D' in disc:
            tv_scores.append(('DISC-D', 1.0))
        if 'I' in disc:
            tv_scores.append(('DISC-I', 1.0))
        if 'S' in disc:
            tv_scores.append(('DISC-S', 1.0))
        if 'C' in disc:
            tv_scores.append(('DISC-C', 1.0))
    
    # MBTI dimensions
    if pd.notna(candidate.get('mbti')):
        mbti = str(candidate['mbti'])
        if 'E' in mbti:
            tv_scores.append(('MBTI-E', 1.0))
        if 'I' in mbti:
            tv_scores.append(('MBTI-I', 0.8))
        if 'S' in mbti:
            tv_scores.append(('MBTI-S', 1.0))
        if 'N' in mbti:
            tv_scores.append(('MBTI-N', 1.0))
        if 'T' in mbti:
            tv_scores.append(('MBTI-T', 1.0))
        if 'F' in mbti:
            tv_scores.append(('MBTI-F', 1.0))
        if 'J' in mbti:
            tv_scores.append(('MBTI-J', 1.0))
        if 'P' in mbti:
            tv_scores.append(('MBTI-P', 1.0))
    
    # PAPI scores
    papi_mapping = {
        'papi_t': 'PAPI-T', 'papi_e': 'PAPI-E', 'papi_i': 'PAPI-I',
        'papi_c': 'PAPI-C', 'papi_d': 'PAPI-D', 'papi_z': 'PAPI-Z',
        'papi_l': 'PAPI-L', 'papi_p': 'PAPI-P', 'papi_a': 'PAPI-A',
        'papi_s': 'PAPI-S'
    }
    
    for papi_key, papi_name in papi_mapping.items():
        if pd.notna(candidate.get(papi_key)) and candidate[papi_key] > 0:
            tv_scores.append((papi_name, candidate[papi_key]/10))
    
    # Strengths
    strength_mapping = {
        'strength_adaptability': 'Str-Adaptability',
        'strength_connectedness': 'Str-Connectedness',
        'strength_analytical': 'Str-Analytical',
        'strength_strategic': 'Str-Strategic',
        'strength_deliberative': 'Str-Deliberative',
        'strength_discipline': 'Str-Discipline',
        'strength_futuristic': 'Str-Futuristic',
        'strength_ideation': 'Str-Ideation',
        'strength_belief': 'Str-Belief',
        'strength_arranger': 'Str-Arranger',
        'strength_command': 'Str-Command',
        'strength_self_assurance': 'Str-SelfAssurance',
        'strength_developer': 'Str-Developer',
        'strength_achiever': 'Str-Achiever',
        'strength_communication': 'Str-Communication',
        'strength_woo': 'Str-Woo',
        'strength_relator': 'Str-Relator'
    }
    
    for strength_key, strength_name in strength_mapping.items():
        if pd.notna(candidate.get(strength_key)) and candidate[strength_key] > 0:
            tv_scores.append((strength_name, 1.0))
    
    # Sort by score and get top 3
    tv_scores.sort(key=lambda x: x[1], reverse=True)
    top_tvs = tv_scores[:3]
    
    # Format as string
    if top_tvs:
        return ', '.join([f"{name}({score:.2f})" for name, score in top_tvs])
    else:
        return "No TV data"

# NEW FUNCTION: Get Top TGVs
def get_top_tgvs(candidate):
    """Get top 3 Talent Group Variables for a candidate"""
    tgv_mapping = {
        'tv_cognitive': 'Cognitive',
        'tv_leadership': 'Leadership',
        'tv_adaptability': 'Adaptability',
        'tv_motivation': 'Motivation',
        'tv_creativity': 'Creativity',
        'tv_conscientiousness': 'Conscientiousness',
        'tv_social': 'Social',
        'tv_cultural_values': 'Cultural'
    }
    
    tgv_scores = []
    for tgv_key, tgv_name in tgv_mapping.items():
        if pd.notna(candidate.get(tgv_key)) and candidate[tgv_key] > 0:
            tgv_scores.append((tgv_name, candidate[tgv_key]))
    
    # Sort by score and get top 3
    tgv_scores.sort(key=lambda x: x[1], reverse=True)
    top_tgvs = tgv_scores[:3]
    
    # Format as string
    if top_tgvs:
        return ', '.join([f"{name}({score:.2f})" for name, score in top_tgvs])
    else:
        return "No TGV data"

# Form functions
def render_role_information_form():
    st.header("Role Information")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        role_name = st.text_input("Role Name", placeholder="Ex: Data Analyst, Marketing Manager", key="role_name_tab1")
    with col2:
        job_level = st.selectbox("Job Level", ["Choose level", "Junior", "Middle", "Senior", "Lead", "Principal"], key="job_level_tab1")
    
    role_purpose = st.text_area("Role Purpose", 
                              placeholder="Describe the primary purpose and expected outcomes of this role...", 
                              height=100,
                              key="role_purpose_tab1")
    
    st.markdown("---")
    st.subheader("Employee Benchmarking")
    st.caption("Select high-performing employees as benchmarks (max 3)")
    
    employee_options = get_employee_options()
    selected_benchmarks = st.multiselect(
        "Select Benchmark Employees", 
        options=employee_options, 
        max_selections=3,
        placeholder="Choose 1-3 top performers...",
        key="benchmarks_tab1"
    )
    
    benchmark_ids = extract_employee_ids(selected_benchmarks)
    
    generate_btn = st.button("Generate Talent Analysis", 
                           type="primary", 
                           use_container_width=True,
                           key="generate_tab1")
    
    return generate_btn, role_name, job_level, role_purpose, benchmark_ids

def render_job_details_form():
    st.header("Job Details")
    st.write("All fields below are required. Please add at least one item for each category.")
    
    categories = {
        'responsibilities': {
            'title': 'Key Responsibilities',
            'placeholder': 'e.g., Develop and maintain data pipelines, Analyze business requirements...'
        },
        'work_inputs': {
            'title': 'Work Inputs', 
            'placeholder': 'e.g., Business requirements, Data sources, User stories...'
        },
        'work_outputs': {
            'title': 'Work Outputs',
            'placeholder': 'e.g., Analytics dashboards, Data models, Reports...'
        },
        'qualifications': {
            'title': 'Qualifications',
            'placeholder': 'e.g., Bachelor\'s in Computer Science, 3+ years experience...'
        },
        'competencies': {
            'title': 'Competencies',
            'placeholder': 'e.g., JavaScript Frameworks, Problem Solving, Team Collaboration...'
        }
    }
    
    for category, config in categories.items():
        st.subheader(f"{config['title']}")
        
        for i, item in enumerate(st.session_state.job_details[category]):
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.session_state.job_details[category][i] = st.text_input(
                    f"{config['title']} {i+1}", 
                    value=item,
                    placeholder=config['placeholder'],
                    label_visibility="collapsed",
                    key=f"{category}_{i}_tab2"
                )
            with col2:
                if st.button("Delete", key=f"del_{category}_{i}_tab2"):
                    st.session_state.job_details[category].pop(i)
                    st.rerun()
        
        if st.button(f"Add {config['title']}", key=f"add_{category}_tab2"):
            st.session_state.job_details[category].append("")
            st.rerun()
        
        st.markdown("---")
    
    generate_btn = st.button("Generate Ranked Talent List", 
                           type="primary", 
                           use_container_width=True,
                           key="generate_tab2")
    
    return generate_btn

def display_ranked_talent_list_tab1(rankings, baseline_dict):
    """Display Ranked Talent List untuk Tab 1 dengan kolom yang diminta"""
    st.header("Ranked Talent List")
    
    if len(rankings) == 0:
        st.warning("No data available for display")
        return
    
    # Buat dataframe untuk display dengan kolom yang diminta
    display_data = []
    
    for _, candidate in rankings.iterrows():
        # Get top TGVs dan top TVs menggunakan fungsi baru
        top_tgvs = get_top_tgvs(candidate)
        top_tvs = get_top_tvs(candidate)
        
        # Identifikasi strengths dan gaps
        strengths = []
        gaps = []
        
        tgv_mapping = {
            'tv_cognitive': 'Cognitive',
            'tv_leadership': 'Leadership',
            'tv_adaptability': 'Adaptability',
            'tv_motivation': 'Motivation',
            'tv_creativity': 'Creativity',
            'tv_conscientiousness': 'Conscientiousness',
            'tv_social': 'Social',
            'tv_cultural_values': 'Cultural'
        }
        
        for tv_key, tgv_name in tgv_mapping.items():
            if tv_key in candidate:
                baseline_key = tv_key.replace('tv_', '')
                if baseline_key in baseline_dict:
                    gap = candidate[tv_key] - baseline_dict[baseline_key]
                    if gap > 0.1:
                        strengths.append(f"{tgv_name}(+{gap:.2f})")
                    elif gap < -0.1:
                        gaps.append(f"{tgv_name}({gap:.2f})")
        
        candidate_data = {
            'employee_id': candidate['employee_id'],
            'name': candidate['fullname'],
            'final_match_rate': candidate['final_match_rate'],
            'top_tgvs': top_tgvs,
            'top_tvs': top_tvs,
            'strengths': ', '.join(strengths) if strengths else 'None',
            'gaps': ', '.join(gaps) if gaps else 'None',
            'position': candidate.get('position', 'N/A'),
            'department': candidate.get('department', 'N/A')
        }
        display_data.append(candidate_data)
    
    display_df = pd.DataFrame(display_data)
    
    # Format display
    display_df['final_match_rate'] = display_df['final_match_rate'].round(1)
    
    # Rename columns untuk clean display
    column_rename = {
        'employee_id': 'Employee ID',
        'name': 'Name',
        'final_match_rate': 'Match Rate (%)',
        'top_tgvs': 'Top TGVs (Score)',
        'top_tvs': 'Top TVs (Score)',
        'strengths': 'Strengths vs Benchmark',
        'gaps': 'Gaps vs Benchmark',
        'position': 'Position',
        'department': 'Department'
    }
    
    display_df = display_df.rename(columns=column_rename)
    
    # Tampilkan tabel dengan progress bar untuk match rate
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Match Rate (%)": st.column_config.ProgressColumn(
                "Match Rate (%)",
                help="Match rate percentage",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            )
        }
    )

# REVISED FUNCTION: Display untuk Tab 2 dengan kolom tambahan
def display_simple_ranked_talent_list(rankings, title="Ranked Talent List"):
    """Display sederhana untuk Tab 2 dengan kolom Role, Division, dan Job Level"""
    st.header(title)
    
    # Kolom untuk Tab 2 - ditambah Role, Division, Job Level
    display_columns = [
        'employee_id', 'fullname', 'final_match_rate', 'position', 'department',
        'division', 'grade'
    ]
    
    available_columns = [col for col in display_columns if col in rankings.columns]
    display_df = rankings[available_columns].copy()
    
    # Format display
    display_df['final_match_rate'] = display_df['final_match_rate'].round(1)
    
    # Rename columns untuk clean display
    column_rename = {
        'employee_id': 'Employee ID',
        'fullname': 'Name',
        'final_match_rate': 'Match Rate (%)',
        'position': 'Role',  # Diubah dari Position menjadi Role
        'department': 'Department',
        'division': 'Division',  # Kolom baru
        'grade': 'Job Level'  # Kolom baru
    }
    
    display_df = display_df.rename(columns=column_rename)
    
    # Tampilkan tabel sederhana
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Match Rate (%)": st.column_config.ProgressColumn(
                "Match Rate (%)",
                help="Match rate percentage",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            )
        }
    )

# =============================================================================
# MAIN APP LAYOUT - REVISED DASHBOARD
# =============================================================================

def main():
    st.set_page_config(page_title="Talent Match Intelligence", layout="wide")
    st.title("Talent Match Intelligence System")
    
    # Create tabs
    tab1, tab2 = st.tabs(["Role Information", "Job Details"])
    
    with tab1:
        # TAB 1: Role Information → Output: AI Job Profile + Ranked Talent + COMPREHENSIVE DASHBOARD
        generate_btn, role_name, job_level, role_purpose, benchmark_ids = render_role_information_form()
        
        if generate_btn:
            if not all([role_name, job_level != "Choose level", role_purpose, benchmark_ids]):
                st.error("Please complete all Role Information fields and select benchmark employees")
            else:
                with st.spinner("Generating comprehensive analysis..."):
                    # Generate AI Job Profile
                    ai_profile = generate_job_profile(role_name, job_level, role_purpose, benchmark_ids)
                    st.session_state.ai_job_profile = ai_profile
                    
                    # Compute talent matching dengan mapping TGV yang dikoreksi
                    baseline = compute_tgv_baselines(benchmark_ids)
                    
                    if baseline:
                        rankings = get_ranked_talent_with_tv_tgv_details(baseline)
                        
                        if not rankings.empty:
                            st.session_state.ranked_talent = rankings
                            st.session_state.baseline = baseline
                            st.session_state.role_info_generated = True
                            
                            st.markdown("---")
                            
                            # OUTPUT 1: AI-Generated Job Profile
                            st.header("AI-Generated Job Profile")
                            st.markdown(ai_profile)
                            
                            st.markdown("---")
                            
                            # OUTPUT 2: Ranked Talent List - DENGAN KOLOM YANG DIMINTA
                            display_ranked_talent_list_tab1(rankings, baseline)
                            
                            st.markdown("---")
                            
                            # OUTPUT 3: COMPREHENSIVE DASHBOARD VISUALIZATION
                            st.header("Talent Match Dashboard - Comprehensive Analysis")
                            
                            # ROW 1: Match Distribution & Top Strengths Gaps
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.plotly_chart(
                                    create_match_rate_distribution(rankings), 
                                    use_container_width=True
                                )
                            
                            with col2:
                                st.plotly_chart(
                                    create_tgv_strengths_gaps_chart(rankings, baseline),
                                    use_container_width=True
                                )
                            
                            # ROW 2: Benchmark Comparisons (Radar + Heatmap)
                            st.subheader("Benchmark vs Candidate Comparisons")
                            
                            col3, col4 = st.columns(2)
                            
                            with col3:
                                st.plotly_chart(
                                    create_benchmark_comparison_radar(rankings, baseline),
                                    use_container_width=True
                                )
                            
                            with col4:
                                st.plotly_chart(
                                    create_tgv_heatmap_comparison(rankings, baseline),
                                    use_container_width=True
                                )
                            
                            # ROW 3: Correlation Analysis
                            st.subheader("TGV Relationship Analysis")
                            st.plotly_chart(
                                create_tgv_correlation_heatmap(rankings),
                                use_container_width=True
                            )
                            
                            # ROW 4: Detailed Insights
                            st.markdown("---")
                            st.markdown(generate_detailed_insights(rankings, baseline))
                            
                        else:
                            st.error("No ranking results returned")
                    else:
                        st.error("Could not compute TGV baselines from selected benchmarks")
    
    with tab2:
        # TAB 2: Job Details → Output: HANYA Ranked Talent List (sederhana)
        generate_btn = render_job_details_form()
        
        if generate_btn:
            # Validate job details
            required_fields = ['responsibilities', 'work_inputs', 'work_outputs', 'qualifications', 'competencies']
            valid_job_details = all(
                len(st.session_state.job_details.get(field, [])) > 0 and 
                any(item.strip() for item in st.session_state.job_details.get(field, [])) 
                for field in required_fields
            )
            
            if not valid_job_details:
                st.error("Please add at least one valid item for each category in Job Details")
            else:
                with st.spinner("Computing talent matches..."):
                    # For Tab 2, use default benchmark employees
                    st.info("Using default benchmark employees for talent matching")
                    
                    # Get some default benchmark employees
                    default_query = """
                    SELECT employee_id FROM employees 
                    WHERE fullname IS NOT NULL 
                    LIMIT 3
                    """
                    default_benchmarks = pd.read_sql(default_query, conn)['employee_id'].tolist()
                    
                    baseline = compute_tgv_baselines(default_benchmarks)
                    
                    if baseline:
                        rankings = get_ranked_talent_with_tv_tgv_details(baseline)
                        
                        if not rankings.empty:
                            st.session_state.ranked_talent = rankings
                            st.session_state.job_details_generated = True
                            
                            st.markdown("---")
                            
                            # OUTPUT: HANYA Ranked Talent List (sederhana) dengan kolom tambahan
                            display_simple_ranked_talent_list(rankings, "Ranked Talent List")
                            
                        else:
                            st.error("No ranking results returned")
                    else:
                        st.error("Could not compute TGV baselines")

if __name__ == "__main__":

    main()

