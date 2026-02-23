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
CLASSIFICATION_ID = "1ebSYov3JxNrrfMeCTFao-UD_ohZ3gG_k9quTnEwsZc4"
RECEITAS_LIQUIDAS_ID = "1yCIzLZNOL5QHXHtuFckAcxoImJ9Pl6VdCwZPWQOn5Pc"
TRANSACOES_LIQUIDAS_ID = "18XQoRxyR8V8kpiL2JxtPQV15H0DHkKnQvhpdyHCHfFw"

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

import time
import threading
import collections
from functools import wraps
from gspread.exceptions import APIError

# --- SLIDING WINDOW RATE LIMITER ---
# O Google Sheets tem limite de 60 reads/minuto/usuário.
# Em vez de um delay fixo entre cada chamada (que torna tudo lento),
# usamos uma janela deslizante que permite rajadas rápidas e só freia
# quando estamos próximos do limite.
_api_lock = threading.Lock()
_call_timestamps = collections.deque()
_WINDOW_SIZE = 60   # janela de 60 segundos (quota reseta por minuto)
_MAX_CALLS = 55     # limite conservador (quota real = 60)

def _throttle_api():
    """Sliding window rate limiter: permite rajadas, freia perto do limite."""
    with _api_lock:
        now = time.time()
        # Limpar chamadas fora da janela de 60s
        while _call_timestamps and _call_timestamps[0] < now - _WINDOW_SIZE:
            _call_timestamps.popleft()
        
        # Se perto do limite, esperar até a chamada mais antiga sair da janela
        if len(_call_timestamps) >= _MAX_CALLS:
            wait_until = _call_timestamps[0] + _WINDOW_SIZE + 0.1
            wait = wait_until - now
            if wait > 0:
                time.sleep(wait)
                # Limpar novamente após a espera
                now = time.time()
                while _call_timestamps and _call_timestamps[0] < now - _WINDOW_SIZE:
                    _call_timestamps.popleft()
        
        _call_timestamps.append(time.time())

# --- CACHE DE SPREADSHEETS ---
# Evita chamar client.open_by_key() repetidamente para a mesma planilha.
_spreadsheet_cache = {}
_spreadsheet_cache_time = {}
_SPREADSHEET_CACHE_TTL = 300  # 5 minutos

def _get_spreadsheet(client, spreadsheet_id):
    """Retorna spreadsheet do cache ou abre e cacheia."""
    now = time.time()
    cached_time = _spreadsheet_cache_time.get(spreadsheet_id, 0)
    
    if spreadsheet_id in _spreadsheet_cache and (now - cached_time) < _SPREADSHEET_CACHE_TTL:
        return _spreadsheet_cache[spreadsheet_id]
    
    _throttle_api()
    spreadsheet = client.open_by_key(spreadsheet_id)
    _spreadsheet_cache[spreadsheet_id] = spreadsheet
    _spreadsheet_cache_time[spreadsheet_id] = now
    return spreadsheet

def _invalidate_spreadsheet_cache(spreadsheet_id=None):
    """Invalida o cache de uma planilha específica ou de todas."""
    if spreadsheet_id:
        _spreadsheet_cache.pop(spreadsheet_id, None)
        _spreadsheet_cache_time.pop(spreadsheet_id, None)
    else:
        _spreadsheet_cache.clear()
        _spreadsheet_cache_time.clear()

def retry_on_quota(max_retries=5, initial_delay=5):
    """
    Decorator para tentar novamente em caso de erro de cota (429).
    Backoff exponencial: 5s, 10s, 20s, 40s, 60s.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except APIError as e:
                    # Verifica se é erro 429 (Too Many Requests)
                    is_429 = False
                    if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 429:
                        is_429 = True
                    if not is_429 and '429' in str(e):
                        is_429 = True
                        
                    if is_429:
                        # Invalidar cache de spreadsheets (pode estar stale)
                        _invalidate_spreadsheet_cache()
                        
                        if attempt == max_retries - 1:
                            st.error("⚠️ O Google Sheets está sobrecarregado (Muitas requisições). Tente novamente em 1 minuto.")
                            raise
                        
                        effective_delay = min(delay, 60)  # Cap em 60s
                        st.toast(f"⏳ Cota do Google atingida. Aguardando {effective_delay}s... ({attempt+1}/{max_retries})")
                        time.sleep(effective_delay)
                        delay *= 2
                    else:
                        raise
            return func(*args, **kwargs)
        return wrapper
    return decorator


@retry_on_quota()
def read_sheet_as_dataframe(spreadsheet_id, sheet_index=0):
    """
    Lê todos os dados de uma aba (worksheet) de uma planilha Google Sheets
    e retorna como pandas DataFrame.
    """
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    
    _throttle_api()
    worksheet = spreadsheet.get_worksheet(sheet_index)
    
    _throttle_api()
    records = worksheet.get_all_records()
    if not records:
        # Tenta pelo menos pegar o header para criar um DF vazio com colunas
        _throttle_api()
        header = worksheet.row_values(1)
        if header:
            return pd.DataFrame(columns=header)
        return pd.DataFrame()
    
    return pd.DataFrame(records)


@retry_on_quota()
def write_dataframe_to_sheet(df, spreadsheet_id, sheet_index=0):
    """
    Sobrescreve uma aba (worksheet) com o conteúdo de um DataFrame.
    Limpa a aba e escreve header + dados.
    """
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    
    _throttle_api()
    worksheet = spreadsheet.get_worksheet(sheet_index)
    
    # Limpar todo o conteúdo existente
    _throttle_api()
    worksheet.clear()
    
    if df.empty:
        # Se vazio, escrever apenas o header
        if len(df.columns) > 0:
            _throttle_api()
            worksheet.update([df.columns.tolist()], value_input_option="RAW")
        return
    
    # Converter tudo para string para evitar erros de serialização
    df_str = df.copy()
    for col in df_str.columns:
        # Normalizar datas para formato consistente YYYY-MM-DD
        if pd.api.types.is_datetime64_any_dtype(df_str[col]):
            df_str[col] = df_str[col].dt.strftime('%Y-%m-%d').fillna('')
        else:
            df_str[col] = df_str[col].astype(str).replace("nan", "").replace("None", "").replace("NaT", "")
    
    # Montar dados: header + linhas
    data = [df_str.columns.tolist()] + df_str.values.tolist()
    
    _throttle_api()
    worksheet.update(data, value_input_option="RAW")


@retry_on_quota()
def read_settings_from_sheet(spreadsheet_id=SETTINGS_ID):
    """
    Lê as configurações (settings) da aba 'Settings' (JSON Legacy).
    """
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    
    try:
        _throttle_api()
        worksheet = spreadsheet.worksheet("Settings")
    except gspread.WorksheetNotFound:
        return None
    
    # Settings são armazenadas como JSON na célula A1
    _throttle_api()
    cell_value = worksheet.acell("A1").value
    if cell_value:
        try:
            return json.loads(cell_value)
        except (json.JSONDecodeError, TypeError):
            return None
    return None

@retry_on_quota()
def write_settings_to_sheet(settings_dict, spreadsheet_id=SETTINGS_ID):
    """
    Salva as configurações (settings) na aba 'Settings'.
    """
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    worksheet = _get_or_create_worksheet(spreadsheet, "Settings")
    
    # Limpar e escrever JSON
    _throttle_api()
    worksheet.clear()
    json_str = json.dumps(settings_dict, indent=2, ensure_ascii=False)
    _throttle_api()
    worksheet.update_acell("A1", json_str)


def _get_or_create_worksheet(spreadsheet, title, rows=100, cols=20):
    """Retorna a worksheet pelo título, criando-a se não existir."""
    try:
        _throttle_api()
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        _throttle_api()
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

@retry_on_quota()
def read_categories(spreadsheet_id=SETTINGS_ID):
    """Lê a lista de categorias da aba 'Categorias'."""
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    ws = _get_or_create_worksheet(spreadsheet, "Categorias")
    
    # Lê coluna A (pula header se houver, mas vamos assumir lista simples ou com header 'Categoria')
    _throttle_api()
    vals = ws.col_values(1)
    if not vals:
        return []
    
    if vals[0] == "Categoria":
        vals = vals[1:]
    
    # Remove vazios e duplicatas, mantém ordem alfabética
    cats = sorted(list({c.strip() for c in vals if c.strip()}))
    return cats

@retry_on_quota()
def save_categories(categories_list, spreadsheet_id=SETTINGS_ID):
    """Salva a lista de categorias na aba 'Categorias'."""
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    ws = _get_or_create_worksheet(spreadsheet, "Categorias")
    
    _throttle_api()
    ws.clear()
    _throttle_api()
    data = [["Categoria"]] + [[c] for c in categories_list]
    ws.update(data, value_input_option="RAW")

@retry_on_quota()
def read_budgets(spreadsheet_id=SETTINGS_ID):
    """Lê a tabela de metas da aba 'Metas'."""
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    ws = _get_or_create_worksheet(spreadsheet, "Metas")
    
    _throttle_api()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=["Categoria", "Valor", "Mes", "Ano"])
    
    df = pd.DataFrame(records)
    # Garantir colunas
    expected_cols = ["Categoria", "Valor", "Mes", "Ano", "Tipo"]
    for col in expected_cols:
        if col not in df.columns:
            if col == "Valor":val = 0.0
            elif col in ["Mes", "Ano"]: val = 0
            elif col == "Tipo": val = "Orçamento"
            else: val = ""
            df[col] = val
            
    return df[expected_cols]

@retry_on_quota()
def save_budgets(df, spreadsheet_id=SETTINGS_ID):
    """Salva o DataFrame de metas na aba 'Metas'."""
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    ws = _get_or_create_worksheet(spreadsheet, "Metas")
    
    _throttle_api()
    ws.clear()
    if df.empty:
        _throttle_api()
        ws.update([["Categoria", "Valor", "Mes", "Ano", "Tipo"]], value_input_option="RAW")
        return

    # Converter para lista de listas
    df_save = df.copy()
    # Tratamento de tipos
    if "Tipo" not in df_save.columns: df_save["Tipo"] = "Orçamento"
    
    df_save["Valor"] = df_save["Valor"].fillna(0.0).astype(float)
    df_save["Mes"] = df_save["Mes"].fillna(0).astype(int)
    df_save["Ano"] = df_save["Ano"].fillna(0).astype(int)
    df_save["Tipo"] = df_save["Tipo"].fillna("Orçamento").astype(str)
    
    data = [df_save.columns.tolist()] + df_save.values.tolist()
    _throttle_api()
    ws.update(data, value_input_option="RAW")


@retry_on_quota()
def read_classification_dataset(spreadsheet_id=CLASSIFICATION_ID):
    """Lê o dataset de treinamento da aba 'classificacao_categoria'."""
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    ws = _get_or_create_worksheet(spreadsheet, "classificacao_categoria")
    
    _throttle_api()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=["Descricao", "Categoria"])
    
    df = pd.DataFrame(records)
    # Garantir colunas
    if "Descricao" not in df.columns: df["Descricao"] = ""
    if "Categoria" not in df.columns: df["Categoria"] = ""
    if "Data" not in df.columns: df["Data"] = ""
    if "Valor" not in df.columns: df["Valor"] = 0.0
            
    return df[["Descricao", "Categoria", "Data", "Valor"]]

@retry_on_quota()
def append_classification(description, category, amount=None, date=None, spreadsheet_id=CLASSIFICATION_ID):
    """Adiciona um novo exemplo de treinamento na aba 'classificacao_categoria'."""
    client = get_gspread_client()
    spreadsheet = _get_spreadsheet(client, spreadsheet_id)
    ws = _get_or_create_worksheet(spreadsheet, "classificacao_categoria")
    
    # Se a aba estiver vazia, adicionar header
    _throttle_api()
    if not ws.get_all_values():
        _throttle_api()
        ws.append_row(["Descricao", "Categoria", "Data", "Valor"])
        
    val_amount = str(amount).replace(".", ",") if amount is not None else ""
    val_date = str(date) if date is not None else ""
    
    _throttle_api()
    ws.append_row([str(description), str(category), val_date, val_amount])

