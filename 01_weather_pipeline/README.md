# 🌤️ Weather Analysis & Automated Reporting Pipeline

## Why This Notebook Was Created
I created this project to transition from static university statistical theory into an end-to-end automated data pipeline. 
Instead of just calculating mean, variance, and skewness on paper, this script processes actual time-series weather records, 
smooths out daily volatility using 7-day and 30-day moving averages, and packages the results into an automated email report.

## What's Inside
* `weather_analysis.ipynb`: Handles data cleaning, statistical distribution profiling, and trend visualization.
* `automated_email_report.py`: Programmatically generates chart images and sends secure email updates using Python's `smtplib`.
* `image.png` : A screenshot of the successful email update in Gmail.
