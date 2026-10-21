# 🌏 Melbourne Historical Weather Analytics

## 📌 Overview

**Notebook:** [WeatherAnalysis.ipynb](./WeatherAnalysis.ipynb)


The original workflow analyses historical daily minimum temperatures in Melbourne, Australia, from 1981 to 1990.

**Dataset:** Public Daily Minimum Temperatures dataset, available from the [Brownlee Datasets repository](https://github.com/jbrownlee/Datasets).

## 🔍 Analytical Workflow

1. Import and validate the historical dataset.
2. Inspect missing values, duplicate dates, and invalid records.
3. Calculate descriptive temperature statistics.
4. Visualise temperature distributions and daily trends.
5. Calculate 7-day and 30-day moving averages.
6. Investigate monthly seasonality and annual summaries.
7. Generate reusable analytical outputs.
8. Optionally deliver reports through Gmail SMTP.

Moving averages are used for descriptive smoothing, not as a predictive weather model.

## 📁 Original Workflow Outputs

The notebook can generate:

- `cleaned_weather.csv`
- `temperature_distribution.png`
- `temperature_boxplot.png`
- `daily_temperature_trend.png`
- `moving_averages.png`
- `monthly_seasonality.png`
- `annual_temperature_summary.csv`
- `weather_summary_report.txt`

For email configuration, see [EMAIL_SETUP_GUIDE.md](../EMAIL_SETUP_GUIDE.md).

---


## 🛠️ Technologies
Python, pandas, NumPy, Matplotlib, seaborn, and Google Colab / Jupyter Notebook.

**Note:** The analysis is descriptive; moving averages smooth historical temperature data and are not forecasts.

[← Back to Automated Weather Intelligence Pipeline](../README.md)
