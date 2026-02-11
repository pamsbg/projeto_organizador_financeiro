"""
Módulo de conexão com Google Sheets via gspread.
Centraliza autenticação e operações de leitura/escrita.
"""
import sys
import os

# Adicionar diretório .packages ao path APENAS se gspread não estiver disponível
# (evita conflito de namespaces quando rodando em venv com dependências instaladas)
try:
    import gspread as _test_gspread
    del _test_gspread
except ImportError:
    _packages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".packages")
    if os.path.isdir(_packages_dir) and _packages_dir not in sys.path:
        sys.path.insert(0, _packages_dir)

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# IDs das planilhas no Google Drive
BASE_FINANCEIRA_ID = "173UZUPU5GXATVkaGGnIaDwJmd1r11YxXutNFxD5uCVs"
RECEITAS_ID = "1ZTEqYxGAJGkanYOWKw7-WftiXeIqEc882wrD_ClPX9s"
SETTINGS_ID = "1p1T_SFfmoNUQWDx17DqII8cNOuDsSdDnznk29SCKO6g"

# Escopos necessários para leitura e escrita
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """
    Cria e retorna um client gspread autenticado.
    Tenta múltiplas fontes de credenciais:
    1. st.secrets['gcp_service_account'] (Streamlit Cloud / secrets.toml)
    2. .streamlit/secrets_new.toml (fallback local)
    3. service_account.json (fallback manual)
    """
    creds_dict = None
    
    # Tentativa 1: st.secrets do Streamlit (funciona no Cloud e quando secrets.toml é legível)
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except Exception:
        pass
    
    # Tentativa 2: Ler do arquivo secrets_new.toml
    if creds_dict is None:
        try:
            import tomllib
            secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets_new.toml")
            if os.path.exists(secrets_path):
                with open(secrets_path, "rb") as f:
                    secrets = tomllib.load(f)
                creds_dict = dict(secrets["gcp_service_account"])
        except Exception:
            pass
    
    # Tentativa 3: Ler de um arquivo JSON de credenciais
    if creds_dict is None:
        try:
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_account.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    creds_dict = json.load(f)
        except Exception:
            pass
    
    if creds_dict is None:
        raise RuntimeError(
            "Credenciais do Google não encontradas. Configure st.secrets['gcp_service_account'], "
            ".streamlit/secrets_new.toml, ou service_account.json"
        )
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def read_sheet_as_dataframe(spreadsheet_id, sheet_index=0):
    """
    Lê todos os dados de uma aba (worksheet) de uma planilha Google Sheets
    e retorna como pandas DataFrame.
    
    Args:
        spreadsheet_id: ID da planilha no Google Drive
        sheet_index: Índice da aba (0 = primeira aba)
    
    Returns:
        pd.DataFrame com os dados da planilha. 
        DataFrame vazio se a planilha estiver vazia.
    """
    client = get_gspread_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.get_worksheet(sheet_index)
    
    records = worksheet.get_all_records()
    if not records:
        # Tenta pelo menos pegar o header para criar um DF vazio com colunas
        header = worksheet.row_values(1)
        if header:
            return pd.DataFrame(columns=header)
        return pd.DataFrame()
    
    return pd.DataFrame(records)


def write_dataframe_to_sheet(df, spreadsheet_id, sheet_index=0):
    """
    Sobrescreve uma aba (worksheet) com o conteúdo de um DataFrame.
    Limpa a aba e escreve header + dados.
    
    Args:
        df: pandas DataFrame para escrever
        spreadsheet_id: ID da planilha no Google Drive
        sheet_index: Índice da aba (0 = primeira aba)
    """
    client = get_gspread_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.get_worksheet(sheet_index)
    
    # Limpar todo o conteúdo existente
    worksheet.clear()
    
    if df.empty:
        # Se vazio, escrever apenas o header
        if len(df.columns) > 0:
            worksheet.update([df.columns.tolist()], value_input_option="RAW")
        return
    
    # Converter tudo para string para evitar erros de serialização
    df_str = df.copy()
    for col in df_str.columns:
        df_str[col] = df_str[col].astype(str).replace("nan", "").replace("None", "").replace("NaT", "")
    
    # Montar dados: header + linhas
    data = [df_str.columns.tolist()] + df_str.values.tolist()
    
    worksheet.update(data, value_input_option="RAW")


def read_settings_from_sheet(spreadsheet_id=SETTINGS_ID, sheet_index=0):
    """
    Lê as configurações (settings) de uma planilha Google Sheets.
    A planilha deve ter uma única célula A1 contendo o JSON das settings.
    
    Returns:
        dict com as configurações
    """
    client = get_gspread_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.get_worksheet(sheet_index)
    
    # Settings são armazenadas como JSON na célula A1
    cell_value = worksheet.acell("A1").value
    if cell_value:
        try:
            return json.loads(cell_value)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def write_settings_to_sheet(settings_dict, spreadsheet_id=SETTINGS_ID, sheet_index=0):
    """
    Salva as configurações (settings) em uma planilha Google Sheets.
    Escreve o JSON na célula A1.
    
    Args:
        settings_dict: dicionário de configurações
    """
    client = get_gspread_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.get_worksheet(sheet_index)
    
    # Limpar e escrever JSON
    worksheet.clear()
    json_str = json.dumps(settings_dict, indent=2, ensure_ascii=False)
    worksheet.update_acell("A1", json_str)
