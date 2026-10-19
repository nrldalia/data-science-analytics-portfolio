# 🤖 Machine Learning & Multivariate Analysis

**Project 02 | Beginner | Supervised & Unsupervised Learning**

## 📌 Project Overview

This project introduces two fundamental machine learning approaches using Python and scikit-learn.

The first notebook demonstrates **supervised learning** through housing value prediction using Linear Regression.

The second notebook demonstrates **unsupervised learning** through synthetic retail customer segmentation using K-Means Clustering.

Both projects follow structured analytical workflows, including data preparation, exploratory analysis, model development, evaluation, visualization, and documentation.

---

## 🎯 Project Objectives

- Understand supervised and unsupervised machine learning.
- Prepare numerical data for model development.
- Train and evaluate a Linear Regression model.
- Apply feature scaling and K-Means Clustering.
- Interpret model outputs using appropriate metrics.
- Translate analytical results into understandable conclusions.
- Document assumptions, limitations, and potential improvements.

---

## 📂 Repository Structure

```text
02_machine_learning/
│
├── HousingAnalysis.ipynb
├── CustomerRetailAnalysis.ipynb
├── README.md
├── requirements.txt
│
└── outputs/
    ├── housing/
    │   ├── housing_distributions.png
    │   ├── income_vs_housing.png
    │   ├── regression_prediction.png
    │   ├── regression_residuals.png
    │   ├── housing_predictions.csv
    │   └── housing_model_metrics.csv
    │
    └── customer_segmentation/
        ├── customer_distribution.png
        ├── cluster_evaluation.png
        ├── customer_clusters.png
        ├── customer_clusters.csv
        ├── cluster_profiles.csv
        └── cluster_evaluation.csv
```

The `outputs/` folder is generated when the notebooks are executed. Generated files are not automatically committed to GitHub.

---

## 🏠 Notebook 1 — Housing Value Prediction

**File:** [HousingAnalysis.ipynb](HousingAnalysis.ipynb)

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

## 🛍️ Notebook 2 — Customer Segmentation

**File:** [CustomerRetailAnalysis.ipynb](CustomerRetailAnalysis.ipynb)

### 🧠 Learning Type
Unsupervised Learning — Clustering

### 📊 Dataset
Reproducible synthetic customer records generated with NumPy.

### 🔍 Research Question
Can customers be grouped according to similarities in annual income and spending score?

### ⚙️ Methodology
1. Generate synthetic customer records.
2. Validate the dataset.
3. Explore income and spending patterns.
4. Standardize features using StandardScaler.
5. Compare candidate cluster counts.
6. Train a K-Means model.
7. Visualize clusters and centroids.
8. Generate numerical customer segment profiles.
9. Discuss possible business applications.
10. Export cluster assignments and evaluation results.

### 📏 Evaluation Methods

| Method | Purpose |
|---|---|
| Inertia | Measures within-cluster squared distances |
| Silhouette Score | Evaluates cohesion and separation |
| Cluster Profiles | Describes group characteristics |
| Centroid Analysis | Identifies representative cluster centers |

### ⚠️ Limitations
The dataset is synthetic and intentionally structured for demonstration.

The resulting clusters do not represent verified customer behavior or validated marketing segments.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| 🐍 Python | Programming |
| 🐼 pandas | Data manipulation |
| 🔢 NumPy | Numerical processing and synthetic data |
| 📊 Matplotlib | Visualization |
| 🎨 seaborn | Statistical visualization |
| 🤖 scikit-learn | Regression, clustering, and evaluation |
| 📓 Google Colab | Notebook execution |

---

## 🚀 Running the Projects

### Option A — Google Colab

1. Open either notebook from this repository.
2. Select **Open in Colab**, if available, or import the notebook through Colab's GitHub option.
3. Connect to a runtime.
4. Run all cells sequentially.
5. Inspect the generated charts, tables, and exported files.

Generated outputs are stored in the Colab runtime unless a persistent Google Drive directory is configured.

### Option B — Local Jupyter

Clone the repository:

```bash
git clone https://github.com/nrldalia/data-science-analytics-portfolio.git
```

Navigate to the project folder:

```bash
cd data-science-analytics-portfolio/02_machine_learning
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Launch Jupyter:

```bash
jupyter notebook
```

Open the notebook you wish to run.

**Note:** The California Housing dataset may require an internet connection on first retrieval.

---

## 🎓 Skills Demonstrated

**Data Preparation:** Validation, feature selection, and standardization.

**Supervised Learning:** Regression modeling, train/test splitting, baseline comparison, and error metrics.

**Unsupervised Learning:** K-Means, cluster evaluation, centroid interpretation, and segmentation.

**Data Visualization:** Distributions, regression relationships, residuals, and cluster plots.

**Documentation:** Research questions, hypotheses, methodological choices, findings, and limitations.

---

## 🏁 Conclusion

Project 02 demonstrates the distinction between predicting a known target and discovering groups in unlabeled data.

The two notebooks introduce essential machine learning workflows while emphasizing appropriate evaluation, transparent assumptions, and responsible interpretation.

**Project Level:** Beginner  
**Primary Focus:** Machine Learning Fundamentals  
**Algorithms:** Linear Regression & K-Means Clustering  
**Environment:** Google Colab / Jupyter Notebook
