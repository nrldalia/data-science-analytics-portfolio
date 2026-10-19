# 🌤️ Weather Analysis & Automated Reporting Pipeline

**Project 01 | Beginner | Python Data Analytics & Automation**

A Python-based data analysis pipeline that explores historical weather patterns, applies descriptive statistics and time-series techniques, generates visual reports, and demonstrates optional automated email delivery.

---

## 📌 Project Overview

Weather observations provide a practical starting point for understanding how raw data can be transformed into meaningful analytical insights.

I developed this project to apply foundational Python, statistics, data cleaning, and visualization concepts to a complete analytical workflow rather than studying each technique in isolation.

The project examines daily minimum temperatures in Melbourne, Australia, from 1981 to 1990.

It demonstrates how to import and validate data, calculate summary statistics, investigate seasonal patterns, visualize moving averages, and generate reusable reports.

### 🎯 Project Objectives

- 📥 **Data Ingestion:** Retrieve historical weather observations from a public CSV source.
- 🧹 **Data Cleaning:** Identify missing values, duplicate dates, and invalid observations.
- 📊 **Descriptive Statistics:** Examine central tendency, dispersion, and distribution.
- 📈 **Time-Series Analysis:** Compare 7-day and 30-day moving averages.
- 🌦️ **Seasonality Analysis:** Explore recurring monthly temperature patterns.
- 📄 **Report Generation:** Create reusable statistical summaries and visualizations.
- 📧 **Email Automation:** Optionally send generated reports using Gmail SMTP.
- ✅ **Validation:** Confirm basic data integrity and output-file generation.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| 🐍 Python | Data processing and automation |
| 🐼 pandas | Data manipulation and time-series operations |
| 🔢 NumPy | Numerical analysis |
| 📊 Matplotlib | Time-series visualizations |
| 🎨 seaborn | Statistical charts |
| 📓 Google Colab / Jupyter | Notebook development and execution |
| 📧 Gmail SMTP | Optional email report delivery |
| 🔐 Google Colab Secrets | Secure credential configuration |

---

## 📂 Project Structure

```text
01_weather_pipeline/
│
├── WeatherAnalysis.ipynb
├── README.md
├── EMAIL_SETUP_GUIDE.md
├── requirements.txt
├── .gitignore
├── email_success.png
│
└── outputs/
    ├── cleaned_weather.csv
    ├── temperature_distribution.png
    ├── temperature_boxplot.png
    ├── daily_temperature_trend.png
    ├── moving_averages.png
    ├── monthly_seasonality.png
    ├── annual_temperature_summary.csv
    └── weather_summary_report.txt
```

The `outputs/` folder contains files generated when the notebook is executed. Depending on how the project is saved, these generated files may need to be uploaded to GitHub separately.

---

## 🗂️ Dataset Information

**Dataset:** Daily Minimum Temperatures in Melbourne, Australia

**Source:** [Daily Minimum Temperatures Dataset](https://github.com/jbrownlee/Datasets)

| Attribute | Description |
|---|---|
| Location | Melbourne, Australia |
| Period | 1981–1990 |
| Frequency | Daily |
| Target measurement | Minimum temperature |
| Unit | Degrees Celsius (°C) |
| Data format | CSV |

This is a historical dataset, not a live weather feed.

---

## 🔬 Methodology

### 1. 📥 Data Ingestion

The pipeline retrieves weather observations from a publicly accessible CSV dataset.

The expected columns are verified before processing begins.

### 2. 🧹 Data Quality Assessment

The dataset is assessed for:

- Missing temperature values
- Duplicate records and dates
- Invalid dates and numeric values
- Gaps in the daily calendar

### 3. ⚙️ Data Cleaning and Transformation

Dates are converted to datetime format, invalid records are removed, and observations are arranged chronologically.

Missing calendar days are preserved as missing values rather than assigned artificial temperatures.

### 4. 📊 Descriptive Statistics

The analysis calculates:

- Mean and median
- Standard deviation and variance
- Minimum and maximum
- Quartiles
- Skewness

These statistics describe historical variability but do not establish forecasting accuracy.

### 5. 📈 Exploratory Data Analysis

Histograms, boxplots, and time-series charts are used to examine temperature distributions and changes over time.

### 6. 🌡️ Moving Average Analysis

Two rolling averages are calculated:

- **7-day moving average:** Emphasizes shorter-term changes.
- **30-day moving average:** Provides a smoother view of longer-term patterns.

Moving averages are descriptive techniques, not prediction models.

### 7. 🌦️ Seasonal Analysis

Monthly averages are calculated to investigate recurring seasonal variation.

Annual summary statistics are also generated for year-by-year comparison.

### 8. 📄 Automated Report Generation

The notebook generates a statistical summary report and saves supporting charts.

Report generation occurs when the notebook is executed.

### 9. 📧 Optional Email Delivery

Generated reports can be sent using Gmail SMTP with TLS.

Each user must provide their own credentials through secure configuration.

### 10. ✅ Pipeline Validation

Basic assertions verify the processed data structure and check that expected output files were created.

---

## 🚀 How to Run the Project

### Option A — Google Colab (Recommended)

1. Open [`WeatherAnalysis.ipynb`](WeatherAnalysis.ipynb) on GitHub.
2. Select **Open in Colab**, if available, or open Google Colab and import the notebook from GitHub.
3. Connect to a Colab runtime.
4. Run the notebook cells from top to bottom.
5. Open the **Files** sidebar to inspect generated files.
6. Review the charts and statistical summary.

**Note:** Files saved in Colab's `/content/outputs/` directory are temporary and may disappear when the runtime resets. Configure Google Drive storage if you need persistent outputs.

### Option B — Local Jupyter Notebook

Clone the repository:

```bash
git clone https://github.com/nrldalia/data-science-analytics-portfolio.git
```

Navigate to the project directory:

```bash
cd data-science-analytics-portfolio/01_weather_pipeline
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start Jupyter:

```bash
jupyter notebook
```

Open `WeatherAnalysis.ipynb` and run the cells sequentially.

**Note:** The Gmail credential configuration shown in the Colab workflow requires adjustment for local Jupyter execution.

---

## 📧 How to Test Email Automation

The project includes an optional email reporting function.

By default:

```python
SEND_EMAIL = False
```

To enable email delivery, users must configure their own Gmail account and App Password before changing this setting to `True`.

### 🔐 Recruiter Testing Instructions

Detailed instructions are provided in:

**[📖 Gmail App Password & Email Setup Guide](EMAIL_SETUP_GUIDE.md)**

The guide explains how to:

1. Enable Google 2-Step Verification.
2. Generate a Gmail App Password.
3. Configure Google Colab Secrets.
4. Enable the email delivery function.
5. Verify the received report and attachments.
6. Troubleshoot common SMTP issues.

No passwords or private credentials are included in this repository.

---

## 📊 Analytical Outputs

The pipeline produces several visual and tabular outputs.

| Output | Description |
|---|---|
| 📊 Temperature Distribution | Histogram and density visualization |
| 📦 Temperature Boxplot | Median, quartiles, and potential outliers |
| 📈 Daily Temperature Trend | Historical daily observations |
| 🌡️ Moving Averages | Comparison of 7-day and 30-day trends |
| 🌦️ Monthly Seasonality | Average temperature by calendar month |
| 📋 Annual Summary | Yearly descriptive statistics |
| 📄 Statistical Report | Generated analytical summary |

### 🔍 Interpretation

The analysis examines how temperature values are distributed, how much they vary, and whether seasonal patterns can be observed.

The 7-day moving average retains more short-term variation, while the 30-day moving average provides greater smoothing.

Monthly aggregation is used to investigate differences between warmer and cooler parts of the year.

Detailed statistics and plots are available in the executed notebook.

---

## ⚠️ Project Limitations

- The dataset contains historical observations from 1981–1990.
- The pipeline does not retrieve current weather conditions.
- Moving averages do not provide temperature forecasts.
- Descriptive statistics alone cannot establish predictability.
- Email delivery requires valid user credentials.
- The notebook does not implement unattended scheduling.
- The analysis is limited to the selected location and observation period.

---

## 🎓 Skills Demonstrated

**Data Analytics:** Data cleaning, statistical analysis, exploratory visualization, and time-series aggregation.

**Python Programming:** pandas, NumPy, functions, file handling, and basic error handling.

**Automation:** Programmatic report generation and optional SMTP delivery.

**Documentation:** Methodology, assumptions, limitations, reproducibility, and testing instructions.

---

## 🏁 Conclusion

This project demonstrates how historical weather data can be transformed into structured analytical outputs through a reproducible Python workflow.

It combines foundational statistical techniques with practical reporting automation, providing an introductory example of end-to-end data analysis.

**Project Level:** Beginner  
**Primary Focus:** Python Data Analytics, Statistics & Automation  
**Development Environment:** Google Colab / Jupyter Notebook
