
---

## 1. Decision Trees
- **What:** Supervised model that splits feature space into rectangles using axis-aligned rules.
- **Prediction:** majority class (classification) or mean value (regression) within a leaf.
- **Splitting:** choose feature and threshold that maximize impurity reduction.

---

## 2. Impurity & Split Criteria
- **Gini impurity:** $G = 1 - \sum_k p_k^2$.
- **Entropy (Information gain):** $H = -\sum_k p_k \log p_k$; gain = parent H - weighted children H.
- **Mean Squared Error (regression):** used as impurity for regression trees.

---

## 3. Information Gain & Gain Ratio
- **Information Gain:** reduction in impurity after a split.
- **Gain Ratio:** IG normalized by split information to penalize many-valued splits.

---

## 4. Overfitting & Regularization (Trees)
- Trees easily overfit when grown deep.
- **Control:** `max_depth`, `min_samples_split`, `min_samples_leaf`, `max_leaf_nodes`, `min_impurity_decrease`.
- **Pruning:** pre-pruning (stop early) or post-pruning (prune grown tree using validation data).

---

## 5. Bagging & Random Forests
- **Bagging:** bootstrap samples + average/vote reduces variance.
- **Random Forest:** bagged trees with random feature subsets at splits (`max_features`) to decorrelate trees.
- **Out-Of-Bag (OOB) error:** validation using samples not in bootstrap – approximate CV.
- **Feature importance:** mean decrease in impurity or permutation importance.

---

## 6. Boosting (AdaBoost, Gradient Boosting)
- **Boosting idea:** sequentially fit weak learners to residuals (or reweight examples) to reduce bias.
- **AdaBoost:** reweights misclassified examples; combines learners by weighted vote.
- **Gradient Boosting:** fits next learner to gradient of loss (residuals for squared error).
- **Key hyperparams:** `n_estimators`, `learning_rate`, `max_depth`, `subsample` (stochastic GB).

---

## 7. Modern GBMs (XGBoost, LightGBM, CatBoost)
- **XGBoost:** regularized objective, tree pruning, approximate histograms, parallelization.
- **LightGBM:** histogram-based, leaf-wise growth, faster on large data but riskier overfitting.
- **CatBoost:** handles categorical features natively with ordered boosting to reduce target leakage.

---

## 8. Regularization in Boosting
- **Shrinkage (learning rate):** multiplies each tree's contribution; smaller → more trees needed.
- **Tree regularization:** `max_depth`, `min_child_weight` (XGBoost), `lambda`/`alpha` (L2/L1 on leaf weights).
- **Subsample & colsample:** row and column sampling to reduce overfitting.

---

## 9. Evaluation & Validation
- **Cross-validation:** k-fold CV for hyperparameter tuning.
- **OOB (Random Forest):** alternative to CV.
- **Metrics:** accuracy, precision/recall, F1, ROC-AUC for classification; RMSE/MAE for regression.
- **Calibration:** check predicted probabilities (calibration curve, Brier score).

---

## 10. Class Imbalance Strategies
- **Resampling:** oversample minority (SMOTE), undersample majority.
- **Algorithmic:** class weights, focal loss, threshold tuning.
- **Evaluation:** use precision-recall curve when positive class is rare.

---

## 11. Interpretation & Explainability
- **Tree rules:** readable if tree is small.
- **Feature importance:** global view but biased toward high-cardinality features.
- **Partial Dependence Plots (PDP):** show marginal effect of a feature.
- **SHAP / TreeSHAP:** consistent, local explanations and feature contributions.

---

## 12. Computational Considerations
- **Training time:** trees are fast; ensembles scale with number of trees and data size.
- **Memory:** histogram methods reduce memory; LightGBM is memory-efficient.
- **Parallelism:** many implementations support multi-threading.

---

## 13. When to Use Trees / Ensembles
- Use when: non-linear relationships, mixed feature types, missing values, need for strong baseline.
- Avoid when: extremely high-dimensional sparse data (text) without feature engineering, or when strict probabilistic calibration is required (unless calibrated).

---

## 14. Hyperparameters to Tune (short list)
- `n_estimators`, `learning_rate`, `max_depth`, `min_samples_leaf`, `min_samples_split`, `subsample`, `max_features`, regularization terms.

---

## 15. One-line summary table
| Term | Meaning |
|------|---------|
| Decision Tree | Rule-based partitions predicting class or mean |
| Gini / Entropy | Split impurity measures; used to choose splits |
| Pruning | Reduce overfitting by limiting tree size |
| Bagging | Bootstrap aggregation to reduce variance |
| Random Forest | Bagged trees with random feature selection |
| Boosting | Sequential learners reducing bias (or residuals) |
| XGBoost / LightGBM / CatBoost | Optimized GBM implementations |
| OOB | Out-of-bag estimate for bagging methods |
| Feature importance | Global importance via impurity or permutation |
| SHAP | Local, additive feature attributions |

---

## Quick tips
- Start with `RandomForest` as a strong baseline.
- For tabular data, try `LightGBM`/`XGBoost` with modest tuning.
- Use early stopping with a validation set for boosting.
- Use permutation importance and SHAP to validate important features.

---

