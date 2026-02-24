import pandas as pd
from io import BytesIO

def limpar_valor_monetario(valor):
    if pd.isna(valor) or valor == "": 
        return 0.0
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return abs(round(float(valor), 2))
    except (ValueError, TypeError):
        return 0.0

def preparar_download_excel(df, colunas_ordem):
    """Gera o arquivo Excel para o Streamlit."""
    output = BytesIO()
    df_export = df.copy()
    
    for col in colunas_ordem:
        if col not in df_export.columns:
            df_export[col] = ""
            
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export[colunas_ordem].to_excel(writer, index=False, sheet_name='Conciliacao')
    return output.getvalue()