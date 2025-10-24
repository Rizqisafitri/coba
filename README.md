Project: Talent Match Intelligence Test

######################################################:StudyCase1######################################################:
**---Deskripsi**: Proyek ini adalah analisis data menggunakan R untuk mengidentifikasi faktor-faktor yang membuat karyawan berkinerja tinggi (high performers) sukses dalam organisasi. Berdasarkan dataset karyawan, psikometrik, kompetensi, dan performa, script ini melakukan data preparation, eksplorasi, visualisasi, serta modeling dengan Random Forest untuk menghasilkan "rumus sukses" (success formula) yang dapat digunakan untuk mencocokkan kandidat suksesi. Dibangun dengan R dan paket seperti dplyr, ggplot2, randomForest, dan caret.
**Fitur Utama**
1. Data prep & merging dari CSV karyawan.
2. Eksplorasi: korelasi, perbandingan high vs others.
3. Visualisasi: heatmap, radar, plot korelasi, boxplot.
4. Modeling: Random Forest untuk formula sukses.
   
**Prasyarat**
1. R 4.0+ (dengan paket: dplyr, ggplot2, tidyr, corrplot, fmsb, psych, caret, randomForest).
2. Dataset CSV di folder kerja (employees.csv, profiles_psych.csv, dll.).
3. RStudio (opsional).

**Instruksi Setup**
**Install R & RStudio.**
1. Set working directory: setwd("path/to/case_sheets").
2. Install paket: install.packages(c("dplyr", "ggplot2", ...)).
3. Jalankan script lengkap di RStudio.
4. Verifikasi: Cek folder output/ untuk CSV & PNG, plus console output rumus sukses.
   
**Troubleshooting**
1. Paket hilang: install.packages("nama_paket").
2. Path error: Pastikan CSV ada.



######################################################:StudyCase2######################################################:

**---Deskripsi**:Operasionalisasi logika talent matching dalam SQL untuk menghitung match rate karyawan terhadap lowongan pekerjaan berdasarkan benchmark psikometrik (DISC, PAPI, IQ, dll.) dan kompetensi. Menggunakan PostgreSQL dengan CTE untuk agregasi baseline, TV match, TGV match, dan final match rate. Dibangun dengan SQL (PostgreSQL).

**Fitur Utama**
1. Pembuatan tabel: talent_benchmarks (benchmark per lowongan) dan tgv_tv_mapping (mapping variabel psikometrik ke kompetensi).
2. Perhitungan match rate: Baseline dari selected talents, TV match (exact/numeric), TGV match (weighted), final match (overall).
3. Output: Tabel hasil match rate per karyawan, termasuk baseline, user score, dan rate.
   
**Prasyarat**
1. Version 9.8
2. Application Mode Commit Desktop
3. Python Version 3.13.7
4. Current User pgadmin4@pgadmin.org
5. Electron Version 35.4.0
6. Browser Chrome 134.0.6998.205
7. Operating System Windows-11-10.0.26100-SP0

**Troubleshooting**
1. Error JSONB: Pastikan PostgreSQL versi terbaru.
2. Data hilang: Cek tabel profiles_psych & strengths ada data.
3. Performance: Jika query lambat, tambah index pada employee_id.


######################################################:StudyCase3######################################################:

# Talent Match Intelligence - Study Case 3

## Deskripsi Singkat
Aplikasi web Streamlit untuk talent matching dengan integrasi Supabase (PostgreSQL) dan OpenRouter API. Analisis karyawan berdasarkan TGV/TV mapping, AI-generated job profiles, dan dashboard visualisasi. Dibangun dengan Python (Streamlit, psycopg2, Plotly, requests).

## Fitur Utama
- Koneksi Supabase untuk data karyawan (employees, profiles_psych, dll.).
- AI job profile generation via OpenRouter (Claude-3).
- Talent matching: Baseline dari benchmark, ranking berdasarkan TGV (8 kategori), TV (38 variabel).
- Dashboard: Charts (radar, heatmap, histogram), insights, ranked list.
- 2 tabs: Role Information (AI profile + dashboard) & Job Details (ranked list sederhana).

## Prasyarat
- Python 3.8+.
- Streamlit: `pip install streamlit psycopg2-binary pandas plotly requests`.
- Supabase account: Database URL, user, password, port (sslmode=require).
- OpenRouter API key (untuk AI generation).
- Secrets file (st.secrets) dengan keys: postgres (host, port, database, user, password), openai (api_key).

## Instruksi Setup
1. Install Python & paket: `pip install streamlit psycopg2-binary pandas plotly requests`.
2. Setup Supabase: Buat database, import tabel (employees, profiles_psych, papi_scores, strengths, dim_*).
3. Dapatkan OpenRouter API key dari openrouter.ai.
4. Buat file secrets.toml di .streamlit/ dengan config Supabase & API key.
5. Jalankan app: `streamlit run studycase3.py`.
6. Akses browser: http://localhost:8501. Pilih tab, isi form, generate analysis.

## Konfigurasi Secrets (secrets.toml)
Buat file `.streamlit/secrets.toml` di root folder proyek dengan isi berikut (sesuaikan dengan credentials Anda):
app password = "komtamamp11"

- **Catatan Keamanan**: Jangan commit file ini ke Git. Gunakan environment variables jika deploy ke production.

## Troubleshooting
- Error DB: Cek secrets Supabase & koneksi internet.
- Error AI: Verifikasi OpenRouter API key & quota.
- No data: Pastikan tabel di Supabase ada data.
- Performance: Jika lambat, kurangi query atau tambah index di DB.

## Kontribusi & Lisensi
MIT License. Data privasi hati-hati. Integrasi AI memerlukan API key valid.
