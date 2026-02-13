import pandas as pd
import os
import re
import subprocess
import json
import uuid
from datetime import datetime, date

import gsheets

SETTINGS_FILE = "settings.json"  # Fallback local apenas


DEFAULT_SETTINGS = {
    "categories": [
        "Moradia",
        "Alimentação (Mercado/Sacolão)",
        "Moradia",
        "Alimentação (Mercado/Sacolão)",
        "Transporte (Combustível/Estacionamento/Manutenção)",
        "Transporte (Uber/99)",
        "Saúde/Farmácia",
        "Pessoal/Vestuário",
        "Lazer/Restaurantes",
        "Assinaturas/Serviços",
        "Pets",
        "Educação/Cursos",
        "Manutenção Casa",
        "Pagamento/Crédito",
        "Outros"
    ],
    "budgets": {
        "Moradia": 2000.0,
        "Alimentação (Mercado/Sacolão)": 1200.0,
        "Transporte (Combustível/Manutenção)": 600.0,
        "Transporte (Uber/99)": 300.0,
        "Saúde/Farmácia": 400.0,
        "Pessoal/Vestuário": 300.0,
        "Lazer/Restaurantes": 600.0,
        "Assinaturas/Serviços": 200.0,
        "Pets": 200.0,
        "Educação/Cursos": 500.0,
        "Manutenção Casa": 200.0,
        "Outros": 300.0
    },
    "income_sources": {
        "Salário (Principal)": 0.0,
        "Salário (Cônjuge)": 0.0,
        "Renda Extra": 0.0,
        "VR/VA": 0.0
    }
}

def load_settings():
    """Carrega configurações: Categorias e Metas (Tabular), Outros (JSON legacy)."""
    settings = {}
    
    # 1. Carregar Legacy/Defaults (para income_sources e backup)
    legacy = {}
    try:
        legacy = gsheets.read_settings_from_sheet() or {}
    except:
        pass
        
    if not legacy and os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                legacy = json.load(f)
        except:
            pass
            
    if not legacy:
        legacy = DEFAULT_SETTINGS.copy()
        
    settings["income_sources"] = legacy.get("income_sources", DEFAULT_SETTINGS["income_sources"])
    
    # 2. Carregar Categorias (Tabular)
    try:
        cats = gsheets.read_categories()
        if not cats: # Migração ou Falha na Leitura
            print("--- Aviso: Tabela de Categorias vazia ou erro na leitura. Usando Legacy/Default. ---")
            cats = legacy.get("categories", DEFAULT_SETTINGS["categories"])
            # Tenta salvar para corrigir
            try:
                gsheets.save_categories(cats)
            except:
                pass
        else:
             print(f"--- Categorias Carregadas da Tabela: {len(cats)} itens ---")
             
        settings["categories"] = cats
    except Exception as e:
        print(f"ERRO CRÍTICO ao ler categorias tabular: {e}")
        settings["categories"] = legacy.get("categories", DEFAULT_SETTINGS["categories"])
        
    # 3. Carregar Metas (Tabular)
    try:
        budgets_df = gsheets.read_budgets()
        if budgets_df.empty: # Migração
            print("--- Migrando Metas para Tabela ---")
            # Converte dict 'default' para DF
            default_budgets = legacy.get("budgets", {}).get("default", {})
            rows = []
            for cat, val in default_budgets.items():
                rows.append({"Categoria": cat, "Valor": val, "Mes": 0, "Ano": 0})
            
            if rows:
                budgets_df = pd.DataFrame(rows)
            else:
                budgets_df = pd.DataFrame(columns=["Categoria", "Valor", "Mes", "Ano"])
                
            gsheets.save_budgets(budgets_df)
        else:
             print(f"--- Metas Carregadas da Tabela: {len(budgets_df)} linhas ---")
            
        settings["budgets_df"] = budgets_df
    except Exception as e:
        print(f"ERRO CRÍTICO ao ler metas tabular: {e}")
        settings["budgets_df"] = pd.DataFrame(columns=["Categoria", "Valor", "Mes", "Ano"])

    print("--- Settings Tabulares Carregados (Categorias + Metas) ---")
    return settings

def save_settings(settings):
    """Salva configurações. Retorna True se sucesso, False se erro."""
    success = True
    
    # 1. Salvar Abas Novas
    try:
        gsheets.save_categories(settings.get("categories", []))
        gsheets.save_budgets(settings.get("budgets_df", pd.DataFrame()))
    except Exception as e:
        print(f"ERRO ao salvar abas tabulares: {e}")
        success = False
        
    # 2. Salvar Legacy (Income)
    legacy_structure = {
        "categories": settings.get("categories", []),
        "income_sources": settings.get("income_sources", DEFAULT_SETTINGS["income_sources"]),
        "budgets": {"default": {}} 
    }
    
    try:
        current_legacy = gsheets.read_settings_from_sheet() or {}
        current_legacy["income_sources"] = settings.get("income_sources", DEFAULT_SETTINGS["income_sources"])
        current_legacy["categories"] = settings.get("categories", [])
        gsheets.write_settings_to_sheet(current_legacy)
    except Exception as e:
         print(f"Aviso: Erro ao salvar legacy JSON: {e}")
         # Não marca como falha crítica se o tabular funcionou
         
    # Backup local
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(legacy_structure, f, indent=4, ensure_ascii=False)
    except:
        pass
        
    return success

def get_budgets_for_date(settings, target_date, owner=None):
    """Retorna dict {Categoria: Valor} baseado no DataFrame de Metas (filtrando por Mês/Ano)."""
    if isinstance(target_date, (datetime, date)):
        mes = target_date.month
        ano = target_date.year
    else:
        # Se for string YYYY-MM
        try:
            parts = str(target_date).split('-')
            ano = int(parts[0])
            mes = int(parts[1])
        except:
             mes = 0
             ano = 0
             
    df = settings.get("budgets_df", pd.DataFrame())
    if df.empty:
        return {}
        
    # Garantir que coluna Tipo exista antes de selecionar
    if 'Tipo' not in df.columns:
        df['Tipo'] = 'Orçamento'

    # 1. Metas Padrão (Mes=0, Ano=0)
    defaults = df[(df["Mes"] == 0) & (df["Ano"] == 0)].set_index("Categoria")[["Valor", "Tipo"]].to_dict('index')
    
    # 2. Metas Específicas do Mês
    specifics = df[(df["Mes"] == mes) & (df["Ano"] == ano)].set_index("Categoria")[["Valor", "Tipo"]].to_dict('index')
    
    # Merge: Específicas sobrescrevem Padrão
    final_budget = defaults.copy()
    final_budget.update(specifics)
    
    # Normalizar saída: {Cat: {'Valor': X, 'Tipo': Y}}
    # Se algum não tiver Tipo, usar Orçamento
    for cat in final_budget:
        if 'Tipo' not in final_budget[cat]:
            final_budget[cat]['Tipo'] = 'Orçamento'
            
    return final_budget

def load_data():
    """Carrega os dados da planilha Google Sheets ou cria um DataFrame vazio."""
    try:
        df = gsheets.read_sheet_as_dataframe(gsheets.BASE_FINANCEIRA_ID)
        
        if df.empty:
            return create_empty_dataframe()
        
        # Converter colunas de data com format='mixed' para suportar variações
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce').dt.date
        

        # Garantir coluna reference_date
        if 'reference_date' not in df.columns:
            if 'date' in df.columns:
                 df['reference_date'] = df['date']
        else:
             df['reference_date'] = pd.to_datetime(df['reference_date'], format='mixed', errors='coerce').dt.date

        # Garantir coluna ID
        if 'id' not in df.columns:
            # df['id'] = df.apply(generate_id, axis=1) # Lento
            df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
                
        # Garantir coluna owner
        if 'owner' not in df.columns:
            df['owner'] = "Família"
        
        # Converter amount para numérico
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
                
        if 'installment_info' in df.columns:
            df = df.drop(columns=['installment_info'])
            
        return df
    except Exception as e:
        print(f"Erro ao carregar dados do Google Sheets: {e}")
        return create_empty_dataframe()

def generate_id(row=None):
    """Gera um ID único aleatório para permitir duplicatas manuais."""
    return str(uuid.uuid4())

def create_empty_dataframe():
    """Cria um DataFrame vazio com as colunas esperadas."""
    return pd.DataFrame(columns=['id', 'date', 'reference_date', 'title', 'amount', 'category', 'owner'])


def save_data(df):
    """Salva o DataFrame na planilha Google Sheets."""
    # Garantir que não salvamos colunas auxiliares
    # Garantir que não salvamos colunas auxiliares
    # dedup_idx removido do código

    
    gsheets.write_dataframe_to_sheet(df, gsheets.BASE_FINANCEIRA_ID)

def load_income_data():
    """Carrega dados de receitas do Google Sheets ou cria vazio."""
    try:
        df = gsheets.read_sheet_as_dataframe(gsheets.RECEITAS_ID)
        
        if df.empty:
            return _create_empty_income_df()
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date

        # Garante coluna reference_date
        if 'reference_date' not in df.columns:
             if 'date' in df.columns:
                 df['reference_date'] = df['date']
        else:
             df['reference_date'] = pd.to_datetime(df['reference_date'], errors='coerce').dt.date
        
        # Garante coluna owner
        if 'owner' not in df.columns:
            df['owner'] = "Família"
                
        # Forçar tipos string para evitar erro do Streamlit (TextColumn vs Float/Nan)
        text_cols = ['source', 'type', 'recurrence', 'owner']
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '').replace('None', '')
        
        # Converter amount para numérico
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
        
        return df
    except Exception as e:
        print(f"Erro ao carregar receitas do Google Sheets: {e}")
        return _create_empty_income_df()


def _create_empty_income_df():
    """Cria DataFrame vazio de receitas com tipos corretos."""
    df = pd.DataFrame(columns=['date', 'reference_date', 'source', 'amount', 'type', 'recurrence', 'owner'])
    df['source'] = df['source'].astype(str)
    df['type'] = df['type'].astype(str)
    df['recurrence'] = df['recurrence'].astype(str)
    df['owner'] = df['owner'].astype(str)
    df['amount'] = df['amount'].astype(float)
    return df


def save_income_data(df):
    """Salva dados de receitas no Google Sheets."""
    gsheets.write_dataframe_to_sheet(df, gsheets.RECEITAS_ID)

def categorize_transaction(title):
    """Categoriza a transação com base no título, usando regras refinadas."""
    title_lower = title.lower()
    
    # Regras de Negócio (Ordem importa: regras mais específicas primeiro)
    
    # 1. Receitas / Pagamentos
    if any(x in title_lower for x in ['pagamento recebido', 'ajuste a crédito', 'estorno']):
        return 'Pagamento/Crédito'
        
    # 2. Moradia (Fixo)
    if any(x in title_lower for x in ['claro', 'vivo', 'tim', 'oi', 'net', 'enel', 'sabesp', 'condominio', 'aluguel', 'iptu', 'luz', 'agua', 'gas', 'imobiliaria']):
        return 'Moradia'

    # 3. Mercado / Alimentação Essencial
    if any(x in title_lower for x in ['mercado', 'supermercado', 'assai', 'carrefour', 'pão de açúcar', 'extra', 'chama', 'açougue', 'sacolão', 'hortifruti', 'atacadista', 'hirota', 'aneto']):
        return 'Alimentação (Mercado/Sacolão)'
        
    # 4. Transporte (Carro / Combustível / Estacionamento)
    if any(x in title_lower for x in ['posto', 'abastece', 'estacionamento', 'sem par', 'veloe', 'w r car', 'ipva', 'seguro auto', 'mecanica', 'auto posto', 'gasolina', 'park']):
        return 'Transporte (Combustível/Estacionamento/Manutenção)'

    # 5. Transporte (Uber / 99)
    if any(x in title_lower for x in ['uber', '99app', '99*', 'taxi', 'pop']):
        return 'Transporte (Uber/99)'

    # 6. Saúde (Farmácia / Convênio)
    if any(x in title_lower for x in ['farmacia', 'drogasil', 'drogaria', 'drugstore', 'saude', 'hospital', 'clinica', 'medico', 'laboratorio', 'genera', 'promofarma']):
        return 'Saúde/Farmácia'
        
    # 7. Pets based on 'Cobasi', 'Petz', 'Bichosdomato'
    if any(x in title_lower for x in ['pet', 'cobasi', 'bichos', 'veterinario', 'banho e tosa']):
        return 'Pets'
        
    # 8. Assinaturas / Serviços Digitais
    if any(x in title_lower for x in ['spotify', 'netflix', 'youtube', 'prime', 'hbo', 'disney', 'nubank', 'anuidade', 'tarifa', 'google', 'apple']):
        return 'Assinaturas/Serviços'
        
    # 9. Lazer / Restaurantes
    if any(x in title_lower for x in ['ifood', 'ifd*', 'delivery', 'restaurante', 'choperia', 'padaria', 'burger', 'pizza', 'mcdonald', 'bk ', 'food', 'lanches', 'bar ', 'gastrobar', 'pizzaria', 'sorvetes', 'loteria', 'jogos', 'steam', 'cinema', 'ingresso']):
        return 'Lazer/Restaurantes'

    # 10. Pessoal / Vestuário
    if any(x in title_lower for x in ['shopee', 'aliexpress', 'amazon', 'mercadolivre', 'magalu', 'shein', 'bravium', 'confeccoes', 'magazine', 'lojas', 'store', 'roupas', 'calcados', 'perfumaria', 'cosmetico', 'cabelo', 'barbearia']):
        return 'Pessoal/Vestuário'
        
    # 11. Educação / Cursos
    if any(x in title_lower for x in ['curso', 'escola', 'faculdade', 'udemy', 'alura', 'hotmart', 'educacao']):
        return 'Educação/Cursos'
        
    # 12. Manutenção Casa
    if any(x in title_lower for x in ['leroy', 'cec', 'telhanorte', 'ferragens', 'construcao', 'telha']):
        return 'Manutenção Casa'
        
    # Default
    if 'pg *' in title_lower or 'mp *' in title_lower:
        return 'Outros' # Tenta pegar casos genéricos de maquininha
        
    return 'Outros'



import re

def extract_date_from_filename(filename):
    """
    Tenta extrair mês e ano do nome do arquivo.
    Suporta formatos: YYYY-MM, YYYYMM, YYYY-MM-DD, YYYYMMDD
    Retorna (month, year) ou (None, None) se não conseguir.
    """
    import re
    
    # Padrão 1: YYYY-MM ou YYYY-MM-DD (ex: 2026-02, 2026-02-15, fatura-2026-01)
    match = re.search(r'(\d{4})-(\d{2})(?:-\d{2})?', filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12 and 2020 <= year <= 2050:
            return month, year
    
    # Padrão 2: YYYYMMDD (ex: fatura-20260128 -> Jan/2026)
    match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2050:
            return month, year
    
    # Padrão 3: YYYY_MM (ex: nubank_2026_02)
    match = re.search(r'(\d{4})[_](\d{2})', filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12 and 2020 <= year <= 2050:
            return month, year
    
    return None, None

def clean_amount_str(val):
    """Limpa string de valor financeiro para float."""
    if isinstance(val, (int, float)): return float(val)
    val = str(val).strip()
    val = val.replace('R$', '').replace('$', '').strip()
    
    # Caso Brasileiro: 1.200,50 -> Se tem vírgula no final e ponto no meio
    if ',' in val and '.' in val:
        if val.rfind(',') > val.rfind('.'): # Ex: 1.000,00
            val = val.replace('.', '').replace(',', '.')
    elif ',' in val: # Ex: 1000,00
            val = val.replace(',', '.')
    
    try:
        return float(val)
    except:
        return None  # Retorna None se falhar

def process_uploaded_file(uploaded_file, reference_date=None, owner="Família"):
    """
    Processa arquivo CSV/Extrato e retorna dicionário com DataFrames.
    
    Returns:
        dict: {'expenses': pd.DataFrame, 'income': pd.DataFrame}
        error: str (ou None)
    """
    try:
        # 1. Ler arquivo
        try:
            df = pd.read_csv(uploaded_file)
            if len(df.columns) < 2:
                # Se detectou só 1 coluna, provavelmente o separador é ;
                raise ValueError("Separador inválido")
        except:
            uploaded_file.seek(0)
            try:
                # Tentar UTF-8 primeiro (NuBank usa UTF-8)
                # encoding_errors='replace' evita que um byte inválido force o fallback para Latin1 (que leria errado)
                df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', encoding_errors='replace')
            except:
                # Fallback para Latin1 (Bancos antigos)
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
            
        # --- Detecção de Headerless (Sem Cabeçalho) ---
        # Se a "primeira linha" (que virou header) parecer dados (ex: datas), recarregar sem header
        first_row_str = " ".join([str(c) for c in df.columns])
        
        # Procura padrão de data (DD/MM/YYYY ou YYYY-MM-DD) no header
        if re.search(r'\d{2}/\d{2}/\d{4}', first_row_str) or re.search(r'\d{4}-\d{2}-\d{2}', first_row_str):
             uploaded_file.seek(0)
             try:
                # Heurística de Separador: Ler primeira linha e contar ; vs ,
                sample_line = uploaded_file.read(2048).decode('latin1', errors='ignore').splitlines()[0]
                uploaded_file.seek(0)
                
                sep_candidate = ','
                if sample_line.count(';') >= sample_line.count(','):
                    sep_candidate = ';'
                
                df = pd.read_csv(uploaded_file, header=None, sep=sep_candidate, encoding='latin1')
             except:
                uploaded_file.seek(0)
                # Fallback: Tentar detectar automagicamente
                df = pd.read_csv(uploaded_file, header=None, sep=None, engine='python', encoding='latin1')
        
        # Normalizar colunas (mesmo que sejam int 0, 1, 2 vira '0', '1', '2')
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        col_map = {}
        
        # 2. Identificar Data
        date_cols = [c for c in df.columns if any(k in c for k in ['data', 'date', 'dia', 'dt'])]
        
        if date_cols:
            col_map['date'] = date_cols[0]
        else:
            # Fallback: tentar primeira coluna se parecer data
            if '0' in df.columns: # Heurística: Coluna 0 costuma ser Data
                 sample_date = str(df['0'].iloc[0])
                 if re.search(r'\d{2}/\d{2}|\d{4}-\d{2}', sample_date):
                     col_map['date'] = '0'
            
            if 'date' not in col_map:
                # Tentar encontrar coluna com datas via amostragem
                for col in df.columns:
                     if df[col].astype(str).str.contains(r'\d{2}/\d{2}/\d{4}').head(5).any():
                         col_map['date'] = col
                         break
                         
        if 'date' not in col_map: return None, "Coluna de Data não encontrada."
        
        # 3. Identificar Descrição
        title_cols = [c for c in df.columns if any(k in c for k in ['descri', 'title', 'historico', 'hist', 'estab', 'loja', 'nome', 'lançamento', 'lancamento'])]
        if not title_cols:
             # Fallback: Coluna 1 costuma ser Descrição
             if '1' in df.columns: col_map['title'] = '1'
             else: return None, "Coluna de Descrição não encontrada."
        else:
            col_map['title'] = title_cols[0]
        
        # 4. Identificar Valor (Smart Detection)
        # Em vez de confiar só no nome, vamos testar o conteúdo
        amount_col_candidate = None
        
        # Candidatos pelo nome
        name_candidates = [c for c in df.columns if any(k in c for k in ['valor', 'amount', 'preco', 'r$', 'saldo'])]
        
        # Verificar cada coluna numérica
        max_valid_ratio = 0
        best_col = None
        
        for col in df.columns:
            # Ignorar coluna de data já mapeada
            if col == col_map.get('date'): continue
            
            # Tentar converter amostra
            sample = df[col].astype(str).head(20).apply(clean_amount_str)
            valid_ratio = sample.notna().mean()
            
            if valid_ratio > 0.8: # Se 80% parecer número
                # Se for candidato por nome, ganha pontos extra
                score = valid_ratio
                if col in name_candidates: score += 0.2
                # Se tiver negativos, é forte indício de extrato
                if (sample.dropna() < 0).any(): score += 0.1
                # Se for coluna 2 ou 3 (comum em extratos sem header)
                if col in ['2', '3']: score += 0.15
                
                if score > max_valid_ratio:
                    max_valid_ratio = score
                    best_col = col
                    
        if best_col:
            col_map['amount'] = best_col
        else:
            return None, "Não foi possível identificar a coluna de valor automaticamente."

        # Renomear e limpar
        new_df = df.rename(columns={col_map['date']: 'date', col_map['title']: 'title', col_map['amount']: 'amount'})
        new_df = new_df[['date', 'title', 'amount']].copy()
        
        # Limpar valores
        new_df['amount'] = new_df['amount'].apply(clean_amount_str).fillna(0.0)
        
        # Limpar Datas
        iso_dates = pd.to_datetime(new_df['date'], format='%Y-%m-%d', errors='coerce')
        if iso_dates.isna().any():
            br_dates = pd.to_datetime(new_df['date'], format='%d/%m/%Y', errors='coerce')
            iso_dates = iso_dates.fillna(br_dates)
            generic_dates = pd.to_datetime(new_df['date'], dayfirst=True, errors='coerce')
            iso_dates = iso_dates.fillna(generic_dates)
            
        new_df['date'] = iso_dates.dt.date
        new_df = new_df.dropna(subset=['date'])
        
        # --- Lógica de Extrato vs Fatura ---
        is_extrato = 'extrato' in uploaded_file.name.lower()
        
        expenses_data = []
        income_data = []
        
        if is_extrato:
            # Extrato: Positivo = Receita, Negativo = Despesa
            income_rows = new_df[new_df['amount'] > 0].copy()
            expense_rows = new_df[new_df['amount'] < 0].copy()
            
            # Processar Receitas
            if not income_rows.empty:
                income_rows['source'] = income_rows['title'] # Descrição vira Fonte
                income_rows['type'] = 'Extra'
                income_rows['recurrence'] = 'Única'
                income_rows['owner'] = owner
                
                # Remover coluna 'title' para evitar duplicação visual e no banco
                income_rows = income_rows.drop(columns=['title'])
                
                # Definir reference_date para Receitas também
                if reference_date:
                    income_rows['reference_date'] = reference_date
                else:
                    income_rows['reference_date'] = income_rows['date']

                income_data = income_rows
            
            # Processar Despesas (converter para positivo)
            if not expense_rows.empty:
                expense_rows['amount'] = expense_rows['amount'].abs()
                expenses_data = expense_rows
        else:
            # Fatura / Padrão: Tudo é Despesa
            # Se vier negativo, converte pra positivo (comum em alguns csvs)
            new_df['amount'] = new_df['amount'].abs()
            expenses_data = new_df
            
        # --- Enriquecer Despesas ---
        final_expenses = pd.DataFrame()
        if hasattr(expenses_data, 'empty') and not expenses_data.empty:
            expenses_data['category'] = expenses_data['title'].apply(categorize_transaction)

            if reference_date:
                expenses_data['reference_date'] = reference_date
            else:
                expenses_data['reference_date'] = expenses_data['date']
            expenses_data['owner'] = owner
            
            # Deduplicação Intra-Arquivo

            expenses_data = expenses_data.sort_values(by=['date', 'title', 'amount'])

            # expenses_data['dedup_idx'] = ... # Removido
            expenses_data['id'] = [str(uuid.uuid4()) for _ in range(len(expenses_data))]
            final_expenses = expenses_data
            
        return {
            'expenses': final_expenses,
            'income': pd.DataFrame(income_data)
        }, None
        
    except Exception as e:
        return None, f"Erro ao processar CSV: {str(e)}"

def merge_and_save(current_df, new_df):
    """Mescla novos dados de DESPESAS com os atuais."""
    if new_df.empty: return current_df, 0
    
    if not current_df.empty and 'id' not in current_df.columns:
        current_df['id'] = current_df.apply(generate_id, axis=1)
        
    existing_ids = set(current_df['id'].values) if not current_df.empty else set()
    
    unique_new = new_df[~new_df['id'].isin(existing_ids)]
    duplicates = len(new_df) - len(unique_new)
    
    if not unique_new.empty:
        combined = pd.concat([current_df, unique_new], ignore_index=True)
        save_data(combined)
        return combined, duplicates
    return current_df, duplicates

def merge_and_save_income(current_income, new_income):
    """Mescla novos dados de RECEITAS com os atuais."""
    if new_income.empty: return current_income, 0

    # Gerar ID temporário para deduplicação (hash de campos chave)
    def get_hash(row):
        # Hash inclui reference_date se existir, senão usa date como proxy
        ref = str(row.get('reference_date', ''))
        return hash((str(row['date']), str(row['source']), str(row['amount']), str(row['owner']), ref))
    
    if not current_income.empty:
        current_hashes = set(current_income.apply(get_hash, axis=1))
    else:
        current_hashes = set()
        
    # Filtrar novas
    to_add = []
    duplicates = 0
    
    for _, row in new_income.iterrows():
        h = get_hash(row)
        if h not in current_hashes:
            to_add.append(row)
            current_hashes.add(h) # Evitar duplicar no próprio lote
        else:
            duplicates += 1
            
    if to_add:
        new_rows_df = pd.DataFrame(to_add)
        combined = pd.concat([current_income, new_rows_df], ignore_index=True)
        save_income_data(combined)
        return combined, duplicates
        
    return current_income, duplicates

def load_excel_projections(file_path):
    """Lê as projeções de Renda e Gastos da planilha Excel ('Tabelas')."""
    try:
        if not os.path.exists(file_path):
            return None, "Arquivo Excel não encontrado."
            
        df = pd.read_excel(file_path, sheet_name='Tabelas', header=None, engine='openpyxl')
        
        income_row_idx = df[df.apply(lambda row: row.astype(str).str.contains('1- Total de renda da família').any(), axis=1)].index
        
        projections = {}
        
        if not income_row_idx.empty:
            idx = income_row_idx[0]
            row_data = df.iloc[idx]
            
            col_idx = row_data[row_data.astype(str).str.contains('1- Total de renda da família', na=False)].index[0]
            
            start_col = col_idx + 1
            end_col = start_col + 12
            
            income_values = df.iloc[idx, start_col:end_col].values
            projections['income'] = list(income_values)
        else:
            projections['income'] = [0]*12
            
        return projections, None
            
    except Exception as e:
        return None, str(e)
