# Copyright (c) 2026 Raul Hernandez Lopez
#
# This file is part of the project and is licensed under the
# Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0).
#
# You are free to share and adapt this file under the terms of the CC BY-SA 4.0 license.
# Full license: https://creativecommons.org/licenses/by-sa/4.0/legalcode
#
# @author: Raul Hernandez Lopez

# Analisis de datos de Garmin Connect para corredores

#!/usr/bin/env python3
"""
Análisis de datos de running - Garmin Connect
Visualización de datos
@Author: Raul Hernandez
"""

import os
import itertools
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import seaborn as sns

# Config
DATASOURCE = "running_dataset.csv"
GRAPHICS_FOLDER = "graphics_svg"
os.makedirs(GRAPHICS_FOLDER, exist_ok=True)

sns.set_style("whitegrid")


def prepare_data(path_csv):
    # Carga CSV de Garmin y prepara datos.
    df = pd.read_csv(path_csv, parse_dates=["startTimeLocal"])

    # Conversion unidades
    df["distance_km"] = df["distance"] / 1000
    df["duration_min"] = df["duration"] / 60
    df["velocity_kmh"] = df["averageSpeed"] * 3.6

    # Ritmo en min/km
    df["rith_decimal"] = np.where(
        df["averageSpeed"] > 0,
        (1000 / df["averageSpeed"]) / 60,
        np.nan
    )

    # Ritmo en mm:ss
    def decimal_to_mmss(val):
        if pd.isna(val):
            return ""
        mins = int(val)
        segs = int(round((val - mins) * 60))
        return f"{mins}:{segs:02d}"

    df["rith_min_km"] = df["rith_decimal"].apply(decimal_to_mmss)

    # Columnas temporales
    df["date"] = df["startTimeLocal"].dt.date
    df["year"] = df["startTimeLocal"].dt.year
    df["month"] = df["startTimeLocal"].dt.month
    df["trimester"] = df["startTimeLocal"].dt.quarter
    df["year_month"] = df["startTimeLocal"].dt.to_period("M")

    # Día de la semana en español
    days_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes",
        "Saturday": "Sábado", "Sunday": "Domingo",
    }
    df["day_week"] = df["startTimeLocal"].dt.day_name().map(days_es)

    # Filtro que elimina sesiones muy cortas (tests GPS, errores)
    n_prev = len(df)
    df = df[(df["distance_km"] >= 0.5) & (df["duration"] >= 120)].copy()
    print(f"  Filtrado: {n_prev} -> {len(df)} registros")

    df.sort_values("startTimeLocal", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# Ritmo (5.25 -> "5:15")
def fmt_rith(val, _):
    mins = int(val)
    segs = int(round((val - mins) * 60))
    return f"{mins}:{segs:02d}"

# 1 Barras con km totales por año
def graphic_bars_km_yearly(df):
    filtered_year = df[df["year"].between(2014, 2025)]
    km_year = filtered_year.groupby("year", as_index=True)["distance_km"].sum()
    print(km_year)
    fig, ax = plt.subplots(figsize=(12, 5))
    barras = ax.bar(km_year.index.astype(str), km_year.values,
                    color='steelblue', edgecolor='white', linewidth=0.8)

    # tags sobre cada barra
    for b in barras:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + 20,
                f"{h:,.0f}", ha="center", va="bottom", fontsize=8)

    plt.title("Kilómetros totales por año", fontsize=14, weight="bold")
    plt.xlabel("Año")
    plt.ylabel("Kilómetros")
    plt.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "01_barras_km_anual.svg"), format="svg")
    plt.show()


# 2 Líneas de evolución del ritmo medio mensual con media móvil
def graphic_lines_rith_monthly(df):
    filtered_year = df[df["year"].between(2013, 2025)]
    monthly = (
        filtered_year.groupby("year_month")["rith_decimal"]
        .agg(rith_decimal="median", n="count")
        .reset_index()
    )
    monthly = monthly[monthly["n"] >= 4]
    monthly["year_month_dt"] = monthly["year_month"].dt.to_timestamp()
    monthly["avg_movil"] = monthly["rith_decimal"].rolling(6, min_periods=2).mean()
    # print(monthly)
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(monthly["year_month_dt"], monthly["rith_decimal"],
            marker="o", markersize=3, linewidth=0.8, alpha=0.5,
            color="steelblue", label="Ritmo medio mensual")
    ax.plot(monthly["year_month_dt"], monthly["avg_movil"],
            linewidth=2.5, color="darkred", label="Media móvil (6 meses)")

    ax.invert_yaxis()  # Menor min/km = más rápido
    ax.set_ylim(6.5, 4.5)  # ajusta entre 4:30 (rápido, arriba) y 6:30 (lento, abajo)
    plt.title("Evolución del ritmo medio mensual (min/km)", fontsize=14, weight="bold")
    plt.xlabel("Fecha")
    plt.ylabel("Ritmo (min/km)")

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_rith))

    locator = mdates.YearLocator()
    formatter = mdates.DateFormatter("%Y")
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "02_lineas_ritmo_mensual.svg"), format="svg")
    plt.show()


# 3 Histograma de distribución de distancias con KDE
def graphic_histogram_distances(df):
    fig, ax = plt.subplots(figsize=(14, 5))
    filtered_distance = df[df["distance_km"].between(0, 21.5)]
    # definir limites para dejar valores centrados entre los rangos [0.5, 1.5] -> 1 , 2, 3, ... 20
    limit_bins = np.arange(0, 23) - 0.5
    
    alt, lim, bar = ax.hist(filtered_distance["distance_km"].dropna(), bins=limit_bins,
            color="steelblue", alpha=0.7, edgecolor="white",
            linewidth=0.5, label="Frecuencia")
    print(filtered_distance)
    # KDE superpuesto
    ax2 = ax.twinx()
    sns.kdeplot(df["distance_km"].dropna(), ax=ax2,
                color="darkred", linewidth=2, label="KDE")
    ax2.set_ylabel("Densidad (KDE)")
    # tags por barra
    for b in bar:
        h = b.get_height()
        if h > 0: # solo etiquetas con al menos 1 sesión por distancia recorrida
            ax.text(b.get_x() + b.get_width() / 2, h + 5,
                f"{h:,.0f}", ha="center", va="bottom", fontsize=8)
    plt.title("Distribución de distancia por sesión", fontsize=14, weight="bold")
    ax.set_xlabel("Distancia (km)")
    ax.set_ylabel("Nº de sesiones")
    ax.set_xlim(0, 21.5)
    ax.set_ylim(0)
    ax2.set_ylim(0)
    ax.grid(axis="y", alpha=0.3)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))

    # Leyenda combinada
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right")

    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "03_histograma_distancias.svg"), format="svg")
    plt.show()


# 4 Dispersión con Correlación de ritmo con FC media por distancia
def graphic_dispersion_rith_hr(df):
    subset = df.dropna(subset=["rith_decimal", "averageHR"]).copy()
    rith = subset["rith_decimal"]
    filtered_rithm = rith.between(rith.quantile(0.005), rith.quantile(0.995))
    
    subset = subset[filtered_rithm]
    # print(f'dispersión de subset: {subset}')
    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(subset["rith_decimal"], subset["averageHR"],
                    c=subset["distance_km"], cmap="viridis",
                    s=15, alpha=0.5, edgecolors="none")
    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("Distancia (km)")
    ax.invert_xaxis() # Ritmo más rápido (menor min/km) hacia la derecha

    # Regresión lineal solo si hay suficientes datos y variabilidad
    has_regression = (
        len(subset) >= 3
        and subset["rith_decimal"].nunique() > 1
        and subset["averageHR"].nunique() > 1
    )
    if has_regression:
        x = subset["rith_decimal"]
        y = subset["averageHR"]
        coef = np.polyfit(x, y, 1)
        x_reg = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_reg, np.polyval(coef, x_reg),
                color="darkred", linewidth=2, linestyle="--",
                label=f"Regresión: FC = {coef[0]:.1f}*ritmo + {coef[1]:.0f}")

    plt.title("Comparativa Ritmo medio con Frecuencia cardíaca media", fontsize=14, weight="bold")
    plt.xlabel("Ritmo medio (min/km)")
    plt.ylabel("FC media (ppm)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_rith))
    if has_regression:
        plt.legend(loc="upper left", fontsize=9)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "04_dispersion_ritmo_hr.svg"), format="svg")
    plt.show()


# 5 Caja y bigotes con ritmo por año
def graphic_boxplot_rith_yearly(df):
    fig, ax = plt.subplots(figsize=(14, 6))
    filtered_year = df[df["year"].between(2013, 2026)]
    # showfliers=False, se eliminan porque pueden ser sesiones de recuperación lentas
    # o sprints cortos, no aportan información
    years = sorted(filtered_year["year"].unique())
    data_anually = [filtered_year[filtered_year["year"] == a]["rith_decimal"].dropna().values for a in years]
    # print(f'boxplot ritmo anual: {data_anually}')
    sequence = plt.boxplot(data_anually, tick_labels=years, showfliers=False, widths=0.8, vert=True)

    colours=['r','g','b','y']
    for p, c in zip(sequence['boxes'], itertools.cycle(colours)):
        p.set_color(c)
    # mas rapido arriba
    ax.invert_yaxis()
    plt.title("Distribución del ritmo por año (sin outliers)", fontsize=14, weight="bold")
    plt.xlabel("Año")
    plt.ylabel("Ritmo (min/km)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_rith))
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "05_boxplot_ritmo_anual.svg"), format="svg")
    plt.show()


# Seaborn diversas gráficas
def graphic_panel_multi(df):
    # 6 VO2max medio por año
    fig, ax = plt.subplots(figsize=(9, 5))
    vo2 = df.dropna(subset=["vO2MaxValue"])
    print(f'vo2: {vo2['vO2MaxValue']}')
    if not vo2.empty:
        sns.lineplot(data=vo2, x="year", y="vO2MaxValue",
                     estimator="mean", errorbar="sd",
                     marker="o", color="steelblue", ax=ax)
    ax.set_title("VO2max medio por año", fontsize=13, weight="bold")
    ax.set_xlabel("Año")
    ax.set_ylabel("VO2max (mL/kg/min)")
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "06_vo2max_anual.svg"), format="svg")
    plt.show()

    # 07 Sesiones por día de la semana
    fig, ax = plt.subplots(figsize=(9, 5))
    days_sorted = ["Lunes", "Martes", "Miércoles", "Jueves",
                  "Viernes", "Sábado", "Domingo"]
    days_ok = [d for d in days_sorted if d in df["day_week"].values]
    sns.countplot(data=df, x="day_week", order=days_ok,
                  color="orange", ax=ax)
    ax.set_title("Sesiones por día de la semana", fontsize=13, weight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Nº sesiones")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "07_sesiones_dia_semana.svg"), format="svg")
    plt.show()

    # 08 Desnivel positivo por trimestre (violín)
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.violinplot(data=df, x="trimester", y="elevationGain",
                   hue="trimester", legend=False,
                   inner="box", palette="Set2", ax=ax, cut=0)
    ax.set_title("Desnivel positivo por trimestre", fontsize=13, weight="bold")
    ax.set_xlabel("Trimestre")
    ax.set_xticklabels([f"T{int(t.get_text())}" for t in ax.get_xticklabels()])
    ax.set_ylabel("Desnivel + (m)")
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "08_desnivel_trimestre.svg"), format="svg")
    plt.show()

    # 09 Mapa de calor de correlaciones
    fig, ax = plt.subplots(figsize=(9, 7))
    cols_corr = ["distance_km", "rith_decimal", "averageHR",
                 "averageRunningCadenceInStepsPerMinute",
                 "elevationGain", "calories", "vO2MaxValue"]
    cols_ok = [c for c in cols_corr if c in df.columns]
    corr = df[cols_ok].corr()
    # print(corr)
    tags = {
        "distance_km": "Dist (km)", "rith_decimal": "Ritmo",
        "averageHR": "FC media",
        "averageRunningCadenceInStepsPerMinute": "Cadencia",
        "elevationGain": "Desnivel+", "calories": "Calorías",
        "vO2MaxValue": "VO2max",
    }
    corr = corr.rename(index=tags, columns=tags)
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", mask=mask, vmin=-1, vmax=1,
                center=0, square=True, linewidths=0.5, ax=ax, annot_kws={"fontsize": 9})
    ax.set_title("Correlaciones entre métricas", fontsize=13, weight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "09_correlaciones.svg"), format="svg")
    plt.show()


# 10 Pairplot en Seaborn
def graphic_pairplot(df):
    cols = ["distance_km", "rith_decimal", "averageHR",
            "averageRunningCadenceInStepsPerMinute"]
    tags = {
        "distance_km": "Distancia (km)",
        "rith_decimal": "Ritmo (min/km)",
        "averageHR": "FC media (ppm)",
        "averageRunningCadenceInStepsPerMinute": "Cadencia (pasos/min)",
    }
    sub = df[cols].dropna().rename(columns=tags)
    # print(sub)
    g = sns.pairplot(sub, corner=True, kind="scatter", diag_kind="kde",
                     plot_kws={"alpha": 0.4, "s": 10})
    g.figure.suptitle("Análisis multivariable: Distancia, Ritmo, FC y Cadencia",
                      y=1.02, fontsize=14, weight="bold")
    plt.savefig(os.path.join(GRAPHICS_FOLDER, "10_pairplot_multivariable.svg"), format="svg")
    plt.show()

# MAIN
# ============================================================

def main():
    print("Análisis de datos de running - Garmin Connect")
    print("-" * 50)

    df = prepare_data(DATASOURCE)

    print(f"  Entrenamientos: {len(df)}")
    print(f"  Periodo: {df['year'].min()}-{df['year'].max()}")
    print(f"  Total km: {df['distance_km'].sum():,.0f}")
    ritmo = df['rith_decimal'].mean()
    print(f"  Ritmo medio: {int(ritmo)}:{int(round((ritmo % 1) * 60)):02d} min/km")

    print(f"\nGenerando gráficas en {GRAPHICS_FOLDER}/...")

    graphic_bars_km_yearly(df)
    graphic_lines_rith_monthly(df)
    graphic_histogram_distances(df)
    graphic_dispersion_rith_hr(df)
    graphic_boxplot_rith_yearly(df)
    graphic_panel_multi(df)
    graphic_pairplot(df)

    n_svg = len([f for f in os.listdir(GRAPHICS_FOLDER) if f.endswith(".svg")])
    print(f"\nCompletado {n_svg} gráficas SVG generadas.")


if __name__ == "__main__":
    main()
