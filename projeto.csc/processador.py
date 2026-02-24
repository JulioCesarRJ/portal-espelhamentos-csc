import pandas as pd

def filtrar_solicitacoes(df):
    df.columns = [c.strip() for c in df.columns]

    if "DESCRICAO" in df.columns and "DESCRIÇÃO" not in df.columns:
        df['DESCRIÇÃO'] = df['DESCRICAO']
    
    mapeamento_fav = ["EMAIL FAVORECIDO DESPESA", "FAVORECIDO", "E-mail Favorecido"]
    for opcao in mapeamento_fav:
        if opcao in df.columns:
            df['EMAIL FAVORECIDO DESPESA'] = df[opcao]
            break

    STATUS_ALVO = "Em andamento"
    CATEGORIA_ALVO = "Reembolso, adiantamento e prestação de contas"

    df_f = df[
        ((df['ETAPA'] == STATUS_ALVO) | (df.get('STATUS PROTOCOLO') == STATUS_ALVO)) &
        (df['CATEGORIA'] == CATEGORIA_ALVO)
    ].copy()
    
    return df_f


def verificar_espelhamento(df_sol, df_rpt):
    df_rpt['V_COMP'] = pd.to_numeric(
        df_rpt['Valor Origem']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False),
        errors='coerce'
    ).abs().round(2).fillna(0)

    df_rpt['E_COMP'] = df_rpt['E-mail Favorecido'].astype(str).str.lower().str.strip()
    chaves_referencia = set(zip(df_rpt['E_COMP'], df_rpt['V_COMP']))

    emails = df_sol['EMAIL FAVORECIDO DESPESA'].astype(str).str.lower().str.strip()
    valores = df_sol.get('VALOR_COMP', 0)

    return [
        "SIM" if (e, v) in chaves_referencia and v > 0 else "NÃO"
        for e, v in zip(emails, valores)
    ]


def aplicar_memoria(df_atual, df_consolidado):
    if df_consolidado is None or df_consolidado.empty:
        return df_atual

    if 'PROTOCOLO' not in df_consolidado.columns or 'ESPELHAMENTO' not in df_consolidado.columns:
        return df_atual

    #Garante que LINHA exista no consolidado
    linha_cons = df_consolidado['LINHA'] if 'LINHA' in df_consolidado.columns else 0
    linha_cons = pd.Series(linha_cons).fillna(0).astype(int).astype(str)

    #Cria chave dos já resolvidos
    resolvidos_mask = df_consolidado['ESPELHAMENTO'] == 'SIM'
    chaves_resolvidas = set(
        df_consolidado.loc[resolvidos_mask, 'PROTOCOLO']
        .astype(str)
        .str.strip()
        .str.upper()
        + "-"
        + linha_cons[resolvidos_mask]
    )

    # Cria chave atual 
    linha_atual = df_atual['LINHA'] if 'LINHA' in df_atual.columns else 0
    linha_atual = pd.Series(linha_atual).fillna(0).astype(int).astype(str)

    df_atual['CHAVE_TEMP'] = (
        df_atual['PROTOCOLO']
        .astype(str)
        .str.strip()
        .str.upper()
        + "-"
        + linha_atual
    )

    #Remove já resolvidos[
    df_atual = df_atual[~df_atual['CHAVE_TEMP'].isin(chaves_resolvidas)].copy()
    df_atual.drop(columns=['CHAVE_TEMP'], inplace=True)

    return df_atual

