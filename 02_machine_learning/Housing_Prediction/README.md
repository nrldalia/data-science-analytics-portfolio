# 🏠 Housing Value Prediction

**File:** [HousingAnalysis.ipynb](./HousingAnalysis.ipynb)

### 🧠 Learning Type
Supervised Learning — Regression

### 📊 Dataset
California Housing dataset, available through scikit-learn.

### 🔍 Research Question
How effectively can median household income explain and predict median housing values?

### ⚙️ Methodology
1. Load the California Housing dataset.
2. Validate selected numerical variables.
3. Explore income and housing value distributions.
4. Split observations into training and testing datasets.
5. Train a Linear Regression model.
6. Compare model predictions against a mean baseline.
7. Evaluate MAE, MSE, RMSE, and R².
8. Visualize predictions and residuals.
9. Export evaluation results.

### 📈 Evaluation Metrics

| Metric | Purpose |
|---|---|
| MAE | Average absolute prediction error |
| MSE | Average squared prediction error |
| RMSE | Prediction error in target units |
| R² | Performance relative to predicting the test-set mean |

### ⚠️ Limitations
The model uses median income as its only predictor and is intended for educational purposes rather than actual property valuation.

---

## ▶️ Run the notebook
Open [HousingAnalysis.ipynb](./HousingAnalysis.ipynb) in Google Colab or Jupyter. Install dependencies from [requirements.txt](../requirements.txt) if running locally.

[← Back to Machine Learning & Multivariate Analysis](../README.md)
