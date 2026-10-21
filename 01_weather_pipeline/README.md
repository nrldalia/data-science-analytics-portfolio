# 🌤️ Automated Weather Intelligence Pipeline

**Project 01 | Python · Data Analytics · API Integration · Reporting Automation**

This folder brings together **two independent weather-data workflows** that demonstrate the progression from exploratory time-series analysis to API-based collection, data validation and automated reporting. The project uses weather data as a practical context for developing reusable Python data skills.

## 🗂️ Explore the Projects

| Project | Focus | Notebook |
| :--- | :--- | :--- |
| [🌏 Melbourne Historical Weather Analytics](./Melbourne/README.md) | Historical temperature analysis, descriptive statistics, moving averages and seasonality | [WeatherAnalysis.ipynb](./WeatherAnalysis.ipynb) |
| [🇲🇾 METMalaysia API & Automated Reporting](./METMalaysia/README.md) | Authenticated API ingestion, pagination, data validation, geographic mapping, CSV/charts/PDF reports and optional SMTP delivery | [METMalaysia_Weather.ipynb](./METMalaysia_Weather.ipynb) |

## 🧠 Skills Demonstrated

- **Data analytics:** Cleaning, descriptive statistics, time-series trends, and visualisation
- **Data engineering fundamentals:** API requests, JSON processing, pagination, rate-limit handling, and data-quality checks
- **Reporting automation:** Reproducible outputs, PDF reporting and optional email delivery
- **Analytical judgement:** Validating assumptions, reporting missing geographic mappings and documenting limitations

## 📁 Supporting Files

The two notebooks remain at the root of this folder to **preserve existing notebook links**. Each project has its own dedicated README in a subfolder.

- [EMAIL_SETUP_GUIDE.md](./EMAIL_SETUP_GUIDE.md) — Optional email configuration
- [requirements.txt](./requirements.txt) — Python dependencies
- Other existing images and generated outputs are retained in their original locations

**Scope:** The Melbourne project analyses historical temperatures. The METMalaysia project analyses published forecasts; it does not independently predict weather. Email delivery is optional and unattended scheduling has not yet been implemented.

## 🚧 Potential Enhancements

Improve clean-run reproducibility, implement scheduling, strengthen data freshness checks and explore an interactive weather explorer. These are future improvements, not completed features.

[← Back to the main portfolio](../README.md)
