import io
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Analisador de VOP",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --primary: #2563eb;
            --secondary: #0f172a;
            --success: #059669;
            --warning: #d97706;
            --danger: #dc2626;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .hero {
            background: linear-gradient(135deg, rgba(37,99,235,0.12), rgba(15,23,42,0.06));
            border: 1px solid rgba(37,99,235,0.18);
            border-radius: 18px;
            padding: 1.5rem;
            margin-bottom: 1.25rem;
        }
        .metric-card {
            background: rgba(255,255,255,0.75);
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 16px;
            padding: 1rem;
            box-shadow: 0 10px 25px rgba(15,23,42,0.05);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

COLUMN_ALIASES: Dict[str, List[str]] = {
    "patient_id": ["id", "patient_id", "patient", "paciente", "codigo", "cod_paciente", "record_id"],
    "age": ["age", "idade", "anos", "idade_anos", "idadeanos"],
    "sex": ["sex", "sexo", "gender", "genero", "biological_sex"],
    "pwv": [
        "vop",
        "pwv",
        "pulse_wave_velocity",
        "velocidade_onda_pulso",
        "velocidade_da_onda_de_pulso",
        "cfpwv",
        "ba_pwv",
        "carotid_femoral_pwv",
    ],
    "hypertension": ["hipertenso", "hipertensao", "has", "hypertension", "hypertensive", "hta"],
    "diabetes": ["diabetico", "diabetes", "dm", "diabetic", "dm2", "dm1"],
    "sbp": ["pas", "pressao_sistolica", "systolic_bp", "sbp", "ap_hi"],
    "dbp": ["pad", "pressao_diastolica", "diastolic_bp", "dbp", "ap_lo"],
}

SEX_MAP = {
    "m": "Masculino",
    "male": "Masculino",
    "masculino": "Masculino",
    "homem": "Masculino",
    "1": "Masculino",
    "f": "Feminino",
    "female": "Feminino",
    "feminino": "Feminino",
    "mulher": "Feminino",
    "0": "Feminino",
    "2": "Feminino",
}

BOOLEAN_TRUE = {"1", "sim", "yes", "true", "positivo", "presente", "com", "y"}
BOOLEAN_FALSE = {"0", "nao", "não", "no", "false", "negativo", "ausente", "sem", "n"}

AGE_BINS = [0, 39, 49, 59, 69, 79, 200]
AGE_LABELS = ["<40", "40-49", "50-59", "60-69", "70-79", "80+"]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return "_".join(value.strip().lower().replace("/", " ").replace("-", " ").split())


def find_matching_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    normalized = {normalize_text(col): col for col in columns}
    for alias in aliases:
        key = normalize_text(alias)
        if key in normalized:
            return normalized[key]
    for norm_col, original in normalized.items():
        if any(normalize_text(alias) in norm_col for alias in aliases):
            return original
    return None


def load_spreadsheet(uploaded_file) -> pd.DataFrame:
    suffix = uploaded_file.name.lower()
    if suffix.endswith(".csv"):
        raw = uploaded_file.getvalue()
        for sep in [None, ";", ",", "\t"]:
            try:
                if sep is None:
                    return pd.read_csv(io.BytesIO(raw), sep=None, engine="python")
                return pd.read_csv(io.BytesIO(raw), sep=sep)
            except Exception:
                continue
        raise ValueError("Não foi possível identificar o separador do CSV.")
    if suffix.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("Formato não suportado. Envie CSV, XLSX ou XLS.")


def parse_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(r"[^0-9,.-]", "", regex=True)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_sex(series: pd.Series) -> pd.Series:
    mapped = series.astype(str).map(lambda x: SEX_MAP.get(normalize_text(x), np.nan))
    return mapped.fillna("Não informado")


def parse_boolean(series: pd.Series) -> pd.Series:
    def mapper(value):
        key = normalize_text(value)
        if key in BOOLEAN_TRUE:
            return "Sim"
        if key in BOOLEAN_FALSE:
            return "Não"
        try:
            numeric = float(str(value).replace(",", "."))
            return "Sim" if numeric >= 1 else "Não"
        except Exception:
            return np.nan

    return series.map(mapper)


def extract_first_number(text: str, pattern: str) -> Optional[float]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def extract_clinical_context(text: str) -> Dict[str, object]:
    if not text.strip():
        return {}

    lowered = text.lower()
    normalized = normalize_text(text)
    context: Dict[str, object] = {}

    age = extract_first_number(lowered, r"idade\s*[:=]?\s*(\d{1,3})")
    if age is None:
        age = extract_first_number(lowered, r"(\d{1,3})\s*anos")
    if age is not None:
        context["age"] = age

    pwv = extract_first_number(
        lowered,
        r"(?:vop|pwv|velocidade\s+da\s+onda\s+de\s+pulso)\s*[:=]?\s*(\d+(?:[\.,]\d+)?)",
    )
    if pwv is not None:
        context["pwv"] = pwv

    sbp = extract_first_number(lowered, r"(?:pas|pressao\s+sistolica|pressão\s+sistólica|sbp)\s*[:=]?\s*(\d+(?:[\.,]\d+)?)")
    dbp = extract_first_number(lowered, r"(?:pad|pressao\s+diastolica|pressão\s+diastólica|dbp)\s*[:=]?\s*(\d+(?:[\.,]\d+)?)")
    if sbp is not None:
        context["sbp"] = sbp
    if dbp is not None:
        context["dbp"] = dbp

    if any(term in normalized for term in ["sexo_masculino", "masculino", "homem", "male"]):
        context["sex"] = "Masculino"
    elif any(term in normalized for term in ["sexo_feminino", "feminino", "mulher", "female"]):
        context["sex"] = "Feminino"

    if any(term in normalized for term in ["nao_hipertenso", "nao_hipertensa", "sem_hipertensao"]):
        context["hypertension"] = "Não"
    elif any(term in normalized for term in ["hipertenso", "hipertensa", "hipertensao", "has", "hypertension"]):
        context["hypertension"] = "Sim"

    if any(term in normalized for term in ["nao_diabetico", "nao_diabetica", "nao_diabetes", "sem_diabetes"]):
        context["diabetes"] = "Não"
    elif any(term in normalized for term in ["diabetico", "diabetica", "diabetes", "dm1", "dm2", "diabetic"]):
        context["diabetes"] = "Sim"

    return context


def build_manual_context(
    age: Optional[float],
    sex: str,
    hypertension: str,
    diabetes: str,
    pwv: Optional[float],
    sbp: Optional[float],
    dbp: Optional[float],
) -> Dict[str, object]:
    context: Dict[str, object] = {}
    if age is not None:
        context["age"] = age
    if sex != "Não informado":
        context["sex"] = sex
    if hypertension != "Não informado":
        context["hypertension"] = hypertension
    if diabetes != "Não informado":
        context["diabetes"] = diabetes
    if pwv is not None:
        context["pwv"] = pwv
    if sbp is not None:
        context["sbp"] = sbp
    if dbp is not None:
        context["dbp"] = dbp
    return context


def standardize_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    standardized = pd.DataFrame(index=df.index)
    mapping: Dict[str, Optional[str]] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        matched = find_matching_column(df.columns.tolist(), aliases)
        mapping[canonical] = matched
        standardized[canonical] = df[matched] if matched else np.nan

    for column in ["age", "pwv", "sbp", "dbp"]:
        standardized[column] = parse_numeric(standardized[column])

    standardized["sex"] = parse_sex(standardized["sex"])
    standardized["hypertension"] = parse_boolean(standardized["hypertension"])
    standardized["diabetes"] = parse_boolean(standardized["diabetes"])

    if standardized["patient_id"].isna().all():
        standardized["patient_id"] = np.arange(1, len(standardized) + 1)

    standardized["age_group"] = pd.cut(
        standardized["age"], bins=AGE_BINS, labels=AGE_LABELS, include_lowest=True
    )

    return standardized, mapping


def create_dataframe_from_context(context: Dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "patient_id": 1,
                "age": context.get("age", np.nan),
                "sex": context.get("sex", "Não informado"),
                "pwv": context.get("pwv", np.nan),
                "hypertension": context.get("hypertension", np.nan),
                "diabetes": context.get("diabetes", np.nan),
                "sbp": context.get("sbp", np.nan),
                "dbp": context.get("dbp", np.nan),
            }
        ]
    )


def apply_context_to_dataframe(df: pd.DataFrame, context: Dict[str, object], fill_all_missing: bool) -> pd.DataFrame:
    result = df.copy()
    for column, value in context.items():
        if column not in result.columns or value is None:
            continue
        if fill_all_missing:
            result[column] = result[column].fillna(value)
        elif len(result) > 0 and pd.isna(result.loc[result.index[0], column]):
            result.loc[result.index[0], column] = value

    if "age" in result.columns:
        result["age_group"] = pd.cut(result["age"], bins=AGE_BINS, labels=AGE_LABELS, include_lowest=True)
    return result


def summarize_missing(df: pd.DataFrame) -> pd.DataFrame:
    missing = df.isna().sum().rename("missing_count").to_frame()
    missing["missing_pct"] = (missing["missing_count"] / len(df) * 100).round(2)
    return missing.reset_index(names="column")


def grouped_summary(df: pd.DataFrame, group_col: str, value_col: str = "pwv") -> pd.DataFrame:
    valid = df.dropna(subset=[group_col, value_col]).copy()
    if valid.empty:
        return pd.DataFrame(columns=[group_col, "n", "mean", "std"])
    summary = valid.groupby(group_col)[value_col].agg(n="count", mean="mean", std="std").reset_index()
    summary["mean"] = summary["mean"].round(2)
    summary["std"] = summary["std"].round(2)
    return summary


def correlation_text(df: pd.DataFrame) -> Tuple[float, str]:
    valid = df[["age", "pwv"]].dropna()
    if len(valid) < 2:
        return np.nan, "Amostra insuficiente"
    corr = valid["age"].corr(valid["pwv"])
    if pd.isna(corr):
        return np.nan, "Correlação indisponível (variabilidade insuficiente)"
    strength = "fraca"
    if abs(corr) >= 0.7:
        strength = "forte"
    elif abs(corr) >= 0.4:
        strength = "moderada"
    direction = "positiva" if corr >= 0 else "negativa"
    return corr, f"Correlação {direction} {strength}"


def build_scatter(df: pd.DataFrame):
    plot_df = df.dropna(subset=["age", "pwv"]).copy()
    if plot_df.empty:
        return None
    color_col = "sex" if plot_df["sex"].notna().any() else None
    fig = px.scatter(
        plot_df,
        x="age",
        y="pwv",
        color=color_col,
        trendline="ols" if len(plot_df) >= 2 else None,
        title="Dispersão entre VOP e idade",
        labels={"age": "Idade (anos)", "pwv": "VOP", "sex": "Sexo"},
        hover_data=["patient_id", "hypertension", "diabetes"],
    )
    fig.update_layout(legend_title_text="Sexo")
    return fig


def build_age_bar(df: pd.DataFrame):
    plot_df = df.dropna(subset=["age_group", "pwv"]).copy()
    if plot_df.empty:
        return None, pd.DataFrame(columns=["age_group", "media_vop", "n"])
    summary = plot_df.groupby("age_group", observed=False)["pwv"].agg(media_vop="mean", n="count").reset_index()
    summary = summary[summary["n"] > 0]
    summary["media_vop"] = summary["media_vop"].round(2)
    fig = px.bar(
        summary,
        x="age_group",
        y="media_vop",
        text="n",
        title="Média da VOP por faixa etária",
        labels={"age_group": "Faixa etária", "media_vop": "VOP média", "n": "n"},
    )
    fig.update_traces(marker_color="#2563eb")
    return fig, summary


def render_mapping_table(mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "coluna_padronizada": list(mapping.keys()),
            "coluna_origem": [mapping[key] if mapping[key] else "não encontrada" for key in mapping],
        }
    )


def main():
    st.markdown(
        """
        <div class="hero">
            <h1 style="margin-bottom:0.25rem;">🫀 Analisador de Velocidade da Onda de Pulso</h1>
            <p style="margin-bottom:0;">
                Envie a planilha de exames de VOP e/ou descreva o quadro clínico.
                O app organiza, padroniza e pode preencher dados faltantes com base no texto informado.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Entradas")
        uploaded_file = st.file_uploader(
            "Planilha de exames",
            type=["csv", "xlsx", "xls"],
            help="Envie a planilha com VOP, idade, sexo, hipertensão e diabetes quando disponível.",
        )
        clinical_text = st.text_area(
            "Quadro clínico / observações",
            placeholder=(
                "Ex.: Paciente feminina, 58 anos, hipertensa, não diabética, "
                "VOP 10,2 m/s, PAS 148, PAD 92."
            ),
            height=180,
        )
        st.markdown("### Preenchimento manual")
        manual_age = st.number_input("Idade", min_value=0, max_value=120, value=None, placeholder="Opcional")
        manual_sex = st.selectbox("Sexo", ["Não informado", "Feminino", "Masculino"])
        manual_hypertension = st.selectbox("Hipertensão", ["Não informado", "Não", "Sim"])
        manual_diabetes = st.selectbox("Diabetes", ["Não informado", "Não", "Sim"])
        manual_pwv = st.number_input("VOP", min_value=0.0, value=None, placeholder="Opcional")
        manual_sbp = st.number_input("PAS/SBP", min_value=0.0, value=None, placeholder="Opcional")
        manual_dbp = st.number_input("PAD/DBP", min_value=0.0, value=None, placeholder="Opcional")
        fill_all_missing = st.checkbox("Preencher valores ausentes da planilha com o quadro clínico/manual", value=True)

    extracted_context = extract_clinical_context(clinical_text)
    manual_context = build_manual_context(
        manual_age,
        manual_sex,
        manual_hypertension,
        manual_diabetes,
        manual_pwv,
        manual_sbp,
        manual_dbp,
    )
    combined_context = {**extracted_context, **manual_context}

    raw_df = None
    mapping: Dict[str, Optional[str]] = {key: None for key in COLUMN_ALIASES}

    if uploaded_file:
        try:
            raw_df = load_spreadsheet(uploaded_file)
            standardized_df, mapping = standardize_dataframe(raw_df)
        except Exception as exc:
            st.error(f"Erro ao carregar a planilha: {exc}")
            return
        standardized_df = apply_context_to_dataframe(standardized_df, combined_context, fill_all_missing)
    elif combined_context:
        standardized_df = create_dataframe_from_context(combined_context)
        standardized_df = apply_context_to_dataframe(standardized_df, combined_context, fill_all_missing=True)
    else:
        st.info(
            "Você pode enviar a planilha, colar o quadro clínico ou usar os campos manuais. "
            "Assim eu estruturo os dados e preparo a análise da VOP."
        )
        return

    if standardized_df["pwv"].notna().sum() == 0:
        st.warning("Ainda não encontrei um valor de VOP/PWV. Informe na planilha, no texto clínico ou no campo manual.")

    standardized_df["age_group"] = pd.cut(
        standardized_df["age"], bins=AGE_BINS, labels=AGE_LABELS, include_lowest=True
    )

    missing_summary = summarize_missing(standardized_df)
    corr_value, corr_label = correlation_text(standardized_df)
    sex_distribution = standardized_df["sex"].value_counts(dropna=False).rename_axis("sex").reset_index(name="n")
    sex_distribution["percentual"] = (sex_distribution["n"] / sex_distribution["n"].sum() * 100).round(2)
    hypertension_summary = grouped_summary(standardized_df, "hypertension")
    diabetes_summary = grouped_summary(standardized_df, "diabetes")
    age_bar_fig, age_bar_table = build_age_bar(standardized_df)
    scatter_fig = build_scatter(standardized_df)

    valid_pwv = standardized_df["pwv"].dropna()
    pwv_mean = valid_pwv.mean()
    pwv_std = valid_pwv.std()

    st.subheader("1. Dados identificados e preenchimento")
    overview_col, extracted_col = st.columns([2, 1])

    with overview_col:
        st.markdown("**Mapeamento das colunas da planilha**")
        st.dataframe(render_mapping_table(mapping), use_container_width=True)
        if raw_df is None:
            st.caption("Sem planilha: os dados abaixo foram montados a partir do quadro clínico e/ou preenchimento manual.")

    with extracted_col:
        st.markdown("**Informações extraídas do quadro clínico**")
        extracted_table = pd.DataFrame(
            {"campo": list(combined_context.keys()), "valor": list(combined_context.values())}
        ) if combined_context else pd.DataFrame(columns=["campo", "valor"])
        st.dataframe(extracted_table, use_container_width=True)

    st.markdown("**Valores ausentes por coluna padronizada**")
    st.dataframe(missing_summary, use_container_width=True)

    st.subheader("2. Dados padronizados editáveis")
    edited_df = st.data_editor(
        standardized_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="standardized_editor",
    )
    standardized_df = edited_df.copy()
    standardized_df["age"] = parse_numeric(standardized_df["age"])
    standardized_df["pwv"] = parse_numeric(standardized_df["pwv"])
    standardized_df["sbp"] = parse_numeric(standardized_df["sbp"])
    standardized_df["dbp"] = parse_numeric(standardized_df["dbp"])
    standardized_df["sex"] = parse_sex(standardized_df["sex"])
    standardized_df["hypertension"] = parse_boolean(standardized_df["hypertension"])
    standardized_df["diabetes"] = parse_boolean(standardized_df["diabetes"])
    standardized_df["age_group"] = pd.cut(standardized_df["age"], bins=AGE_BINS, labels=AGE_LABELS, include_lowest=True)

    missing_summary = summarize_missing(standardized_df)
    corr_value, corr_label = correlation_text(standardized_df)
    sex_distribution = standardized_df["sex"].value_counts(dropna=False).rename_axis("sex").reset_index(name="n")
    sex_distribution["percentual"] = (sex_distribution["n"] / sex_distribution["n"].sum() * 100).round(2)
    hypertension_summary = grouped_summary(standardized_df, "hypertension")
    diabetes_summary = grouped_summary(standardized_df, "diabetes")
    age_bar_fig, age_bar_table = build_age_bar(standardized_df)
    scatter_fig = build_scatter(standardized_df)
    valid_pwv = standardized_df["pwv"].dropna()
    pwv_mean = valid_pwv.mean()
    pwv_std = valid_pwv.std()

    st.subheader("3. Visão estatística da VOP")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Amostra válida de VOP", int(valid_pwv.count()))
    metric_cols[1].metric("Média da VOP", f"{pwv_mean:.2f}" if not np.isnan(pwv_mean) else "NA")
    metric_cols[2].metric("Desvio-padrão", f"{pwv_std:.2f}" if not np.isnan(pwv_std) else "NA")
    metric_cols[3].metric("Correlação VOP x idade", f"{corr_value:.3f}" if not np.isnan(corr_value) else "NA")
    st.caption(corr_label)

    st.markdown("**Distribuição por sexo**")
    st.dataframe(sex_distribution, use_container_width=True)

    compare_left, compare_right = st.columns(2)
    with compare_left:
        st.markdown("**Comparação entre hipertensos e não hipertensos**")
        st.dataframe(hypertension_summary, use_container_width=True)
    with compare_right:
        st.markdown("**Comparação entre diabéticos e não diabéticos**")
        st.dataframe(diabetes_summary, use_container_width=True)

    st.subheader("4. Gráficos")
    graph_left, graph_right = st.columns(2)
    with graph_left:
        if scatter_fig is not None:
            st.plotly_chart(scatter_fig, use_container_width=True)
        else:
            st.info("Gráfico de dispersão disponível quando houver pelo menos idade e VOP preenchidas.")
    with graph_right:
        if age_bar_fig is not None:
            st.plotly_chart(age_bar_fig, use_container_width=True)
        else:
            st.info("Gráfico por faixa etária disponível quando houver idade e VOP válidas.")

    st.markdown("**Tabela de apoio do gráfico por faixa etária**")
    st.dataframe(age_bar_table, use_container_width=True)

    csv_data = standardized_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Baixar dados padronizados em CSV",
        data=csv_data,
        file_name="dados_vop_padronizados.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
