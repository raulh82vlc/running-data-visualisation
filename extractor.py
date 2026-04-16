# Copyright (c) 2026 Raul Hernandez Lopez
#
# This file is part of the project and is licensed under the
# Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0).
#
# You are free to share and adapt this file under the terms of the CC BY-SA 4.0 license.
# Full license: https://creativecommons.org/licenses/by-sa/4.0/legalcode
#
# @author: Raul Hernandez Lopez

# Extracción de datos de Garmin Connect para corredores

import os
import time
import pandas as pd
import garth
from garminconnect import Garmin
"""
Extraccion de datos de running - Garmin Connect
Visualización de datos
@Author: Raul Hernandez
"""

def load_env_file(env_path: str = ".env") -> None:
    if not os.path.isfile(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file()

EMAIL = os.getenv("GARMIN_EMAIL")
PASSWORD = os.getenv("GARMIN_PASSWORD")
TOKENSTORE_DIR = os.getenv("GARMIN_TOKENSTORE_DIR", ".garmin_tokens")
MAX_LOGIN_RETRIES = int(os.getenv("GARMIN_MAX_LOGIN_RETRIES", "4"))
ACTIVITIES_PAGE_SIZE = int(os.getenv("GARMIN_ACTIVITIES_PAGE_SIZE", "1000"))
OUTPUT_CSV = os.getenv("GARMIN_OUTPUT_CSV", "running_dataset.csv")

if not EMAIL or not PASSWORD:
    raise ValueError("Missing GARMIN_EMAIL or GARMIN_PASSWORD.")


def authenticate_with_retries() -> None:
    if os.path.isdir(TOKENSTORE_DIR):
        try:
            print("Reuse session...")
            garth.resume(TOKENSTORE_DIR)
            return
        except Exception as e:
            print(f"Could not reuse saved session: {e}")

    last_error = None
    for attempt in range(1, MAX_LOGIN_RETRIES + 1):
        try:
            print("Starting direct login with Garth...")
            garth.login(EMAIL, PASSWORD)
            garth.save(TOKENSTORE_DIR)
            print("Session saved for future runs.")
            return
        except Exception as e:
            last_error = e
            if "429" not in str(e) or attempt == MAX_LOGIN_RETRIES:
                raise
            wait_seconds = min(300, (2 ** attempt) * 15)
            print(
                f"Garmin rate-limited login (429). "
                f"Retry {attempt}/{MAX_LOGIN_RETRIES} in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    if last_error:
        raise last_error


try:
    authenticate_with_retries()

    client = Garmin()
    client.garth = garth.client

    all_activities = []
    start = 0
    limit = ACTIVITIES_PAGE_SIZE
    print("Downloading activities...")
    while True:
        activities = client.get_activities(start, limit)
        if not activities:
            break
        all_activities.extend(activities)

        if len(activities) < limit:
            break

        start += limit
        time.sleep(1)

    if not all_activities:
        raise ValueError("No activities downloaded.")

    df = pd.DataFrame(all_activities)
    df_running = df[df["activityType"].apply(lambda x: x.get("typeKey") == "running")].copy()

    for col in sorted(df_running.columns):
        print(col)

    cols = [
        "startTimeLocal",
        "distance",
        "duration",
        "movingDuration",
        "averageSpeed",
        "averageHR",
        "avgStrideLength",
        "maxHR",
        "averageRunningCadenceInStepsPerMinute", # Cadencia media en pasos por minuto
        "maxRunningCadenceInStepsPerMinute", # Cadencia máxima en pasos por minuto
        "elevationGain",
        "elevationLoss",
        "calories",
        "vO2MaxValue", # VO2 Max en ese momento, solo desde 2015
        "steps",
    ]

    cols_final = [c for c in cols if c in df_running.columns]
    print(df_running.columns)
    df_final = df_running[cols_final]
    # evita registros no existentes o no numéricos
    df_final["vO2MaxValue"] = pd.to_numeric(df_final["vO2MaxValue"], errors="coerce")
    df_final["steps"] = pd.to_numeric(df_final["steps"], errors="coerce")

    df_final.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"File saved with {len(df_final)} runs and {len(cols_final)} metrics.")
except Exception as e:
    print(f"Error: {e}")
