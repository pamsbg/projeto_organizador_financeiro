import pandas as pd
import os
import re

import json
import uuid
from datetime import datetime, date

DATA_FILE = "base_financeira.csv"
INCOME_FILE = "receitas.csv"
SETTINGS_FILE = "settings.json"

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
    """Carrega configurações (categorias e orçamentos)."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS

def save_settings(settings):
    """Salva configurações."""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

def get_budgets_for_date(settings, target_date, owner=None):
    """Retorna os orçamentos aplicáveis para uma data (Mês/Ano) e Pessoa."""
    # Formato da chave de período: YYYY-MM ou YYYY-MM_Owner
    if isinstance(target_date, (datetime, date)):
        date_str = target_date.strftime("%Y-%m")
    else:
        date_str = str(target_date)

    all_budgets = settings.get("budgets", {})
    
    # Se owner for "Todos" ou None, precisamos de uma estratégia.
    # Estratégia: Retornar a SOMA de todos os budgets definidos para aquele mês?
    # Ou retornar um budget "Geral" se existir?
    # Vamos assumir:
    # 1. Se tem Owner específico (Renato, Pamela): Retorna o budget dele. Se não existir, retorna Default dele? Ou Default Geral?
    #    Vamos Tentar: YYYY-MM_Renato -> Default_Renato -> Default -> Zerado.
    
    if owner and owner != "Todos":
        keys_to_try = [f"{date_str}_{owner}", f"default_{owner}", f"{date_str}", "default"]
    else:
        # Se for TODOS, queremos visualizar o GLOBAL.
        # O ideal seria somar os individuais. Mas por enquanto, vamos pegar o "Geral" (sem sufixo) se existir,
        # ou somar Renato+Pamela+Familia se existirem?
        # Simplificação: Use o budget base (sem sufixo) como "Geral/Família" se não tiver owner.
        keys_to_try = [date_str, "default"]

    # Buscar o primeiro que existir (Hierarquia de herança)
    # Mas espere, se eu estou definindo budget para o Renato em Fev/2026, eu quero criar uma entrada nova.
    # Na leitura:
    final_budget = {}
    
    # Se formos somar (Todos), a lógica é diferente.
    if owner == "Todos":
        # Iterar sobre todas as chaves que começam com date_str e somar?
        # É complexo. Vamos mudar a abordagem:
        # O "Todos" vê a SOMA dos budgets de (Renato + Pamela + Família) para aquele mês.
        
        # 1. Pega Default (Base)
        base = all_budgets.get("default", {}).copy()
        
        # 2. Soma específicos do mês se existirem
        # Essa lógica de soma é perigosa se o usuário não definiu tudo.
        # Vamos manter simples: "Todos" vê o orçamento da "Família" (sem dono) + Somas?
        # Decisão: O "Todos" é apenas visualização. Vamos somar tudo que encontrarmos para aquele mês.
        
        merged_budget = {}
        # Inicializa com categorias
        for cat in settings.get("categories", []):
            merged_budget[cat] = 0.0
            
        found_any = False
        for key, val in all_budgets.items():
            if key.startswith(date_str): # Ex: 2026-02, 2026-02_Renato
                found_any = True
                for c, v in val.items():
                    merged_budget[c] = merged_budget.get(c, 0.0) + v
        
        if not found_any:
             return all_budgets.get("default", {})
             
        return merged_budget

    # Caso Owner Específico
    current_key = f"{date_str}_{owner}"
    if current_key in all_budgets:
        return all_budgets[current_key]
        
    # Se não tem específico do mês, tenta Default do Owner
    if f"default_{owner}" in all_budgets:
        return all_budgets[f"default_{owner}"]
        
    # Se não tem, retorna vazio ou default geral?
    # Melhor retornar vazio para forçar o usuário a definir? Ou herdar do geral?
    # Se o usuário pediu "separar", melhor não herdar do geral para não duplicar.
    # Retorna ZERO para começar limpo.
    return {c: 0.0 for c in settings.get("categories", [])}

def update_budget_for_date(settings, target_date, new_budgets, owner=None):
    """Atualiza o orçamento para um período e dono específicos."""
    date_str = target_date.strftime("%Y-%m")
    
    key = date_str
    if owner and owner != "Todos":
        key = f"{date_str}_{owner}"
    
    if "budgets" not in settings:
        settings["budgets"] = {}
        
    settings["budgets"][key] = new_budgets
    return settings

def load_data():
    """Carrega os dados do arquivo CSV ou cria um DataFrame vazio se não existir."""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            
            # Converter colunas de data com format='mixed' para suportar variações (com/sem hora)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce').dt.date
            
            # Garantir coluna reference_date
            if 'reference_date' not in df.columns:
                if 'date' in df.columns:
                     df['reference_date'] = df['date']
            else:
                 df['reference_date'] = pd.to_datetime(df['reference_date'], format='mixed', errors='coerce').dt.date
            
            # Se sobrar NaT (erro de conversão), preenche com hoje ou dropa?
            # Melhor não dropar silenciosamente, mas por enquanto vamos manter assim.
            
            # Garantir coluna ID
            if 'id' not in df.columns:
                df['dedup_idx'] = df.groupby(['date', 'title', 'amount']).cumcount()
                df['id'] = df.apply(generate_id, axis=1)
                
            # Garantir coluna owner
            if 'owner' not in df.columns:
                df['owner'] = "Família"
                
            return df
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            return create_empty_dataframe()
    else:
        return create_empty_dataframe()

def generate_id(row):
    """Gera um ID único aleatório para permitir duplicatas manuais (solicitação do usuário)."""
    # O usuário pediu para NÃO remover duplicatas automaticamente.
    # Usando UUID, cada linha importada será um novo registro, mesmo que idêntica.
    return str(uuid.uuid4())

def create_empty_dataframe():
    """Cria um DataFrame vazio com as colunas esperadas."""
    return pd.DataFrame(columns=['id', 'date', 'reference_date', 'title', 'amount', 'category', 'installment_info', 'owner'])

def save_data(df):
    """Salva o DataFrame no arquivo CSV."""
    # Garantir que não salvamos colunas auxiliares se não quiser
    if 'dedup_idx' in df.columns:
        df = df.drop(columns=['dedup_idx'])
    df.to_csv(DATA_FILE, index=False)

def load_income_data():
    """Carrega dados de receitas ou cria vazio."""
    if os.path.exists(INCOME_FILE):
        try:
            df = pd.read_csv(INCOME_FILE, encoding='utf-8')
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
            
            # Garante coluna owner
            if 'owner' not in df.columns:
                df['owner'] = "Família"
                
            # Forçar tipos string para evitar erro do Streamlit (TextColumn vs Float/Nan)
            text_cols = ['source', 'type', 'recurrence', 'owner']
            for col in text_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace('nan', '')
            
            return df
        except:
            return pd.DataFrame(columns=['date', 'source', 'amount', 'type', 'recurrence', 'owner'])
    else:
        df = pd.DataFrame(columns=['date', 'source', 'amount', 'type', 'recurrence', 'owner'])
        # Inicializa com tipos corretos
        df['source'] = df['source'].astype(str)
        df['type'] = df['type'].astype(str)
        df['recurrence'] = df['recurrence'].astype(str)
        df['owner'] = df['owner'].astype(str)
        df['amount'] = df['amount'].astype(float)
        return df

def save_income_data(df):
    """Salva dados de receitas."""
    df.to_csv(INCOME_FILE, index=False, encoding='utf-8')

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

def extract_installment_info(title):
    """Detecta informações de parcelamento no título (ex: Parcela 2/10)."""
    match = re.search(r'Parcela\s+(\d+)/(\d+)', title, re.IGNORECASE)
    if match:
        return match.group(0) # Retorna "Parcela X/Y"
    return None

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

def process_uploaded_file(uploaded_file, reference_date=None, owner="Família"):
    """Processa arquivo CSV genérico (vários bancos) e retorna DataFrame padronizado."""
    try:
        # Tentar ler com diferentes encodings e separadores
        try:
            df = pd.read_csv(uploaded_file)
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
            
        # Normalizar colunas
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Mapeamento de Colunas Inteligente
        col_map = {}
        
        # 1. Identificar Data
        date_cols = [c for c in df.columns if any(k in c for k in ['data', 'date', 'dia', 'dt'])]
        if not date_cols: return None, "Coluna de Data não encontrada."
        col_map['date'] = date_cols[0]
        
        # 2. Identificar Descrição
        # Adicionado 'lançamento' (Itaú) e variantes
        title_cols = [c for c in df.columns if any(k in c for k in ['descri', 'title', 'historico', 'estab', 'loja', 'nome', 'lançamento', 'lancamento'])]
        if not title_cols: return None, "Coluna de Descrição não encontrada."
        col_map['title'] = title_cols[0]
        
        # 3. Identificar Valor
        amount_cols = [c for c in df.columns if any(k in c for k in ['valor', 'amount', 'preco', 'r$'])]
        if not amount_cols: return None, "Coluna de Valor não encontrada."
        col_map['amount'] = amount_cols[0]
        
        # Renomear para padrão
        new_df = df.rename(columns={col_map['date']: 'date', col_map['title']: 'title', col_map['amount']: 'amount'})
        new_df = new_df[['date', 'title', 'amount']].copy()
        
        # --- Limpeza de Dados ---
        
        # Valor: Tratar formato brasileiro (1.000,00) ou americano (1,000.00)
        def clean_amount(val):
            if isinstance(val, (int, float)): return float(val)
            val = str(val).strip()
            # Se tem R$, tira
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
                return 0.0

        new_df['amount'] = new_df['amount'].apply(clean_amount)
        
        # Data: Tentar converter múltiplos formatos para evitar erros com YYYY-MM-DD vs DD/MM/YYYY
        # 1. Tentar ISO primeiro (YYYY-MM-DD) - Comum CSVs Nubank/Estrangeiros
        iso_dates = pd.to_datetime(new_df['date'], format='%Y-%m-%d', errors='coerce')
        
        # 2. Tentar BR (DD/MM/YYYY) para os que falharam
        if iso_dates.isna().any():
            br_dates = pd.to_datetime(new_df['date'], format='%d/%m/%Y', errors='coerce')
            iso_dates = iso_dates.fillna(br_dates)
            
            # 3. Fallback genérico (dayfirst=True)
            generic_dates = pd.to_datetime(new_df['date'], dayfirst=True, errors='coerce')
            iso_dates = iso_dates.fillna(generic_dates)
            
        new_df['date'] = iso_dates.dt.date
        new_df = new_df.dropna(subset=['date']) # Remove linhas sem data válida
        
        # Categorização e Enriquecimento
        new_df['category'] = new_df['title'].apply(categorize_transaction)
        new_df['installment_info'] = new_df['title'].apply(extract_installment_info)
        
        # Referência
        if reference_date:
            new_df['reference_date'] = reference_date
        else:
            new_df['reference_date'] = new_df['date']
            
        # Owner
        new_df['owner'] = owner
            
        # --- Deduplicação Intra-Arquivo (Mesmo dia, mesmo valor, mesmo nome) ---
        new_df = new_df.sort_values(by=['date', 'title', 'amount'])
        new_df['dedup_idx'] = new_df.groupby(['date', 'title', 'amount']).cumcount()
            
        # ID Único
        new_df['id'] = new_df.apply(generate_id, axis=1)
        
        return new_df, None
    except Exception as e:
        return None, f"Erro ao processar CSV: {str(e)}"

def merge_and_save(current_df, new_df):
    """Mescla novos dados com os atuais, usando ID para remover duplicatas."""
    
    # Se o ID não existir no current_df (caso de migração), gera
    if not current_df.empty and 'id' not in current_df.columns:
        current_df['id'] = current_df.apply(generate_id, axis=1)
        
    # Filtrar apenas novos IDs que não estão no current_df
    existing_ids = set(current_df['id'].values) if not current_df.empty else set()
    
    # Identificar duplicatas
    unique_new_df = new_df[~new_df['id'].isin(existing_ids)]
    duplicates_count = len(new_df) - len(unique_new_df)
    
    if not unique_new_df.empty:
        # Concatena
        combined = pd.concat([current_df, unique_new_df], ignore_index=True)
        save_data(combined)
        return combined, duplicates_count
    else:
        return current_df, duplicates_count

def load_excel_projections(file_path):
    """Lê as projeções de Renda e Gastos da planilha Excel ('Tabelas')."""
    try:
        if not os.path.exists(file_path):
            return None, "Arquivo Excel não encontrado."
            
        # Carregar planilha Tabelas
        # Renda: A linha "1- Total de renda da família" geralmente está na linha 17 (index 15 ou 16 dependendo do header)
        # Vamos ler sem header e achar a linha.
        df = pd.read_excel(file_path, sheet_name='Tabelas', header=None, engine='openpyxl')
        
        # Localizar a linha de "Total de renda da família"
        income_row_idx = df[df.apply(lambda row: row.astype(str).str.contains('1- Total de renda da família').any(), axis=1)].index
        
        projections = {}
        
        if not income_row_idx.empty:
            idx = income_row_idx[0]
            row_data = df.iloc[idx]
            
            # Achar a coluna onde esta o texto
            col_idx = row_data[row_data.astype(str).str.contains('1- Total de renda da família', na=False)].index[0]
            
            # Pegar os próximos 12 valores (Jan..Dez)
            # Nota: col_idx é label. Valores começam em col_idx + 1
            # Importante: O pandas read_excel(header=None) usa ints 0, 1, 2 para colunas.
            start_col = col_idx + 1
            end_col = start_col + 12
            
            income_values = df.iloc[idx, start_col:end_col].values
            projections['income'] = list(income_values)
        else:
            projections['income'] = [0]*12 # Fallback
            
        return projections, None
            
    except Exception as e:
        return None, str(e)
