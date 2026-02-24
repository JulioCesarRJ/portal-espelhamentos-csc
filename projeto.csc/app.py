import streamlit as st
import pandas as pd
from utils import limpar_valor_monetario, preparar_download_excel
from processador import filtrar_solicitacoes, verificar_espelhamento
from config import ORDEM_COLUNAS_EXPORTACAO

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Portal de Espelhamentos CSC",
    layout="wide",
    page_icon="📊"
)

st.title("📊 Portal de Espelhamentos CSC")


# ======================================================
# FUNÇÃO AUXILIAR — APLICAR MEMÓRIA POR CHAVE
# ======================================================
def aplicar_data_por_chave(df_base, df_cons):
    if df_cons is None or df_cons.empty:
        return df_base

    df_cons_copy = df_cons.copy()

    df_cons_copy['LINHA'] = pd.to_numeric(
        df_cons_copy.get('LINHA', 0),
        errors='coerce'
    ).fillna(0).astype(int)

    df_cons_copy['KEY'] = (
        df_cons_copy['PROTOCOLO'].astype(str).str.strip()
        + "-"
        + df_cons_copy['LINHA'].astype(str)
    )

    mapa_datas = dict(zip(
        df_cons_copy['KEY'],
        df_cons_copy['DATA DA DESPESA']
    ))

    df_base['KEY'] = (
        df_base['PROTOCOLO'].astype(str).str.strip()
        + "-"
        + df_base['LINHA'].astype(str)
    )

    df_base['DATA DA DESPESA'] = df_base['KEY'].map(mapa_datas).fillna(
        df_base.get('DATA DA DESPESA', "")
    )

    df_base.drop(columns=['KEY'], inplace=True)

    return df_base


# ======================================================
# FUNÇÃO COM CACHE
# ======================================================
@st.cache_data(show_spinner=False)
def carregar_e_processar_inicial(file_sol, file_rpt, file_cons):
    df_sol = pd.read_csv(file_sol) if file_sol.name.endswith('.csv') else pd.read_excel(file_sol)
    df_rpt = pd.read_csv(file_rpt) if file_rpt.name.endswith('.csv') else pd.read_excel(file_rpt)
    df_cons = pd.read_excel(file_cons) if file_cons else None

    df_sol_f = filtrar_solicitacoes(df_sol)

    df_sol_f['QTD ITENS'] = pd.to_numeric(
        df_sol_f['QTD ITENS'],
        errors='coerce'
    ).fillna(1).astype(int)

    if 'DATA DA DESPESA' not in df_sol_f.columns:
        df_sol_f['DATA DA DESPESA'] = ""

    return df_sol_f, df_rpt, df_cons


# ======================================================
# UPLOAD
# ======================================================
col1, col2, col3 = st.columns(3)

with col1:
    file_sol = st.file_uploader("📂 Solicitações (Atual)", type=['csv', 'xlsx'])

with col2:
    file_rpt = st.file_uploader("📂 Arquivo RPT 53", type=['csv', 'xlsx'])

with col3:
    file_cons = st.file_uploader("📥 Consolidado Anterior (Opcional)", type=['csv', 'xlsx'])


# ======================================================
# PROCESSAMENTO PRINCIPAL
# ======================================================
if file_sol and file_rpt:

    df_sol_f, df_rpt, df_cons = carregar_e_processar_inicial(
        file_sol, file_rpt, file_cons
    )

    aba1, aba2, aba3 = st.tabs([
        "✅ Validação Simples",
        "🧩 Desmembramento Multi-Itens",
        "✉️ Gerador de Mensagens"
    ])

    # ======================================================
    # ABA 1
    # ======================================================
    with aba1:

        sol_1 = df_sol_f[df_sol_f['QTD ITENS'] == 1].copy()

        if not sol_1.empty:

            sol_1['LINHA'] = 0
            sol_1['VALOR_COMP'] = sol_1['VALOR'].apply(limpar_valor_monetario)
            sol_1['ESPELHAMENTO'] = verificar_espelhamento(sol_1, df_rpt)

            sol_1 = aplicar_data_por_chave(sol_1, df_cons)

            editado = st.data_editor(
                sol_1[['PROTOCOLO', 'DESCRIÇÃO', 'EMAIL FAVORECIDO DESPESA',
                       'ATENDENTE', 'VALOR', 'DATA DA DESPESA', 'ESPELHAMENTO']],
                hide_index=True,
                use_container_width=True,
                disabled=['PROTOCOLO', 'DESCRIÇÃO',
                          'EMAIL FAVORECIDO DESPESA', 'VALOR', 'ESPELHAMENTO'],
                key="editor_simples"
            )

            sol_1['DATA DA DESPESA'] = editado['DATA DA DESPESA']

    # ======================================================
    # ABA 2 — MULTI
    # ======================================================
    with aba2:

        sol_m = df_sol_f[df_sol_f['QTD ITENS'] >= 2].copy()

        if not sol_m.empty:

            df_exp = sol_m.loc[
                sol_m.index.repeat(sol_m['QTD ITENS'])
            ].copy()

            df_exp['LINHA'] = df_exp.groupby(level=0).cumcount() + 1

            if 'DATA DA DESPESA' not in df_exp.columns:
                df_exp['DATA DA DESPESA'] = ""

            df_exp = aplicar_data_por_chave(df_exp, df_cons)

            if df_cons is not None and not df_cons.empty:

                df_cons_copy = df_cons.copy()

                df_cons_copy['LINHA'] = pd.to_numeric(
                    df_cons_copy.get('LINHA', 0),
                    errors='coerce'
                ).fillna(0).astype(int)

                df_cons_copy['KEY'] = (
                    df_cons_copy['PROTOCOLO'].astype(str).str.strip()
                    + "-"
                    + df_cons_copy['LINHA'].astype(str)
                )

                mapa_valores = dict(zip(
                    df_cons_copy['KEY'],
                    df_cons_copy['VALOR']
                ))

                df_exp['KEY'] = (
                    df_exp['PROTOCOLO'].astype(str).str.strip()
                    + "-"
                    + df_exp['LINHA'].astype(str)
                )

                df_exp['VALOR_UNITARIO'] = df_exp['KEY'].map(mapa_valores).fillna(0.0)

                df_exp.drop(columns=['KEY'], inplace=True)

            else:
                df_exp['VALOR_UNITARIO'] = 0.0

            editado = st.data_editor(
                df_exp[['PROTOCOLO', 'LINHA', 'DESCRIÇÃO',
                        'EMAIL FAVORECIDO DESPESA', 'ATENDENTE',
                        'VALOR_UNITARIO', 'DATA DA DESPESA']],
                hide_index=True,
                use_container_width=True,
                disabled=['PROTOCOLO', 'LINHA', 'DESCRIÇÃO', 'EMAIL FAVORECIDO DESPESA'],
                key="editor_multi_itens"
            )

            df_exp['VALOR'] = editado['VALOR_UNITARIO']
            df_exp['DATA DA DESPESA'] = editado['DATA DA DESPESA']
            df_exp['VALOR_COMP'] = df_exp['VALOR'].apply(limpar_valor_monetario)
            df_exp['ESPELHAMENTO'] = verificar_espelhamento(df_exp, df_rpt)

            df_m_final = df_exp

    # ======================================================
    # ABA 3 — GERADOR
    # ======================================================
    with aba3:

        lista = []

        if 'sol_1' in locals() and not sol_1.empty:
            lista.append(sol_1)

        if 'df_m_final' in locals() and not df_m_final.empty:
            lista.append(df_m_final)

        if lista:

            df_final = pd.concat(lista)

            df_final['LINHA'] = pd.to_numeric(
                df_final.get('LINHA', 0),
                errors='coerce'
            ).fillna(0).astype(int)

            df_final['VALOR_COMP'] = df_final['VALOR'].apply(limpar_valor_monetario)
            df_final['ESPELHAMENTO'] = verificar_espelhamento(df_final, df_rpt)

            st.subheader("✉️ Mensagens para Atendentes")

            novos_matches = df_final[df_final['ESPELHAMENTO'] == "SIM"].copy()

            if df_cons is not None:

                df_cons['LINHA'] = pd.to_numeric(
                    df_cons.get('LINHA', 0),
                    errors='coerce'
                ).fillna(0).astype(int)

                ja_notificados = set(
                    df_cons[df_cons['ESPELHAMENTO'] == 'SIM']['PROTOCOLO'].astype(str)
                    + "-"
                    + df_cons['LINHA'].astype(str)
                )

                novos_matches['CHAVE'] = (
                    novos_matches['PROTOCOLO'].astype(str)
                    + "-"
                    + novos_matches['LINHA'].astype(str)
                )

                novos_matches = novos_matches[
                    ~novos_matches['CHAVE'].isin(ja_notificados)
                ]

            if novos_matches.empty:
                st.info("Nenhum novo espelhamento encontrado.")
            else:
                for at, dados in novos_matches.groupby('ATENDENTE'):

                    msg = f"Boa tarde, {at}. Tudo bom?\n\n"
                    msg += "Foram identificadas despesas espelhadas nos protocolos abaixo:\n"

                    for r in dados.itertuples():
                        msg += f"\n- Protocolo: {r.PROTOCOLO} | Valor: R$ {r.VALOR_COMP:.2f}"

                    st.code(msg, language="text")

            excel_out = preparar_download_excel(
                df_final,
                ORDEM_COLUNAS_EXPORTACAO
            )

            st.download_button(
                "📥 Baixar Planilha Consolidada",
                excel_out,
                "conciliacao_consolidada.xlsx"
            )
