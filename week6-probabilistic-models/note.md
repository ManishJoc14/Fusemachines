
---

## 1. MLE (Maximum Likelihood Estimation)
- **What:** Finds parameter value that makes observed data most probable.
- **Formula for binomial:** θ̂ = k/n.
- **No prior, no uncertainty** – just a point estimate.
- **Problem:** Unstable for small samples.

---

## 2. MAP (Maximum a Posteriori)
- **What:** Maximizes posterior = Likelihood × Prior.
- **Formula for Beta-Binomial:** (k + α – 1)/(n + α + β – 2).
- **Adds prior** – pulls estimate toward prior when data is small.
- **Still a point estimate** – no uncertainty.

---

## 3. Full Bayes
- **What:** Entire posterior distribution, not just the peak.
- **Gives:** Credible intervals, probability statements like P(θ_A > θ_B).
- **Requires:** MCMC when no closed form.

---

## 4. Beta(α, β) Distribution
- **Distribution for a probability** (e.g., churn rate).
- **Mean** = α/(α+β)
- **Variance** = αβ / [(α+β)²(α+β+1)]
- **Conjugate prior** for Bernoulli/Binomial – posterior is also Beta.

---

## 5. Dirichlet Distribution
- **Multivariate generalization of Beta** – for >2 categories.
- **Parameters:** α₁, α₂, …, αₖ.
- **Mean for category i** = α_i / sum(α)
- **Conjugate prior** for Multinomial.

---

## 6. Sequential Update
- Start with prior Beta(α, β).
- Each observation: if success → α += 1; if failure → β += 1.
- **Why?** Because Beta is conjugate – easy update.

---

## 7. Decision Boundary (Bayesian vs Frequentist)
- Bayesian: P(θ > threshold) > 0.90 reached at small n (17) due to prior.
- Frequentist: sample size for hypothesis test is huge (6304) because no prior and small effect size.

---

## 8. Multivariate Gaussian
- **Parameters:** mean vector μ, covariance matrix Σ.
- **Conditional Gaussian formula:**  
  μ₁|₂ = μ₁ + Σ₁₂ Σ₂₂⁻¹ (x₂ – μ₂)  
  σ²₁|₂ = Σ₁₁ – Σ₁₂ Σ₂₂⁻¹ Σ₂₁
- **Correlation** ρ = Σ₁₂ / √(Σ₁₁ Σ₂₂)

---

## 9. Condition Number (κ)
- **κ = largest eigenvalue / smallest eigenvalue** of Σ.
- Large κ (>1000) → near‑singular → numerical instability.
- Indicates multicollinearity.

---

## 10. BN (Bayesian Network) vs MRF
- **BN:** Directed acyclic graph (DAG) – causal interpretation.
- **MRF:** Undirected graph – correlational, no causality.
- **Use BN for interventions, MRF for cyclic relations.**

---

## 11. GP (Gaussian Process) Kernel
- **Trend kernel:** DotProduct – linear extrapolation.
- **Seasonal kernel:** RBF × ExpSineSquared(periodicity=1) – repeating pattern.
- **Noise kernel:** WhiteKernel – independent noise.

---

## 12. MCMC (Markov Chain Monte Carlo)
- **What:** Sampling from posterior when no closed form.
- **NUTS:** Adaptive Hamiltonian Monte Carlo – efficient.
- **Diagnostics:**  
  - **r_hat** (<1.01) = chains converged.  
  - **ess** (effective sample size) = number of independent draws.

---

## 13. Uncertainty in Bayesian
- **Posterior spread** → standard deviation, credible interval.
- **HDI (Highest Density Interval)** – narrowest interval containing 94% probability.
- **Direct interpretation:** 94% chance true value lies in interval.

---

## 14. L1 Regularization (Lasso)
- Adds penalty Σ|β| to loss.
- **Creates sparsity** – some coefficients become exactly zero.
- **Feature selection** automatically.

---

## 15. Log Odds
- **Odds** = p/(1-p)
- **Log odds** = ln(p/(1-p))
- Logistic regression models log odds as linear function: β₀ + β₁x₁ + …
- **Sigmoid** converts log odds back to probability.

---

## Additional Terms Not in the Summary but Important

### Prior Distribution
- Belief about parameter **before** seeing data.
- Can be **informative** (e.g., Beta(2,8)) or **non‑informative** (e.g., Beta(1,1)).
- Strength = α + β (pseudo‑observations).

### Posterior Distribution
- Prior updated with data.
- **Posterior ∝ Likelihood × Prior**.
- Contains all uncertainty.

### Likelihood
- Probability of observed data **given** parameter.
- For binomial: L(θ) = C(n,k) θ^k (1-θ)^(n-k).

### Conjugate Prior
- Prior and posterior belong to same distribution family.
- Beta for binomial, Dirichlet for multinomial, Normal for normal mean.
- **Why convenient?** Simple update without MCMC.

### Kernel (in GP)
- Covariance function: measures similarity between inputs.
- **RBF (Radial Basis Function):** k(x,x') = σ² exp(-||x-x'||² / (2ℓ²)).
- **ExpSineSquared:** periodic kernel.
- **DotProduct:** linear kernel.

### Length Scale (ℓ)
- In RBF kernel: how far you need to move in input space for output to change significantly.
- Small ℓ → quickly varying function. Large ℓ → smooth function.

### Periodicity
- In ExpSineSquared kernel: how often pattern repeats (e.g., 1 year).

### Effective Sample Size (ess)
- Number of **independent** draws from MCMC.
- Lower than number of samples due to autocorrelation.
- High ess = efficient sampling.

### R hat (Gelman‑Rubin)
- Compares within‑chain and between‑chain variance.
- Close to 1 → convergence.
- Rule of thumb: < 1.01.

### Credible Interval vs Confidence Interval
- **Credible interval (Bayesian):** Direct probability – “94% chance θ in [L,U]”.
- **Confidence interval (Frequentist):** Long‑run coverage – “In 94% of repeated samples, interval contains true θ.”

### HDI (Highest Density Interval)
- Narrowest credible interval.
- Every point inside has higher density than any point outside.

### Marginalization
- Integrating out a variable from joint distribution.
- For Gaussian: remove its row and column from mean and covariance.

### Conditional Independence
- Two variables are independent given a third.
- In DAGs: d‑separation determines conditional independence.

### D‑Separation
- Graphical criterion for conditional independence in BNs.
- Path blocked given evidence → independent.

### Bias‑Variance Tradeoff
- **Bias:** error from wrong assumptions.
- **Variance:** error from sensitivity to training data.
- More complex model: low bias, high variance (overfitting).
- Regularization increases bias, reduces variance.

### Overfitting
- Model fits training data too well, fails on test data.
- More parameters → more risk.

### Regularization
- Adds penalty to loss to prevent overfitting.
- L1 → sparsity. L2 → shrinkage.

---

## One‑line summary of all terms

| Term | Meaning |
|------|---------|
| MLE | k/n, no prior |
| MAP | adds prior, point estimate |
| Full Bayes | whole posterior distribution |
| Beta | distribution for a proportion |
| Dirichlet | Beta for >2 categories |
| Sequential update | add 1 to α or β |
| Decision boundary | n=17 (Bayes) vs n=6304 (freq) |
| Multivariate Gaussian | μ, Σ, conditional formula |
| Condition number | κ = λ_max/λ_min; large → unstable |
| BN | directed, causal |
| MRF | undirected, correlational |
| GP kernel | trend + seasonal + noise |
| MCMC | sample posterior |
| NUTS | efficient HMC sampler |
| r_hat | convergence (<1.01) |
| ess | effective sample size |
| Uncertainty | posterior spread, HDI |
| L1 | sparsity |
| Log odds | ln(p/(1-p)) |
| Prior | belief before data |
| Posterior | belief after data |
| Likelihood | P(data|θ) |
| Conjugate prior | same family after update |
| Kernel | covariance function in GP |
| Length scale | smoothness in RBF |
| Periodicity | cycle length |
| Credible interval | direct probability |
| HDI | narrowest credible interval |
| Marginalization | drop variable |
| Conditional independence | independent given third |
| D‑separation | graphical independence criterion |
| Bias‑variance | tradeoff in model complexity |
| Overfitting | fits training too well |
| Regularization | penalty to avoid overfitting |

---