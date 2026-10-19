# 🌤️ Weather Analytics & Automated Reporting Pipeline

**Project 01 | Python Data Analytics · API Integration · Automation**

> From historical weather exploration to a Malaysia-wide forecast reporting pipeline powered by the METMalaysia API.

## 📌 Project Overview

This project demonstrates the development of Python-based weather analytics and automated reporting through two complementary workflows.

**🌏 Part 1 — Historical Weather Analytics (Melbourne, Australia)**

An introductory data analytics project exploring historical daily minimum temperatures from 1981 to 1990, using data cleaning, descriptive statistics, time-series analysis, and visual reporting.

**🇲🇾 Part 2 — METMalaysia Weather API Integration & Automated Reporting**

An enhanced pipeline that retrieves Malaysian weather forecasts through the METMalaysia API, validates the data, investigates geographic relationships, produces analytical reports, generates PDF visualisations, and supports email delivery.

The second workflow represents an extension of the original project from exploratory analysis into API integration, data quality management, and practical reporting automation.

---

## 🗂️ Project Structure

```text
01_weather_pipeline/
│
├── WeatherAnalysis.ipynb
├── METMalaysia_Weather.ipynb
├── README.md
├── EMAIL_SETUP_GUIDE.md
├── requirements.txt
├── .gitignore
├── email_success.png
└── output_content/
```

| Notebook | Description |
|---|---|
| [🌏 WeatherAnalysis.ipynb](WeatherAnalysis.ipynb) | Melbourne historical weather analytics |
| [🇲🇾 METMalaysia_Weather.ipynb](METMalaysia_Weather.ipynb) | Malaysian weather forecast API integration and automated reporting |

---

# 🇲🇾 Part 2 — METMalaysia Weather API & Automated Reporting

## 🎯 Project Objectives

The objective is to build a reproducible weather-data reporting workflow that:

1. Retrieves Malaysian forecast data from an authenticated API.
2. Handles pagination, request failures, and API rate limits.
3. Validates and transforms raw forecast records.
4. Investigates geographic hierarchy relationships across Malaysian locations.
5. Produces national and state-level descriptive summaries.
6. Automatically generates CSV reports, charts, and a PDF report.
7. Supports optional report delivery through Gmail SMTP.

**Project scope:** The pipeline analyses published forecasts. It does not train a weather prediction model or independently forecast future temperatures.

## 📊 Data Collection Results

The following results were obtained from the project run covering the forecast date **19 October 2026**.

| Metric | Result |
|---|---:|
| Forecast records collected | 12,390 |
| Distinct forecast locations | 2,065 |
| Complete forecast datatype coverage | 2,065 locations |
| Duplicate forecast keys | 0 |
| Non-numeric temperature records | 0 |
| Locations mapped to a state ancestor | 1,980 |
| Geographic mapping coverage | 95.88% |
| Unmapped forecast locations | 85 |

These figures describe a collected forecast snapshot. Future API responses may contain different numbers of locations, forecast dates, or values.

## 🔄 Pipeline Architecture

```text
        METMalaysia Weather API
                  |
                  v
       Authenticated API Requests
                  |
                  v
      Paginated Forecast Collection
                  |
                  v
       Validation & Data Cleaning
                  |
                  v
      Geographic Hierarchy Mapping
                  |
                  v
       Exploratory Data Analysis
                  |
                  v
      Automated Report Generation
          /       |        \
         v        v         v
       CSV      Charts      PDF
                            |
                            v
                   Gmail SMTP Delivery
```

## 🧪 Data Validation & Quality Assurance

The pipeline performs structural checks before producing analytical summaries.

Validation includes:

- Required column and forecast datatype checks.
- Duplicate detection using location, forecast date, and datatype.
- Numeric validation of forecast maximum and minimum temperatures.
- Temperature consistency checks.
- Geographic identifier matching.
- Parent-location hierarchy resolution.
- Identification of locations without verified state mappings.

For the analysed forecast snapshot, all 2,065 collected locations contained the six expected forecast datatypes.

These checks establish structural consistency, not meteorological forecast accuracy.

## 🗺️ Malaysian Geographic Mapping

One of the project's challenges was identifying reliable geographic relationships between forecast locations and Malaysian states.

Initial attempts to match state-level location identifiers revealed that some API resources used different identifiers for similarly named places.

Further investigation identified the `locationrootid` field in the METMalaysia location catalogue, allowing parent-location relationships to be traced.

### Geographic Mapping Results

| Indicator | Result |
|---|---:|
| Catalogue locations examined | 2,823 |
| Locations resolved to state ancestors | 2,654 |
| Unresolved catalogue locations | 169 |
| Forecast locations mapped to state ancestors | 1,980 |
| Forecast locations remaining unmapped | 85 |
| Kuala Lumpur-associated forecast locations | 28 |

Of the 85 unmapped forecast locations, 67 had unresolved catalogue hierarchies and 18 had forecast identifiers absent from the retrieved catalogue.

**Important limitation:** Geographic assignments reflect the hierarchy published by METMalaysia. They are not independently verified administrative boundaries. Locations without a resolved assignment are retained under `Unmapped` rather than being assigned to a state based on name similarity.

## 📈 National Forecast Analysis

For the 19 October 2026 snapshot, the location-level forecast statistics were:

| Temperature metric | Minimum | Mean | Maximum |
|---|---:|---:|---:|
| Forecast daily maximum (°C) | 24.00 | 32.92 | 34.00 |
| Forecast daily minimum (°C) | 12.00 | 23.73 | 25.00 |
| Forecast temperature spread (°C) | 6.00 | 9.19 | 18.00 |

The temperature spread is calculated as the forecast daily maximum minus the forecast daily minimum for each location. It is not a measure of forecast uncertainty.

National and state-level averages are unweighted across forecast locations, rather than population-weighted or area-weighted estimates.

## 📄 Automated Reporting Outputs

The reporting workflow generates the following files when executed in Google Colab.

```text
metmalaysia_outputs/
└── automated_reports/
    ├── location_forecasts.csv
    ├── national_temperature_summary.csv
    ├── state_temperature_summary.csv
    ├── state_weather_frequency.csv
    ├── malaysia_weather_report.txt
    ├── malaysia_weather_forecast_report.pdf
    └── charts/
        ├── state_temperature_comparison.png
        ├── significant_weather_distribution.png
        └── geographic_mapping_coverage.png
```

The PDF report includes an executive summary, temperature statistics, state-level comparisons, weather-category visualisations, geographic mapping coverage, and analytical limitations.

These outputs are generated during notebook execution and are not necessarily committed to the repository.

## 📧 Automated Email Delivery

The pipeline supports sending the generated weather report through Gmail SMTP.

The email workflow:

1. Loads the generated report files.
2. Creates an email with the forecast date and summary.
3. Attaches the PDF report and a CSV summary.
4. Requests confirmation before sending.
5. Submits the email through Gmail SMTP.

Credentials are supplied privately at runtime and must not be committed to the repository.

**Automation scope:** Report generation and email delivery are executable through the notebook. Fully unattended recurring execution and scheduling are not yet implemented.

## 🛠️ Technical Challenges & Lessons Learned

| Challenge | Investigation and resolution |
|---|---|
| HTTP 401 authentication errors | Tested API endpoints and corrected authentication or request configuration |
| HTTP 429 rate-limit responses | Introduced request pacing, cooldown handling, and collection recovery |
| Pagination and overlapping results | Investigated pagination boundaries and preserved collected records |
| Duplicate state names and identifiers | Standardised Federal Territory aliases while preserving original API identifiers |
| Missing geographic parent references | Traced available hierarchy relationships and quantified unresolved mappings |
| Report reproducibility | Separated collection, validation, analysis, report generation, and delivery into documented stages |

These challenges highlighted the importance of validating assumptions, preserving intermediate outputs, and explicitly documenting incomplete data coverage.

---

## ▶️ How to Run the METMalaysia Notebook

### Requirements

- Python environment or Google Colab.
- Authorised METMalaysia API token.
- Internet access for API retrieval.
- Required Python libraries.
- Optional Gmail account and App Password for email delivery.

### Instructions

1. Open [METMalaysia_Weather.ipynb](METMalaysia_Weather.ipynb) in Google Colab.
2. Obtain your own METMalaysia API token through the [METMalaysia API documentation](https://metapi2.met.gov.my/docs).
3. Configure the notebook's API authentication using your own credentials.
4. Execute the collection and validation stages in sequence.
5. Review the geographic mapping results and unresolved location counts.
6. Run the analytical reporting and visualisation stages.
7. Generate the PDF report.
8. Optionally configure Gmail SMTP and confirm email delivery.

### 🔐 Security Notes

Never commit API tokens, Gmail App Passwords, `.env` files containing secrets, or private credentials.

Review both notebook code cells and saved cell outputs before publishing.

### ⚠️ Reproducibility Notes

The notebook was developed incrementally in Google Colab. Review the execution order and required intermediate files before running it from a fresh runtime.

API availability, response structure, forecast dates, and rate limits may change. The original forecast snapshot may therefore not be reproduced exactly.

---

# 🌏 Part 1 — Melbourne Historical Weather Analytics

## 📌 Overview

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

For email configuration, see [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md).

---

## 💻 Technologies & Skills

**Programming and analysis:** Python, pandas, NumPy, Matplotlib, seaborn, descriptive statistics, and time-series analysis.

**API and data engineering:** Authenticated HTTP requests, JSON processing, pagination, rate-limit handling, checkpoint recovery, data validation, and geographic reference mapping.

**Reporting and automation:** CSV generation, Matplotlib charts, ReportLab PDF generation, Gmail SMTP, and Google Colab.

**Analytical practices:** Data-quality assessment, critical evaluation of assumptions, documentation of limitations, and reproducible reporting.

---

## 🚧 Future Enhancements

- Improve clean-run reproducibility and dependency management.
- Add automated data freshness checks.
- Strengthen geographic mapping using authoritative reference data.
- Implement unattended scheduling in a suitable execution environment.
- Develop an interactive Malaysia Weather Forecast Explorer.

These are planned improvements, not completed functionality.

---

## 🎓 Project Reflection

This project began as a beginner-level exercise in historical weather analysis and gradually evolved into a more comprehensive data analytics and automation workflow.

The development process reinforced the importance of understanding data structures, validating API responses, investigating unexpected results, and documenting technical limitations.

Rather than focusing only on producing charts, the enhanced project emphasises how raw data can be collected, evaluated, transformed, and delivered as practical reporting outputs.

**Project repository:** [Data Science & Analytics Portfolio](https://github.com/nrldalia/data-science-analytics-portfolio)

**Focus:** Continuous learning in Python, data analytics, data engineering fundamentals, and practical automation.
