# Synthetic Drift Summary

- Drifted columns: **3**
- MonthlyCharges mean: 64.95 -> 84.32 (shift +19.37)
- Month-to-month contract share: 54.8% -> 95.9%
- Churn rate: 26.5% -> 55.0%

The injected drift was detected in MonthlyCharges, Contract, and Churn. In production, this result should block silent promotion and trigger investigation followed by retraining if the change is genuine.