# Running Data Visualisation

Personal running analytics system that extracts training data from **Garmin Connect** and generates professional statistical visualizations. Built for long-term performance analysis spanning multiple years of training sessions.

**Author:** Raul Hernandez Lopez  
**License:** [CC BY-SA 4.0](LICENSE)

---

## Overview

The project is split into two independent scripts:

| Script | Purpose |
|--------|---------|
| `extractor.py` | Authenticates with Garmin Connect and downloads all running activity data to a CSV file |
| `running_data_analysis.py` | Reads the CSV and generates 10 SVG visualizations covering performance, trends, and correlations |

---

## Requirements

### Python version

Python **3.10+** is required. The project was developed and tested with Python 3.13.

### Dependencies

Install all dependencies using:

```bash
pip install -r requirements.txt
```

Create a `requirements.txt` with the following content (or install manually):

```
garminconnect>=0.2.38
garth>=0.5.21
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
seaborn>=0.12
python-dateutil>=2.8
requests-oauthlib>=1.3
```

### Recommended: virtual environment

```bash
python -m venv env_garmin
source env_garmin/bin/activate        # macOS / Linux
env_garmin\Scripts\activate           # Windows
pip install -r requirements.txt
```

---

## Configuration

### 1. Create a `.env` file

Copy the template below and fill in your Garmin credentials:

```ini
GARMIN_EMAIL=your_garmin_email@example.com
GARMIN_PASSWORD=your_garmin_password

# Optional — defaults shown
GARMIN_TOKENSTORE_DIR=.garmin_tokens
GARMIN_MAX_LOGIN_RETRIES=4
GARMIN_ACTIVITIES_PAGE_SIZE=1000
GARMIN_OUTPUT_CSV=running_dataset.csv
```

The `.env` file is excluded from version control. Never commit it.

### 2. Environment variables reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GARMIN_EMAIL` | *(required)* | Garmin Connect account email |
| `GARMIN_PASSWORD` | *(required)* | Garmin Connect account password |
| `GARMIN_TOKENSTORE_DIR` | `.garmin_tokens` | Directory where session tokens are cached |
| `GARMIN_MAX_LOGIN_RETRIES` | `4` | Max retries on rate-limiting (HTTP 429) |
| `GARMIN_ACTIVITIES_PAGE_SIZE` | `1000` | Records fetched per API request |
| `GARMIN_OUTPUT_CSV` | `running_dataset.csv` | Output CSV filename |

---

## Usage

### Step 1 — Extract data from Garmin Connect

```bash
python extractor.py
```

On first run, the script authenticates with Garmin Connect and saves session tokens to `.garmin_tokens/`. Subsequent runs reuse the cached tokens to avoid repeated logins.

The script will:
1. Authenticate using credentials from `.env`
2. Fetch all running activities (with automatic pagination)
3. Filter for `typeKey == "running"` sessions only
4. Export 15 metrics per session to `running_dataset.csv`

**Output:** `running_dataset.csv` — one row per session.

#### CSV columns

| Column | Unit | Description |
|--------|------|-------------|
| `startTimeLocal` | YYYY-MM-DD HH:MM:SS | Session start time |
| `distance` | meters | Total distance |
| `duration` | seconds | Total elapsed time |
| `movingDuration` | seconds | Active moving time |
| `averageSpeed` | m/s | Average speed |
| `averageHR` | bpm | Average heart rate |
| `maxHR` | bpm | Maximum heart rate |
| `avgStrideLength` | meters | Average stride length |
| `averageRunningCadenceInStepsPerMinute` | steps/min | Average cadence |
| `maxRunningCadenceInStepsPerMinute` | steps/min | Maximum cadence |
| `elevationGain` | meters | Positive elevation change |
| `elevationLoss` | meters | Negative elevation change |
| `calories` | kcal | Energy expenditure |
| `vO2MaxValue` | mL/kg/min | VO2 max estimate (may be NaN for older data) |
| `steps` | count | Total steps |

---

### Step 2 — Generate visualizations

```bash
python running_data_analysis.py
```

Reads `running_dataset.csv` and writes 10 SVG charts to `graphics_svg/`.

#### Filtering applied

- Sessions shorter than **0.5 km** or **2 minutes** are excluded (GPS warm-up artefacts)
- Monthly pace charts require **≥ 4 sessions** per month to be plotted

#### Output charts

| File | Chart type | Content |
|------|-----------|---------|
| `01_barras_km_anual.svg` | Bar chart | Total kilometres per year |
| `02_lineas_ritmo_mensual.svg` | Line chart | Monthly pace with 6-month moving average |
| `03_histograma_distancias.svg` | Histogram + KDE | Distribution of session distances |
| `04_dispersion_ritmo_hr.svg` | Scatter + regression | Heart rate vs pace |
| `05_boxplot_ritmo_anual.svg` | Box-and-whisker | Pace distribution per year |
| `06_vo2max_anual.svg` | Line + error bars | Annual VO2 max trend (mean ± std dev) |
| `07_sesiones_dia_semana.svg` | Bar chart | Session count by day of week |
| `08_desnivel_trimestre.svg` | Violin plot | Elevation gain distribution per quarter |
| `09_correlaciones.svg` | Heatmap | Correlation matrix (7 metrics) |
| `10_pairplot_multivariable.svg` | Pairplot | Multivariate analysis: distance, pace, HR, cadence |

The script also prints a summary to stdout:

```
Total sessions: 1884
Years: 2013 – 2025
Total km: 14,237.4
Average pace: 5:32 /km
```

---

## Project structure

```
running-data-visualisation/
├── extractor.py              # Garmin Connect data extraction
├── running_data_analysis.py  # Analysis and visualizations
├── running_dataset.csv       # Exported data (git-ignored)
├── graphics_svg/             # Generated SVGs (git-ignored)
│   ├── 01_barras_km_anual.svg
│   ├── 02_lineas_ritmo_mensual.svg
│   └── ...
├── .env                      # Credentials — never commit (git-ignored)
├── .garmin_tokens/           # Cached auth tokens (git-ignored)
├── requirements.txt          # Python dependencies
└── LICENSE
```

---

## Authentication notes

- Garmin Connect uses OAuth. Tokens are stored locally in `.garmin_tokens/` and reused across runs.
- If authentication fails due to rate limiting, the script retries with exponential backoff up to `GARMIN_MAX_LOGIN_RETRIES` attempts.
- MFA / two-factor authentication on Garmin Connect may interfere with automated login. Disable it or use an app-specific session if needed.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'garminconnect'`**  
Activate the virtual environment before running:
```bash
source env_garmin/bin/activate
```

**`LoginError` or HTTP 429**  
Garmin rate-limits repeated login attempts. Wait a few minutes and retry, or increase `GARMIN_MAX_LOGIN_RETRIES` in `.env`.

**Empty CSV / no activities exported**  
Ensure the `.env` credentials are correct and that the account has running activities recorded on Garmin Connect.

**SVG charts not generated**  
Check that `running_dataset.csv` exists and contains data. Run `extractor.py` first.

---

## License

[Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](LICENSE)  
© 2026 Raul Hernandez Lopez
