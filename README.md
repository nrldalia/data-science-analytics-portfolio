# 🌤️ Automated Weather Analysis & Email Reporting Process

An end-to-end Python data science and engineering project that automates data ingestion, exploratory data analysis (EDA), statistical distribution profiling, time-series trend calculation, and scheduled email report generation.

---

## 🚀 Project Overview
The goal of this project is to bridge raw time-series data and actionable insights without manual intervention. It simulates a complete automated workflow:
1. **Data Ingestion & Cleaning:** Processes local weather records, handling missing values and date-time indexing.
2. **Exploratory Data Analysis (EDA):** Computes descriptive statistics (mean, median, standard deviation, and skewness) to understand temperature distributions and volatility.
3. **Time-Series Analysis:** Calculates 7-day and 30-day moving averages to smooth out daily noise and reveal seasonal trends.
4. **Automated Reporting:** Generates a high-resolution trend chart using Matplotlib and automatically emails a statistical summary report with the chart attached using Python's `smtplib`.

---

## 🛠️ Tech Stack & Libraries
* **Programming Language:** Python
* **Data Manipulation & Analysis:** Pandas, NumPy
* **Data Visualization:** Matplotlib, Seaborn
* **Automation & Networking:** `smtplib`, `email.mime`
* **Environment:** Jupyter Notebook / Anaconda

---

## 📊 Key Visualizations & Insights

### Time-Series Moving Averages
<img width="1298" height="542" alt="image" src="https://github.com/user-attachments/assets/14281abd-a545-4829-9f07-07604d02639e" />

* **Observation:** The 7-day moving average captures short-term fluctuations, while the 30-day moving average highlights broader seasonal shifts in local weather patterns.

---

## ⚙️ How to Run This Project

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/nrldalia/weather-analysis-automate.git](https://github.com/your-username/your-repo-name.git)
