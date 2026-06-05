## Reflection: When the Bayesian answer changed my decision

### Example: Comparing churn rates (Part 1, Q3)

**My actual results from the assignment:**  

| Group | n | MLE (churn rate) | MAP | Prior pull |
|-------|---|-----------------|-----|-------------|
| Group A (Month‑to‑month, large) | ~3870 | 0.4271 | 0.4265 | 0.0006 |
| Group A_small (n=40) | 40 | 0.3750 | 0.3333 | 0.0417 |
| Group B (Two‑year, large) | ~1400 | 0.0283 | 0.0288 | 0.0005 |

When I look at the small sample of 40 month‑to‑month customers, the MLE gives a churn rate of 37.5%. Based only on that, I would likely launch an expensive retention campaign.

But the Bayesian approach with a Beta(2,8) prior tells a different story. The MAP estimate is 33.3%, pulled toward the prior mean of 20%. More importantly, the 94% HDI is wide, roughly 22% to 53%. This wide interval shows that the true rate could be as low as 22%, so the MLE is not trustworthy with such a small sample.

Instead of acting immediately, I will collect more data before committing to a costly campaign. The Bayesian answer changes my decision because it quantifies uncertainty directly, which the MLE does not. The mechanism is simple: the prior provides a sensible baseline, and the posterior HDI reveals how much we still don't know.