
---

## 1. Data Inspection
- **head()** – View first n rows to understand structure and content.
- **info()** – Display column names, data types, non-null counts, memory usage.
- **describe()** – Summary statistics: count, mean, std, min, 25%, 50%, 75%, max.
- **dtypes** – Check data type of each column (object, int64, float64, etc.).

---

## 2. Data Types and Format Issues
- **String vs Numeric:** Some columns may be stored as strings (object) when they should be numeric (int, float).
- **Composite Columns:** Some fields combine multiple values (e.g., "120/80" for Blood Pressure).
- **Solution:** Use `pd.to_numeric()`, `.str.split()`, or `.str.extract()` to parse and convert.

---

## 3. String Operations (pandas str accessor)
- **`.str.split(delimiter, expand=True)`** – Split string column into multiple columns.
  - Example: "120/80" → Systolic=120, Diastolic=80.
  - `expand=True` returns a DataFrame instead of Series.
- **`.str.extract(pattern)`** – Extract pattern from string using regex.
- **`.str.contains(pattern)`** – Check if string contains pattern (useful for filtering).

---

## 4. Type Conversion
- **`pd.to_numeric(series, errors='coerce')`** – Convert to numeric, replace non-numeric with NaN.
- **`astype('int64')`** or **`astype('float64')`** – Explicit conversion (fails if invalid).
- **`pd.to_datetime(series)`** – Parse strings to datetime.
- **Why it matters:** Numeric types enable mathematical operations, statistics, and modeling.

---

## 5. Missing Data (Null/NaN Values)
- **`.isnull()` or `.isna()`** – Returns boolean mask of missing values.
- **`.isnull().sum()`** – Count missing values per column.
- **`.isnull().mean()`** – Proportion of missing values.
- **Detection is crucial:** Many algorithms fail with NaN values.

---

## 6. Missing Data Mechanisms (Why Data is Missing)
- **MCAR (Missing Completely at Random):** No pattern; missing independently of any variable.
  - Example: Random computer crash losing a patient's record.
  - Least problematic; safe to drop or impute.

- **MAR (Missing at Random):** Missing pattern depends on other observed variables.
  - Example: Patients with high cholesterol more likely to skip certain tests.
  - Can be handled with multiple imputation if the dependency is known.

- **MNAR (Missing Not at Random):** Missing value depends on the value itself.
  - Example: Patients refuse to report embarrassing diet information.
  - Most problematic; requires domain knowledge to handle correctly.

---

## 7. Handling Missing Values – Strategies
- **Drop rows (`dropna()`):** Remove entire rows with any missing value.
  - Pros: Simple, clean data.
  - Cons: Lose data, introduce bias if MNAR.

- **Drop column:** Remove columns with >threshold missing values.
  - Use when column is non-critical or >30% missing.

- **Forward fill (`fillna(method='ffill')`):** Propagate last observed value forward.
  - Use for time-series data only.

- **Backward fill (`fillna(method='bfill')`):** Propagate next value backward.
  - Use for time-series data only.

- **Fill with constant (`fillna(value)`):** Replace with fixed value (0, mean, median).
  - Clinical data: use domain-specific value (e.g., 0 for "not present").
  - Lifestyle data: use "Unknown" category.

- **Interpolation (`interpolate()`):** Fill based on neighboring values.
  - Suitable for continuous, ordered data.

- **Multiple imputation:** Use statistical model to predict missing values.
  - Advanced; preserves uncertainty better.

---

## 8. Univariate Analysis
- **One variable at a time** – Understand distribution, central tendency, spread.
- **Goal:** Identify outliers, skewness, and data quality issues before bivariate analysis.
- **Types:**
  - **Numerical:** Age, Cholesterol, BMI (continuous values).
  - **Categorical:** Sex, Smoking, Diet, Country (discrete categories).

---

## 9. Distribution Shape and Skewness
- **Skewness (γ):** Measure of asymmetry in distribution.
  - γ ≈ 0 → Symmetric, approximately normal.
  - γ > 0 → Right-skewed (long tail on right).
  - γ < 0 → Left-skewed (long tail on left).
  - |γ| < 0.5 → Approximately normal.
  - |γ| > 1 → Highly skewed; likely needs transformation.

- **Kurtosis (κ):** Measure of "tailedness" (how extreme the outliers are).
  - κ ≈ 0 → Normal (mesokurtic).
  - κ > 0 → Heavy tails; extreme values (leptokurtic).
  - κ < 0 → Light tails; fewer extreme values (platykurtic).

- **Why it matters:** Many algorithms assume normality (Linear Regression, Logistic Regression, LDA).

---

## 10. Data Transformations
- **Log Transform (`np.log1p()`):** For right-skewed data.
  - Compresses large values.
  - Uses log(1+x) to handle zero values safely.
  - Common for: income, medical measurements, count data.

- **Square Root Transform (`np.sqrt()`):** Milder alternative to log.
  - Useful for moderately right-skewed data.
  - Preserves more original structure.
  - Common for: count data, positively skewed features.

- **Box-Cox Transform:** Data-driven, finds optimal power λ.
  - Requires strictly positive values.
  - λ=0 → log transform, λ=0.5 → sqrt transform.
  - `scipy.stats.boxcox()`.

- **Yeo-Johnson Transform:** Like Box-Cox but handles zero/negative values.
  - More flexible; works with real-world medical data.
  - `sklearn.preprocessing.PowerTransformer(method='yeo-johnson')`.
  - Automatically learns best transformation.

- **Standardization (Z-score):** Center and scale.
  - Formula: z = (x - μ) / σ.
  - Result: mean=0, std=1.
  - Does NOT change distribution shape.
  - Use when features on different scales (Age vs Cholesterol).
  - `sklearn.preprocessing.StandardScaler`.

- **Min-Max Normalization:** Scale to fixed range [0,1].
  - Formula: x' = (x - min) / (max - min).
  - Does NOT fix skewness.
  - Sensitive to outliers.
  - `sklearn.preprocessing.MinMaxScaler`.

- **When NOT to transform:** If skewness < 0.5, data is already approximately normal.

---

## 11. Numerical Summary Statistics
- **Mean (μ):** Average value; affected by outliers.
- **Median:** Middle value; robust to outliers.
- **Mode:** Most frequent value.
- **Std (σ):** Spread around mean; Var = σ².
- **Quantiles (Percentiles):** 25% (Q1), 50% (Q2=median), 75% (Q3).
- **IQR (Interquartile Range):** Q3 - Q1; robust measure of spread.
- **Min/Max:** Extreme values.

---

## 12. Outliers – Identification and Treatment
- **Definition:** Values unusually far from the central tendency.
- **Detection methods:**
  - **IQR method:** Outliers are < Q1 - 1.5×IQR or > Q3 + 1.5×IQR.
  - **Z-score method:** Outliers have |z| > 3 (or 2.5 for sensitive detection).
  - **Visual:** Boxplot, scatter plot.

- **Are they errors or real?**
  - Medical context: "Outliers" may be real extreme cases (critically ill patients).
  - vs Data entry error: "AGE = 999" is likely a data quality issue.
  - Always investigate before removing.

- **Treatment:**
  - Remove (only if confirmed error).
  - Cap/clip to reasonable bounds (medical domain knowledge needed).
  - Flag and note for later analysis.
  - Use robust statistics (median, IQR) that aren't affected by outliers.

---

## 13. Categorical Variables – Exploration
- **Unique values:** `.nunique()` – Count distinct categories.
- **Value counts:** `.value_counts()` – Frequency of each category.
- **Proportions:** `.value_counts(normalize=True)` – Relative frequency.
- **Bar plot:** `sns.countplot()` or `.value_counts().plot(kind='bar')`.

- **Common issues:**
  - **Inconsistent encoding:** "Yes"/"yes"/"Y" for same category → use `.str.lower()`.
  - **Whitespace:** "Yes " != "Yes" → use `.str.strip()`.
  - **Rare categories:** Some categories appear very few times → consider grouping.

---

## 14. Data Merging and Joining
- **`.merge()`:** Join on common key(s), like SQL JOIN.
  - `how='inner'` – Only matching rows (default).
  - `how='left'` – All left rows + matches from right.
  - `how='right'` – All right rows + matches from left.
  - `how='outer'` – All rows from both.

- **`.join()`:** Join on index (simpler for DataFrames with matching indices).
- **`.concat()`:** Stack rows or columns (union).

- **Why it matters:** Clinical data often split across tables; need to combine.

---

## 15. Data Quality Checklist
- ✓ No unexpected missing values?
- ✓ Data types appropriate?
- ✓ Inconsistent encoding fixed (e.g., Yes/Y/yes)?
- ✓ Whitespace/punctuation cleaned?
- ✓ Outliers investigated?
- ✓ Ranges sensible (e.g., Age 0-130, not -5 or 999)?
- ✓ Duplicates checked?
- ✓ Enough samples for analysis?

---

## One-line summary of all terms

| Term | Meaning |
|------|---------|
| head() | View first rows |
| info() | Column names, types, non-null counts |
| describe() | Summary statistics |
| dtypes | Data type of each column |
| Composite columns | Multiple values in one field (e.g., "120/80") |
| str.split() | Split string column by delimiter |
| str.extract() | Extract pattern from string |
| pd.to_numeric() | Convert to numeric, coerce errors to NaN |
| astype() | Explicit type conversion |
| isnull() / isna() | Boolean mask of missing values |
| MCAR | Missing Completely At Random; least problematic |
| MAR | Missing At Random; depends on other variables |
| MNAR | Missing Not At Random; depends on value itself; most problematic |
| dropna() | Remove rows with missing values |
| fillna() | Fill missing values with constant or method |
| interpolate() | Fill based on neighboring values |
| Univariate analysis | Examine one variable at a time |
| Skewness | Measure of asymmetry; |γ| < 0.5 → normal |
| Kurtosis | Measure of tailedness / extreme values |
| Log transform | np.log1p(); for right-skewed data |
| Sqrt transform | Milder transformation for moderate skew |
| Box-Cox transform | Data-driven; requires positive values |
| Yeo-Johnson transform | Box-Cox alternative; handles zero/negative |
| Standardization (Z-score) | (x - μ) / σ; mean=0, std=1 |
| Min-Max normalization | (x - min) / (max - min); range [0,1] |
| Mean | Average; affected by outliers |
| Median | Middle value; robust to outliers |
| Std (σ) | Spread around mean; σ² = variance |
| IQR | Interquartile Range = Q3 - Q1 |
| Outlier (IQR method) | < Q1 - 1.5×IQR or > Q3 + 1.5×IQR |
| Outlier (Z-score) | \|z\| > 3 (or 2.5 for sensitive) |
| value_counts() | Frequency of each category |
| merge() | SQL-like join on key(s) |
| join() | Join on index |
| concat() | Stack rows or columns |

---
