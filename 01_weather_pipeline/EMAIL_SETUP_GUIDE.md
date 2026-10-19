# Gmail App Password Setup Guide

## Weather Analysis & Automated Reporting Pipeline

### 1. Purpose

This guide explains how to configure and test the optional Gmail email reporting functionality in the Weather Analysis Pipeline.

The pipeline generates a statistical report and a moving-average chart from historical weather observations. Users can optionally send these outputs to an email address through Gmail SMTP.

**Important:** Email delivery is disabled by default. Each user must configure their own Gmail credentials before testing the functionality.

---

## 2. Prerequisites

Before testing email delivery, ensure you have:

- A Google account with Gmail access.
- Google Colab access.
- 2-Step Verification enabled on your Google account.
- A Gmail App Password, if supported by your account.
- Successfully executed the weather analysis notebook to generate the report and chart.

No credentials are included in this repository.

## 3. Enable Google 2-Step Verification

1. Visit [Google Account Security](https://myaccount.google.com/security).
2. Sign in to your Google account.
3. Locate **2-Step Verification**.
4. Follow Google's instructions to enable it, if necessary.

2-Step Verification is generally required to generate an App Password.

## 4. Generate a Gmail App Password

1. Open [Google App Passwords](https://myaccount.google.com/apppasswords).
2. Sign in to your Google account.
3. Enter an application name, such as `Weather Analysis Pipeline`.
4. Select **Create**.
5. Copy the generated 16-character App Password.
6. Store it securely.

**Security notice:** Do not use your regular Gmail password in the Python script. Do not commit App Passwords to GitHub.

App Passwords may not be available for certain accounts, including some organization-managed accounts or accounts with Advanced Protection enabled.

## 5. Configure Google Colab Secrets

The project uses Google Colab Secrets to avoid storing credentials directly in notebook source code.

1. Open `WeatherAnalysis.ipynb` in Google Colab.
2. Locate the **Secrets** icon (key symbol) in the left sidebar.
3. Add the following secrets:

| Secret Name | Description |
|---|---|
| `WEATHER_SENDER_EMAIL` | Gmail address used to send the report |
| `WEATHER_RECEIVER_EMAIL` | Email address receiving the report |
| `WEATHER_EMAIL_APP_PASSWORD` | Gmail App Password generated in Step 4 |

4. Enable **Notebook access** for all three secrets.

Example values:

- `WEATHER_SENDER_EMAIL`: `example@gmail.com`
- `WEATHER_RECEIVER_EMAIL`: `recipient@example.com`
- `WEATHER_EMAIL_APP_PASSWORD`: Your private App Password

These are examples only. Use your own credentials when testing.

## 6. Load Credentials in the Notebook

Locate the email configuration cell and use the following code:

```python
from google.colab import userdata

sender_email = userdata.get("WEATHER_SENDER_EMAIL")
receiver_email = userdata.get("WEATHER_RECEIVER_EMAIL")
app_password = userdata.get("WEATHER_EMAIL_APP_PASSWORD")

print("Email configuration loaded successfully.")
```

This retrieves credentials from Colab Secrets without exposing them in the notebook source.

## 7. Generate the Report Files

Run the notebook's analysis and report-generation cells before testing email delivery.

Confirm that the following files exist:

```text
outputs/
├── weather_summary_report.txt
└── moving_averages.png
```

Both files are required by the email delivery function.

## 8. Enable Email Delivery

In the email delivery cell, locate:

```python
SEND_EMAIL = False
```

Change it to:

```python
SEND_EMAIL = True
```

Run the cell to send the report.

The script will connect to Gmail SMTP using TLS and attach the generated report and chart.

## 9. Verify Successful Delivery

After execution:

1. Check the Colab output for `Email report sent successfully!`.
2. Open the recipient's email inbox.
3. Locate the email with the subject:

   **Weather Analysis - Historical Temperature Report**

4. Confirm that the following attachments are present:
   - `weather_summary_report.txt`
   - `moving_averages.png`

5. Open the attachments to verify their contents.

**Note:** A successful SMTP response indicates that Gmail accepted the message for delivery. It does not guarantee arrival in the recipient's inbox. Check the spam folder if necessary.

## 10. Troubleshooting

| Issue | Possible Cause | Suggested Action |
|---|---|---|
| Authentication failed | Incorrect App Password | Generate a new App Password and update Colab Secrets |
| Secret not found | Incorrect secret name or access disabled | Verify spelling and enable Notebook access |
| Missing attachment | Report generation cells were not executed | Run the notebook's preceding cells |
| Connection timeout | Network or SMTP connectivity issue | Retry and verify network access |
| Email not received | Spam filtering or delivery delay | Check spam and recipient address |
| App Password unavailable | Google account security restrictions | Check account eligibility and Google security settings |

## 11. Security Best Practices

- Never commit Gmail credentials or App Passwords to GitHub.
- Never print App Passwords in notebook outputs.
- Use Google Colab Secrets for credential management.
- Disable email delivery after testing if it is no longer needed.
- Revoke unused App Passwords from your Google Account security settings.

## 12. Project Limitations

This project demonstrates email report delivery, not a fully scheduled production email service.

The email is sent only when the relevant notebook cell is executed with valid credentials.

The weather dataset is historical, so rerunning the notebook does not automatically produce new current-weather observations.

## 13. Expected Testing Outcome

A successful test demonstrates that the project can:

1. Generate analytical outputs.
2. Prepare report attachments.
3. Authenticate with Gmail SMTP.
4. Submit an email containing the generated report and visualization.

This verifies the optional email delivery component of the Weather Analysis Pipeline.

---

**Project:** Weather Analysis & Automated Reporting Pipeline  
**Level:** Beginner  
**Environment:** Google Colab  
**Email Service:** Gmail SMTP  
**Authentication:** Gmail App Password via Colab Secrets