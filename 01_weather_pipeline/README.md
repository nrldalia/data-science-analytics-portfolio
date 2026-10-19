
# Weather Analysis & Automated Reporting Pipeline

## Overview

A beginner-level Python data analysis project exploring
historical daily minimum temperatures in Melbourne,
Australia, from 1981 to 1990.

The project demonstrates data ingestion, validation,
cleaning, descriptive statistics, time-series analysis,
visualization, and automated report generation.

## Objectives

1. Analyze historical temperature observations.
2. Evaluate data quality and completeness.
3. Explore statistical distributions.
4. Investigate short-term and long-term patterns.
5. Examine monthly seasonal variation.
6. Generate reusable analytical reports.
7. Demonstrate optional email delivery.

## Technologies

- Python
- pandas
- NumPy
- Matplotlib
- seaborn
- Jupyter Notebook
- SMTP

## Dataset

Daily Minimum Temperatures in Melbourne, Australia.

Source:
https://github.com/jbrownlee/Datasets

Period: 1981–1990

Measurement: Daily minimum temperature (°C)

## Methodology

1. Data ingestion
2. Data quality assessment
3. Data cleaning and transformation
4. Descriptive statistical analysis
5. Exploratory data analysis
6. Moving-average analysis
7. Monthly seasonality analysis
8. Report generation
9. Optional email delivery
10. Basic pipeline validation

## How to Run

1. Clone or download the repository.
2. Open the project directory.
3. Install dependencies:

   pip install -r requirements.txt

4. Start Jupyter Notebook:

   jupyter notebook

5. Open WeatherAnalysis.ipynb.
6. Run all cells in sequence.

The notebook retrieves the historical CSV from
a public GitHub source, so internet access is
required during ingestion.

Generated files are saved in the outputs directory.

## Email Configuration

Email delivery is disabled by default.

To enable it, configure Gmail SMTP credentials
and set SEND_EMAIL = True in the notebook.

Do not store passwords or app passwords in GitHub.

## Analytical Findings

The project examines historical temperature
distribution, variability, rolling averages,
and recurring monthly patterns.

Detailed numerical results and charts are
generated when the notebook is executed.

Moving averages describe historical patterns
and are not temperature forecasts.

## Limitations

- Historical dataset rather than live weather data.
- No predictive machine learning model.
- No unattended scheduling.
- Email delivery requires external configuration.
- Results apply to the analyzed observation period.

## Future Improvements

- Live weather API integration
- Scheduled report execution
- Additional automated tests
- Logging and monitoring
- Multi-location analysis

## Project Level

Beginner | Python Data Analysis & Automation
