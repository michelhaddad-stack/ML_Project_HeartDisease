import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def load_data(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        try:
            return pd.read_csv(path, sep=None, engine="python")
        except Exception:
            return pd.read_csv(path)

    raise ValueError("Formato não suportado. Use .xlsx, .xls ou .csv")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    df = df.rename(
        columns={
            "idade": "idade",
            "sexo": "sexo",
            "vop": "vop",
            "hipertensao": "has",
            "hipertensão": "has",
            "has": "has",
            "diabetes": "dm",
            "dm": "dm",
        }
    )

    return df


def to_numeric_or_nan(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(r"[^0-9,.-]", "", regex=True)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["idade", "sexo", "vop", "has", "dm"]

    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan

    df["idade"] = to_numeric_or_nan(df["idade"])
    df["vop"] = to_numeric_or_nan(df["vop"])
    df["has"] = pd.to_numeric(df["has"], errors="coerce")
    df["dm"] = pd.to_numeric(df["dm"], errors="coerce")

    df = df.dropna(subset=["vop", "idade"])

    return df


def descriptive_stats(df: pd.DataFrame) -> None:
    media_vop = df["vop"].mean()
    dp_vop = df["vop"].std()

    print(f"Média da VOP: {media_vop:.2f} m/s")
    print(f"Desvio-padrão: {dp_vop:.2f}")

    sexo_dist = df["sexo"].value_counts(dropna=False)
    print("\nDistribuição por sexo:")
    print(sexo_dist)

    has_sim = df[df["has"] == 1]["vop"]
    has_nao = df[df["has"] == 0]["vop"]
    print("\nVOP - Hipertensos:", has_sim.mean())
    print("VOP - Não hipertensos:", has_nao.mean())

    dm_sim = df[df["dm"] == 1]["vop"]
    dm_nao = df[df["dm"] == 0]["vop"]
    print("\nVOP - Diabéticos:", dm_sim.mean())
    print("VOP - Não diabéticos:", dm_nao.mean())

    correlacao = df["vop"].corr(df["idade"])
    print(f"\nCorrelação VOP x Idade: {correlacao:.2f}")


def plot_scatter(df: pd.DataFrame) -> None:
    plt.figure(figsize=(8, 5))
    sns.scatterplot(data=df, x="idade", y="vop")
    plt.xlabel("Idade")
    plt.ylabel("VOP (m/s)")
    plt.title("VOP vs Idade")
    plt.tight_layout()
    plt.show()


def plot_age_bars(df: pd.DataFrame) -> None:
    bins = [0, 40, 50, 60, 70, 80, 100]
    labels = ["<40", "40-50", "50-60", "60-70", "70-80", "80+"]

    df = df.copy()
    df["faixa_etaria"] = pd.cut(df["idade"], bins=bins, labels=labels)
    media_por_faixa = df.groupby("faixa_etaria", observed=False)["vop"].mean()

    plt.figure(figsize=(8, 5))
    media_por_faixa.plot(kind="bar")
    plt.xlabel("Faixa Etária")
    plt.ylabel("VOP média")
    plt.title("VOP por Faixa Etária")
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Análise estatística de VOP.")
    parser.add_argument("arquivo", help="Caminho para arquivo .xlsx/.xls/.csv com dados de VOP")
    args = parser.parse_args()

    df = load_data(args.arquivo)
    df = normalize_columns(df)
    df = preprocess(df)

    descriptive_stats(df)
    plot_scatter(df)
    plot_age_bars(df)


if __name__ == "__main__":
    main()
