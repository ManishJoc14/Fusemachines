
---

## 1. Linear Regression (Ordinary Least Squares)
- **What:** Models a continuous response as a linear function of inputs: $y = X\beta + \varepsilon$.
- **OLS estimate (normal equations):** $\hat{\beta} = (X^T X)^{-1} X^T y$.
- **Objective:** minimize sum of squared residuals $\sum_i (y_i - x_i^T\beta)^2$.

---

## 2. Assumptions of the Classical Linear Model
- **Linearity:** expectation of $y$ is linear in parameters.
- **Independence:** errors $\varepsilon_i$ are independent.
- **Homoscedasticity:** Var($\varepsilon_i$) = $\sigma^2$ (constant).
- **No perfect multicollinearity:** $X^T X$ invertible.
- **Errors normally distributed** (for exact finite-sample inference): $\varepsilon \sim N(0,\sigma^2 I)$.

---

## 3. Gauss–Markov Theorem
- **Result:** Under assumptions (except normality), OLS is the Best Linear Unbiased Estimator (BLUE).
- **Meaning:** among linear unbiased estimators, OLS has minimum variance.

---

## 4. Variance and Standard Errors
- **Error variance estimator:** $\hat{\sigma}^2 = \frac{1}{n-p}\sum (y_i - x_i^T\hat{\beta})^2$ where $p$ = number of parameters.
- **Covariance of coefficients:** $\mathrm{Cov}(\hat{\beta}) = \hat{\sigma}^2 (X^T X)^{-1}$.
- **Standard error:** $\mathrm{SE}(\hat{\beta}_j)=\sqrt{\mathrm{Var}(\hat{\beta}_j)}$.

---

## 5. Hypothesis Tests & Confidence Intervals
- **t-test (single coefficient):** $t = \frac{\hat{\beta}_j - b_0}{\mathrm{SE}(\hat{\beta}_j)}$ with $n-p$ d.f.
- **p-value:** probability of observing |t| or more extreme under null.
- **Confidence interval (e.g., 95%):** $\hat{\beta}_j \pm t_{n-p,0.975}\cdot \mathrm{SE}(\hat{\beta}_j)$.
- **F-test:** joint test for multiple coefficients (e.g., all slopes = 0).

---

## 6. Goodness‑of‑Fit
- **R²:** proportion of variance explained: $R^2 = 1 - \frac{\mathrm{SSR}}{\mathrm{SST}}$.
- **Adjusted R²:** penalizes extra predictors: $1 - (1-R^2)\frac{n-1}{n-p}$.

---

## 7. Multicollinearity
- **What:** predictors highly correlated → inflated variances for $\hat{\beta}$.
- **VIF (Variance Inflation Factor):** $\mathrm{VIF}_j = \frac{1}{1-R_j^2}$; large VIF (>10) signals trouble.
- **Condition number (κ):** ratio of largest to smallest singular value of $X$; large κ → near singular.

---

## 8. Regularization
- **Ridge (L2):** minimizes $\|y - X\beta\|^2 + \lambda \|\beta\|_2^2$ → closed form: $\hat{\beta}_{\text{ridge}} = (X^T X + \lambda I)^{-1} X^T y$.
- **Lasso (L1):** minimizes $\|y - X\beta\|^2 + \lambda \|\beta\|_1$ → promotes sparsity; solved via coordinate descent.
- **Elastic Net:** combination of L1 and L2.
- **Note:** standardize features before regularizing.

---

## 9. Model Selection & Validation
- **Train/test split:** estimate generalization on held‑out data.
- **k‑fold cross‑validation:** average performance across folds; use to tune hyperparameters (e.g., $\lambda$).
- **Information criteria:** AIC/BIC trade off fit vs complexity.

---

## 10. Feature Engineering
- **Interactions:** include $x_1 x_2$ to model multiplicative effects.
- **Polynomial features:** model nonlinearity via $x, x^2, x^3, ...$ but beware overfitting.
- **Centering & scaling:** improves numerical stability and interpretability.

---

## 11. Robustness to Assumption Violations
- **Heteroscedasticity:** use robust (White) standard errors or weighted least squares (WLS).
- **Autocorrelation (time series):** use Durbin–Watson to detect; use GLS or Newey–West SEs.
- **Outliers & influential points:** detect with leverage, Cook's distance, DFBETAS; consider robust regression (Huber, RANSAC).

---

## 12. Computational Methods
- **Closed form:** $\hat{\beta} = (X^T X)^{-1} X^T y$ (works for small/medium p).
- **Gradient descent:** iterative method for large datasets or regularized objectives.
- **QR decomposition / SVD:** numerically stable ways to compute OLS and diagnose multicollinearity.

---

## 13. Partitioning Variability & Influence
- **Leverage:** diagonal of the hat matrix $H = X(X^T X)^{-1}X^T$; high leverage points can dominate fit.
- **Residuals:** raw residuals $e_i = y_i - \hat{y}_i$; studentized residuals adjust for influence.
- **Cook's distance:** measures effect of removing an observation on all coefficients.

---

## 14. Logistic Regression (Related classification model)
- **Model:** log odds linear in predictors: $\log\frac{p}{1-p} = X\beta$.
- **Fitted by:** maximum likelihood (no closed‑form), often via Newton–Raphson / IRLS.
- **Interpretation:** exponentiated coefficients are odds ratios.

---

## 15. Practical Tips
- **Always plot residuals:** look for patterns, heteroscedasticity, nonlinearity.
- **Standardize continuous predictors** when using regularization or interpreting coefficients.
- **Prefer cross‑validation** for model selection over in‑sample metrics.
- **Be skeptical of high R²** for models with many predictors; check adjusted R² and validation error.

---

## Additional Terms Important for Linear Models

- **Normal equations:** closed‑form derivation for OLS parameters.
- **Leverage & influence:** diagnostics to find data points that disproportionately affect estimates.
- **Weighted least squares (WLS):** handle heteroscedasticity by weighting observations.
- **Generalized Least Squares (GLS):** account for known correlation structure in errors.
- **Partial R²:** contribution of a predictor conditional on others.
- **Orthogonalization / PCA:** reduce multicollinearity and dimensionality.

---

## One‑line summary of core terms

| Term | Meaning |
|------|---------|
| OLS | Closed form $\hat{\beta}=(X^TX)^{-1}X^Ty$ |
| Gauss–Markov | OLS is BLUE under standard assumptions |
| SE | Standard error of coefficients |
| t‑test | Individual coefficient significance |
| F‑test | Joint significance test |
| R² / Adj. R² | Fit measures |
| Multicollinearity | correlated predictors, use VIF |
| Ridge | L2 regularization for stability |
| Lasso | L1 regularization for sparsity |
| CV | Cross‑validation for tuning |
| Heteroscedasticity | non‑constant variance; use robust SE |
| Leverage | influence from input design |
| Cook's distance | combined influence measure |

---

Written to mirror the Week 6 probabilistic summary style — concise formulas, diagnostics, and practical tips for linear models.
