installed.packages()[,"Package"]


# Load required libraries
library(dplyr)
library(ggplot2)
library(tidyr)
library(corrplot)
library(fmsb)  # For radar charts
library(psych)  # For PCA
library(caret)  # For regression



# Set working directory
setwd("C:/Users/LENOVO/Documents/case_sheets")

# Set theme for all plots
theme_set(theme_minimal(base_size = 12))

# Create output folder if not exists
if (!dir.exists("output")) {
  dir.create("output")
  cat("Created 'output/' folder\n")
}

# Load semua dataset
dim_companies <- read.csv("dim_companies.csv", stringsAsFactors = FALSE)
dim_areas <- read.csv("dim_areas.csv", stringsAsFactors = FALSE)
dim_positions <- read.csv("dim_positions.csv", stringsAsFactors = FALSE)
dim_departments <- read.csv("dim_departments.csv", stringsAsFactors = FALSE)
dim_divisions <- read.csv("dim_divisions.csv", stringsAsFactors = FALSE)
dim_directorates <- read.csv("dim_directorates.csv", stringsAsFactors = FALSE)
dim_grades <- read.csv("dim_grades.csv", stringsAsFactors = FALSE)
dim_education <- read.csv("dim_education.csv", stringsAsFactors = FALSE)
dim_majors <- read.csv("dim_majors.csv", stringsAsFactors = FALSE)
dim_competency_pillars <- read.csv("dim_competency_pillars.csv", stringsAsFactors = FALSE)

employees <- read.csv("employees.csv", stringsAsFactors = FALSE)
profiles_psych <- read.csv("profiles_psych.csv", stringsAsFactors = FALSE)
papi_scores <- read.csv("papi_scores.csv", stringsAsFactors = FALSE)
strengths <- read.csv("strengths.csv", stringsAsFactors = FALSE)
performance_yearly <- read.csv("performance_yearly.csv", stringsAsFactors = FALSE)
competencies_yearly <- read.csv("competencies_yearly.csv", stringsAsFactors = FALSE)

# Step 1: Data Preparation and Merging
# Aggregate performance_yearly to latest year per employee (or average if multiple)
performance_agg <- performance_yearly %>%
  group_by(employee_id) %>%
  summarise(rating = max(rating, na.rm = TRUE), .groups = "drop")  # Use max for high performer flag; adjust if needed

# Aggregate competencies_yearly (average score per employee)
competencies_agg <- competencies_yearly %>%
  group_by(employee_id) %>%
  summarise(avg_competency = mean(score, na.rm = TRUE), .groups = "drop")

# Aggregate papi_scores (average score per employee)
papi_agg <- papi_scores %>%
  group_by(employee_id) %>%
  summarise(avg_papi = mean(score, na.rm = TRUE), .groups = "drop")

# Aggregate strengths (concatenate top themes for simplicity)
strengths_agg <- strengths %>%
  group_by(employee_id) %>%
  summarise(top_strengths = paste(unique(theme), collapse = ", "), .groups = "drop")

# Merge into master dataset
master_data <- employees %>%
  left_join(performance_agg, by = "employee_id") %>%
  left_join(profiles_psych, by = "employee_id") %>%
  left_join(competencies_agg, by = "employee_id") %>%
  left_join(papi_agg, by = "employee_id") %>%
  left_join(strengths_agg, by = "employee_id")

# Define high performers (rating == 5)
master_data <- master_data %>% mutate(is_high_performer = ifelse(rating == 5, 1, 0))

# Handle missing values (impute with mean for numeric, or filter out rows with too many NAs)
master_data <- master_data %>% mutate(across(where(is.numeric), ~ ifelse(is.na(.), mean(., na.rm = TRUE), .)))

# Step 2: Data Exploration
# Descriptive stats
summary(master_data)

# Correlation matrix for numeric variables
numeric_vars <- master_data %>% select(rating, pauli, faxtor, iq, gtq, tiki, avg_competency, avg_papi, years_of_service_months, grade_id, education_id)
cor_matrix <- cor(numeric_vars, use = "complete.obs")
print(cor_matrix)

# Differences between high performers and others
high_vs_others <- master_data %>% group_by(is_high_performer) %>% summarise_all(~ mean(., na.rm = TRUE), .groups = "drop")
print(high_vs_others)

# Step 3: Visualizations for Storytelling
# 1. Heatmap of Competency Pillars by Performance Group
competency_heatmap <- competencies_yearly %>%
  left_join(master_data %>% select(employee_id, is_high_performer), by = "employee_id") %>%
  group_by(pillar_code, is_high_performer) %>% summarise(avg_score = mean(score, na.rm = TRUE), .groups = "drop") %>%
  pivot_wider(names_from = is_high_performer, values_from = avg_score, names_prefix = "Group_") %>%
  as.data.frame()
if (nrow(competency_heatmap) > 0) {
  rownames(competency_heatmap) <- competency_heatmap$pillar_code
  competency_heatmap <- competency_heatmap %>% select(-pillar_code)
  png("output/competency_heatmap.png")
  heatmap(as.matrix(competency_heatmap), Colv = NA, Rowv = NA, scale = "none", main = "Competency Scores: High Performers vs Others")
  dev.off()
}

# 2. Radar Chart for Psychometric Profiles (average for high performers)
psych_avg_high <- profiles_psych %>%
  left_join(master_data %>% select(employee_id, is_high_performer), by = "employee_id") %>%
  filter(is_high_performer == 1) %>% summarise(across(c(pauli, faxtor, iq, gtq, tiki), ~ mean(., na.rm = TRUE)))
psych_avg_others <- profiles_psych %>%
  left_join(master_data %>% select(employee_id, is_high_performer), by = "employee_id") %>%
  filter(is_high_performer == 0) %>% summarise(across(c(pauli, faxtor, iq, gtq, tiki), ~ mean(., na.rm = TRUE)))
if (nrow(psych_avg_high) > 0 && nrow(psych_avg_others) > 0) {
  radar_data <- rbind(rep(100, 5), rep(0, 5), psych_avg_high, psych_avg_others)  # Max/min for scaling
  png("output/psychometric_radar.png")
  radarchart(radar_data, axistype = 1, title = "Psychometric Profiles: High Performers (Blue) vs Others (Red)", pcol = c("blue", "red"), pfcol = c(rgb(0,0,1,0.3), rgb(1,0,0,0.3)))
  dev.off()
}

# 3. Correlation Plot
png("output/correlation_plot.png")
corrplot(cor_matrix, method = "circle", title = "Correlations Among Variables")
dev.off()

# 4. Comparison Matrix: Contextual Factors
contextual_plot <- ggplot(master_data, aes(x = factor(is_high_performer), y = years_of_service_months, fill = factor(is_high_performer))) +
  geom_boxplot() + labs(title = "Years of Service: High Performers vs Others", x = "High Performer", y = "Months")
ggsave("output/contextual_boxplot.png", contextual_plot)

# Step 4: Deriving the Success Formula
library(randomForest)
library(caret)

# Pilih variabel numerik dan target (rating)
numeric_vars <- master_data %>% 
  select(rating, pauli, faxtor, iq, gtq, tiki, avg_competency, avg_papi,
         years_of_service_months, grade_id, education_id)

# Tangani missing value dengan imputasi mean
numeric_vars <- numeric_vars %>% 
  mutate(across(everything(), ~ ifelse(is.na(.), mean(., na.rm = TRUE), .)))

# Normalisasi semua variabel predictor (tanpa target)
scaled_data <- numeric_vars %>% mutate(across(-rating, scale))

# Latih model langsung pada seluruh dataset aktual (tanpa split)
rf_model <- randomForest(
  rating ~ ., 
  data = scaled_data, 
  ntree = 500, 
  mtry = 3, 
  importance = TRUE
)

# Hitung prediksi pada data yang sama (karena ini model eksplanasi)
predictions <- predict(rf_model, newdata = scaled_data)
r2 <- cor(predictions, scaled_data$rating)^2

cat("Model R² (Random Forest on full data):", round(r2 * 100, 2), "%\n")

# Ambil tingkat kepentingan variabel (variable importance)
importance_df <- as.data.frame(importance(rf_model))
importance_df <- importance_df[order(-importance_df$IncNodePurity), ]
print(importance_df)

# Normalisasi nilai importance untuk bikin formula berbobot
weights <- importance_df$IncNodePurity / sum(importance_df$IncNodePurity)
success_formula <- paste0(
  "SuccessScore = ", 
  paste0(round(weights, 3), "*", rownames(importance_df), collapse = " + ")
)

# Step 5: Justification output
cat("Final Success Formula:", success_formula, "\n")
cat("Justification: Derived using Random Forest regression trained on full organizational data, ",
    "explaining ~", round(r2 * 100, 1), "% of variance in performance rating.\n", sep = "")

write.csv(cor_matrix, "output/correlation_matrix.csv")

