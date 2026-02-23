import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import uuid
import utils
import utils
import os
import time
import ml_patterns
import gsheets

# Configuração da Página
st.set_page_config(page_title="Organizador Financeiro", layout="wide", page_icon="💰")

# --- LOGIN SYSTEM ---
def check_password():
    """Retorna True se o usuário logar corretamente."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.title("🔒 Acesso Restrito")
    st.markdown("Este sistema é privado. Por favor, digite a senha de acesso.")

    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        correct_password = None
        
        # Tentativa 1: st.secrets (Streamlit Cloud / secrets.toml)
        try:
            correct_password = st.secrets["password"]
        except (FileNotFoundError, KeyError):
            pass
        
        # Tentativa 2: secrets_new.toml (fallback local)
        if correct_password is None:
            try:
                import tomllib
                secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets_new.toml")
                if os.path.exists(secrets_path):
                    with open(secrets_path, "rb") as f:
                        secrets = tomllib.load(f)
                    correct_password = secrets.get("password")
            except Exception:
                pass
        
        # Tentativa 3: Variável de ambiente
        if correct_password is None:
            correct_password = os.environ.get("APP_PASSWORD")
        
        if correct_password is None:
            st.error("⚠️ Senha não configurada!")
            st.code("Esperado em secrets.toml: password = '...'", language="toml")
            return False

        if password == correct_password:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Senha incorreta.")
            
    return False

if not check_password():
    st.stop() # Para a execução aqui se não estiver logado

# --- FIM DO LOGIN ---

# --- PRIVACY MODE ---
if "privacy_mode" not in st.session_state:
    st.session_state.privacy_mode = False

def toggle_privacy():
    st.session_state.privacy_mode = not st.session_state.privacy_mode

# Injetar CSS de Borrão se ativado
if st.session_state.privacy_mode:
    st.markdown("""
        <style>
            /* Borrar APENAS os valores das métricas (stMetric) */
            div[data-testid="stMetricValue"] { filter: blur(10px) !important; transition: filter 0.3s; }
            /* Remover blur genérico de tabelas/gráficos que estava borrando textos */
        </style>
    """, unsafe_allow_html=True)

def get_privacy_data(df_to_mask):
    """
    Retorna uma cópia do DataFrame com valores numéricos mascarados se o modo privado estiver ativo.
    Máscara APENAS colunas monetárias/sensíveis.
    """
    if not st.session_state.privacy_mode or df_to_mask.empty:
        return df_to_mask
    
    masked_df = df_to_mask.copy()
    
    # Lista de termos que INDICAM valor financeiro (Case Insensitive)
    monetary_keywords = ['valor', 'amount', 'total', 'meta', 'realizado', 'diferença', 'saldo', 'entrada', 'saída', 'receita', 'despesa', 'gasto', 'r$', 'balance']
    
    # Lista de termos para EXCLUIR explicitamente (Case Insensitive)
    exclude_keywords = ['ano', 'mês', 'dia', 'data', 'percent', '%', 'qtd', 'quantidade', 'id', 'idx', 'hash', 'code', 'score', 'nota', 'parcela', 'tipo']
    
    target_cols = []
    
    for col in masked_df.columns:
        col_lower = str(col).lower()
        
        # 1. Verificar se é exclúido
        if any(ex in col_lower for ex in exclude_keywords):
            continue
            
        # 2. Verificar se é numérico
        is_numeric = pd.api.types.is_numeric_dtype(masked_df[col])
        
        # 3. Se for numérico E tiver palavra-chave monetária, mascara
        if is_numeric:
            if any(mon in col_lower for mon in monetary_keywords):
                target_cols.append(col)
                
        # 4. Se não for numérico mas o nome for MUITO forte (ex: "Valor (R$)"), mascara também
        # (Streamlit às vezes formata como string antes)
        elif any(mon in col_lower for mon in monetary_keywords):
             target_cols.append(col)

    # Aplicar máscara
    for col in target_cols:
        masked_df[col] = "****"
        
    return masked_df

# Título Principal com Botão de Privacidade
col_title, col_privacy = st.columns([0.9, 0.1])
with col_title:
    st.title("💰 Organizador Financeiro Família Guerra Possa")
with col_privacy:
    # Botão de Olho
    eye_icon = "🙈" if st.session_state.privacy_mode else "👁️"
    if st.button(eye_icon, key="privacy_toggle", help="Ocultar/Exibir Valores", on_click=toggle_privacy):
        pass # Ação feita no on_click (rerun automático)

# Carregar Dados
if 'df' not in st.session_state:
    st.session_state.df = utils.load_data()

df = st.session_state.df

# Carregar Dados de Receitas (Global)
if 'income_df' not in st.session_state:
    st.session_state.income_df = utils.load_income_data()

income_df = st.session_state.income_df

# Carregar Configurações
if 'settings' not in st.session_state:
    st.session_state.settings = utils.load_settings()

settings = st.session_state.settings

if st.session_state.get("just_refreshed"):
    st.toast("Dados e Configurações atualizados da Nuvem (Google Sheets)!", icon="☁️")
    st.session_state.just_refreshed = False

# --- SIDEBAR: CONFIGURAÇÕES ---
with st.sidebar:
    if st.button("🔄 Atualizar Dados"):
        st.session_state.df = utils.load_data()
        st.session_state.income_df = utils.load_income_data()
        st.session_state.settings = utils.load_settings()
        
        # Regenerar dados líquidos
        try:
            rec_liq = utils.compute_receitas_liquidas(
                st.session_state.income_df, st.session_state.df, st.session_state.settings
            )
            utils.save_receitas_liquidas(rec_liq)
            
            trans_liq = utils.compute_transacoes_liquidas(
                st.session_state.df, st.session_state.settings
            )
            utils.save_transacoes_liquidas(trans_liq)
        except Exception as e:
            st.warning(f"⚠️ Erro ao gerar dados líquidos: {e}")
        
        st.session_state.just_refreshed = True
        st.rerun()

    # Filtro de Pessoa (Global para TODAS as abas)
    # Movido para cima para afetar a exibição dos totais
    owner_filter = st.selectbox("Filtrar por Pessoa", ["Todos", "Pamela", "Renato", "Família"], key="global_owner_filter")

    # Calcular Totais Filtrados
    filtered_trans_count = len(df)
    filtered_income_count = len(income_df)
    
    if owner_filter != "Todos":
        if 'owner' in df.columns:
            filtered_trans_count = len(df[df['owner'] == owner_filter])
        if 'owner' in income_df.columns:
            filtered_income_count = len(income_df[income_df['owner'] == owner_filter])

    st.divider()
    
    # Exibir Totais
    col_kpi1, col_kpi2 = st.columns(2)
    
    # Excluir Aplicações contagem de Transações
    filtered_trans_count_kpi = filtered_trans_count
    if not df.empty:
        meta_cats_kpi = utils.get_meta_categories(settings)
        mask_kpi = pd.Series(True, index=df.index)
        if owner_filter != "Todos" and 'owner' in df.columns:
            mask_kpi &= (df['owner'] == owner_filter)
        
        cond_meta_kpi = df['category'].isin(meta_cats_kpi) if meta_cats_kpi else pd.Series(False, index=df.index)
        cond_title_kpi = df['title'].astype(str).str.contains('aplica', case=False, na=False)
        
        mask_kpi &= ~(cond_meta_kpi | cond_title_kpi)
        filtered_trans_count_kpi = len(df[mask_kpi])
            
    val_trans = filtered_trans_count_kpi
    
    # Calcular contagem de Receitas na Sidebar (exclui resgates individuais, +1 se houver rendimento)
    filtered_income_net_count = 0
    
    if not income_df.empty:
        inc_for_count = income_df.copy()
        if owner_filter != "Todos" and 'owner' in inc_for_count.columns:
            inc_for_count = inc_for_count[inc_for_count['owner'] == owner_filter]
        
        # Contar receitas excluindo resgates individuais
        non_resgates = inc_for_count[~inc_for_count['source'].astype(str).str.contains('resgate', case=False, na=False)]
        filtered_income_net_count = len(non_resgates)
        
        # Calcular se há rendimento líquido para adicionar +1 na contagem
        total_resgatado_sb = inc_for_count[inc_for_count['source'].astype(str).str.contains('resgate', case=False, na=False)]['amount'].sum()
        
        total_aplicado_sb = 0
        if not df.empty:
            df_sb = df.copy()
            if owner_filter != "Todos" and 'owner' in df_sb.columns:
                df_sb = df_sb[df_sb['owner'] == owner_filter]
            meta_cats_sb = utils.get_meta_categories(settings)
            cond_meta_sb = df_sb['category'].isin(meta_cats_sb) if meta_cats_sb else pd.Series(False, index=df_sb.index)
            cond_title_sb = df_sb['title'].astype(str).str.contains(r'aplica[çc][ãa]o\s+rdb', case=False, na=False, regex=True)
            total_aplicado_sb = df_sb[cond_meta_sb | cond_title_sb]['amount'].sum()
        
        if total_aplicado_sb > 0 or total_resgatado_sb > 0:
            filtered_income_net_count += 1
        
    val_rec = filtered_income_net_count
    
    if st.session_state.privacy_mode:
        val_trans = "****"
        val_rec = "****"
        
    col_kpi1.metric("Receitas", val_rec, help="Resgates não são contabilizados como receita")
    col_kpi2.metric("Transações", val_trans)
    
    st.divider()
    
    # Filtro de Visualização (Global)
    view_mode_global = st.radio("Visualizar por:", ["Mês de Referência", "Data da Transação"], key="global_view_mode")
    
    st.header("⚙️ Configurações")
    
    with st.expander("Gerenciar Categorias"):
        new_cat = st.text_input("Nova Categoria")
        new_cat_type = st.selectbox("Tipo da Categoria", ["Orçamento", "Meta"], index=0, help="Orçamento: Limite de Gastos\nMeta: Objetivo de Ganho/Economia")
        
        if st.button("Adicionar"):
            if new_cat and new_cat not in settings["categories"]:
                settings["categories"].append(new_cat)
                # Adicionar linha padrão no DF de metas se não existir
                if "budgets_df" in settings:
                     new_row = pd.DataFrame([{"Categoria": new_cat, "Valor": 0.0, "Mes": 0, "Ano": 0, "Tipo": new_cat_type}])
                     settings["budgets_df"] = pd.concat([settings["budgets_df"], new_row], ignore_index=True)
                
                if utils.save_settings(settings):
                    st.success(f"Categoria '{new_cat}' adicionada!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Erro ao salvar categoria na nuvem via gspread.")
            elif new_cat in settings["categories"]:
                st.warning("Categoria já existe.")
        
        cat_to_remove = st.selectbox("Remover Categoria", options=settings["categories"])
        if st.button("Remover"):
            if cat_to_remove in settings["categories"]:
                settings["categories"].remove(cat_to_remove)
                # Remove do DataFrame de Metas
                if "budgets_df" in settings:
                    df_b = settings["budgets_df"]
                    settings["budgets_df"] = df_b[df_b["Categoria"] != cat_to_remove]
                
                if utils.save_settings(settings):
                    st.success(f"Categoria '{cat_to_remove}' removida!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Erro ao remover categoria da nuvem.")

    st.divider()
    with st.expander("🗑️ Zona de Perigo (Apagar Dados)"):
        st.warning("Atenção: Ações aqui não podem ser desfeitas.")
        
        # Opção 1: Limpar Mês/Ano
        st.subheader("Limpar Período")
        col_del1, col_del2 = st.columns(2)
        with col_del1:
            del_month = st.selectbox("Mês", range(1, 13), index=datetime.now().month-1, key="del_m")
        with col_del2:
            del_year = st.selectbox("Ano", range(2024, 2031), index=2, key="del_y")
        
        # Checkboxes para o que apagar
        del_expenses = st.checkbox("Apagar Despesas (Transações)", value=True)
        del_income = st.checkbox("Apagar Receitas", value=False)
        
        st.info("ℹ️ Isso apaga os dados do **Banco de Dados (Planilha)**. Seus arquivos CSV originais no Google Drive **não** são afetados. Para restaurar, você precisará importar novamente.")

        if st.button("🗑️ Confirmar Exclusão"):
            if not del_expenses and not del_income:
                st.warning("Selecione pelo menos um tipo de dado para apagar.")
            else:
                msg_success = []
                
                # Coluna de data a usar depende do modo de visualização
                del_date_col = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
                
                # Apagar Despesas
                if del_expenses and not df.empty:
                    # Garantir datetime
                    use_col = del_date_col if del_date_col in df.columns else 'date'
                    df['dt_obj'] = pd.to_datetime(df[use_col], format='mixed', errors='coerce')
                    mask_keep = ~((df['dt_obj'].dt.month == del_month) & (df['dt_obj'].dt.year == del_year))
                    
                    deleted_exp = len(df) - mask_keep.sum()
                    new_df_kept = df[mask_keep].drop(columns=['dt_obj'])
                    st.session_state.df = new_df_kept
                    utils.save_data_and_refresh_liquidas(new_df_kept, st.session_state.income_df, st.session_state.settings)
                    msg_success.append(f"Despesas ({deleted_exp} itens)")

                # Apagar Receitas
                if del_income:
                    # Carregar receitas atuais para garantir que temos o último estado
                    curr_income = utils.load_income_data()
                    
                    if not curr_income.empty:
                        use_col = del_date_col if del_date_col in curr_income.columns else 'date'
                        curr_income['dt_temp'] = pd.to_datetime(curr_income[use_col], format='mixed', errors='coerce')
                        
                        total_before = len(curr_income)
                        
                        mask_inc_keep = ~((curr_income['dt_temp'].dt.month == del_month) & (curr_income['dt_temp'].dt.year == del_year))
                        new_inc_kept = curr_income[mask_inc_keep].copy()
                        
                        total_after = len(new_inc_kept)
                        deleted_count = total_before - total_after
                        
                        if deleted_count > 0:
                            if 'dt_temp' in new_inc_kept.columns:
                                new_inc_kept = new_inc_kept.drop(columns=['dt_temp'])
                            
                            cols_to_save = [c for c in new_inc_kept.columns if not c.startswith('_')]
                            new_inc_kept = new_inc_kept[cols_to_save]
                            
                            utils.save_income_and_refresh_liquidas(new_inc_kept, st.session_state.df, st.session_state.settings)
                            msg_success.append(f"Receitas ({deleted_count} itens)")
                        else:
                            st.warning(f"Nenhuma receita encontrada em {del_month}/{del_year}.")

                if msg_success:
                     st.cache_data.clear() # Forçar limpeza de cache
                     st.success(f"Sucesso! {', '.join(msg_success)} apagados.")
                     time.sleep(2)
                     st.rerun()
                elif not del_expenses: # Se só marcou receitas e não achou nada
                     st.warning("Nenhum dado encontrado para apagar nos critérios selecionados.")
                
        # Opção 2: Reset Total
        if st.button("🔥 APAGAR TUDO (Reset)"):
            # 1. Apagar Despesas
            utils.save_data_and_refresh_liquidas(pd.DataFrame(columns=df.columns), None, st.session_state.settings)
            st.session_state.df = utils.load_data()
            
            # 2. Apagar Receitas
            curr_inc = utils.load_income_data()
            if not curr_inc.empty:
                utils.save_income_and_refresh_liquidas(pd.DataFrame(columns=curr_inc.columns), st.session_state.df, st.session_state.settings)
                st.session_state.income_df = utils.load_income_data()
            
            st.cache_data.clear()
            st.success("Todos os dados (Despesas e Receitas) foram apagados.")
            time.sleep(1.5)
            st.rerun()

# Criar Abas (Ordem Solicitada: 1 - Importar, 2 - Receitas, 3 - Transações, 4 - Projeções, 5 - Dashboard , 6 - Metas)
tab2, tab1, tab3, tab6, tab4, tab5 = st.tabs(["📥 Importar", "💰 Receitas", "📝 Transações", "🔮 Projeções", "📊 Dashboard", "🎯 Metas"])

# --- ABA 1: RECEITAS (NOVO LOCAL) ---
with tab1:
    st.header("💰 Gerenciar Entradas (Salários, Rendas)")
    st.markdown("Adicione aqui suas fontes de renda. Você pode detalhar por data e pessoa.")
    
    # Filtro de Mês/Ano
    col_rec_filter1, col_rec_filter2 = st.columns(2)
    with col_rec_filter1:
        months = {0: "Todos", 1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 
                  6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        current_month = datetime.now().month
        selected_month_rec = st.selectbox("Mês", options=list(months.keys()), format_func=lambda x: months[x], 
                                          index=current_month, key="rec_month")  # Default: mês atual
    
    with col_rec_filter2:
        current_year = datetime.now().year
        years = [0] + list(range(2024, 2031))
        selected_year_rec = st.selectbox("Ano", options=years, format_func=lambda x: "Todos" if x == 0 else str(x), 
                                         index=years.index(current_year) if current_year in years else 0, key="rec_year")
    
    
    # Usar DataFrame do Session State (já carregado globalmente)
    # Atualiza session state se necessário (ex: reload)
    full_income_df = st.session_state.income_df
    
    # IMPORTANTE: Criar IDs únicos ANTES de qualquer filtro para rastrear deleções
    # Usa hash do conteúdo para garantir consistência
    if not full_income_df.empty:
        full_income_df['_temp_id'] = full_income_df.apply(
            lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                            str(row.get('amount', '')), str(row.get('owner', '')),
                            str(row.get('reference_date', '')))), 
            axis=1
        ).astype(str)
    
    # Aplicar filtros APENAS para visualização (não altera o DataFrame original)
    display_income = full_income_df.copy()
    
    if not display_income.empty and 'date' in display_income.columns:
        display_income['date'] = pd.to_datetime(display_income['date'], format='mixed', errors='coerce')
        if 'reference_date' in display_income.columns:
            display_income['reference_date'] = pd.to_datetime(display_income['reference_date'], format='mixed', errors='coerce')
        
        # Escolher coluna de filtro baseado no modo de visualização
        filter_col_rec = 'reference_date' if view_mode_global == "Mês de Referência" and 'reference_date' in display_income.columns else 'date'
        
        # Filtrar por mês (0 = Todos)
        if selected_month_rec != 0:
            display_income = display_income[display_income[filter_col_rec].dt.month == selected_month_rec]
        
        # Filtrar por ano (0 = Todos)
        if selected_year_rec != 0:
            display_income = display_income[display_income[filter_col_rec].dt.year == selected_year_rec]
    
    # Filtro Visual de Pessoa (Se selecionado pessoa específica)
    if owner_filter != "Todos":
        if 'owner' not in display_income.columns: display_income['owner'] = "Família"
        display_income = display_income[display_income['owner'] == owner_filter]
        st.caption(f"Editando receitas de: **{owner_filter}**")
    else:
        st.caption("Editando **Todas** as receitas")
    # --- LÓGICA VISUAL: APLICAÇÃO - RESGATE (Linha Sintética) ---
    # Calcular Aplicações (Transações) - Resgates (Receitas) do mês filtrado
    total_aplicado_rec = 0.0
    if not st.session_state.df.empty:
        df_aplic = st.session_state.df.copy()
        date_col_aplic = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
        if date_col_aplic not in df_aplic.columns: date_col_aplic = 'date'
        
        if not pd.api.types.is_datetime64_any_dtype(df_aplic[date_col_aplic]):
            df_aplic[date_col_aplic] = pd.to_datetime(df_aplic[date_col_aplic], errors='coerce')
        
        # Filtros de data e pessoa
        mask_aplic = pd.Series(True, index=df_aplic.index)
        if selected_month_rec != 0: mask_aplic &= (df_aplic[date_col_aplic].dt.month == selected_month_rec)
        if selected_year_rec != 0: mask_aplic &= (df_aplic[date_col_aplic].dt.year == selected_year_rec)
        if owner_filter != "Todos" and 'owner' in df_aplic.columns: mask_aplic &= (df_aplic['owner'] == owner_filter)
        
        # Encontrar aplicações (Estruturado estritamente apenas para Aplicação RDB)
        cond_title = df_aplic['title'].astype(str).str.contains(r'aplica[çc][ãa]o\s+rdb', case=False, na=False, regex=True)
        
        mask_aplic &= cond_title
        total_aplicado_rec = df_aplic[mask_aplic]['amount'].sum()
        
    total_resgatado_rec = 0.0
    if not display_income.empty:
        resgates = display_income[display_income['source'].astype(str).str.contains('resgate', case=False, na=False)]
        total_resgatado_rec = resgates['amount'].sum()
        
        # Esconder os resgates individuais da tabela visual
        display_income = display_income[~display_income['source'].astype(str).str.contains('resgate', case=False, na=False)]
        
    rendimento_liquido = abs(total_aplicado_rec - total_resgatado_rec)
    
    # Adicionar o rendimento líquido como uma linha virtual no display_income
    if total_aplicado_rec > 0 or total_resgatado_rec > 0:
        synth_row = pd.DataFrame([{
            "date": pd.Timestamp.now().normalize(),
            "reference_date": pd.Timestamp.now().normalize(),
            "source": f"Aplicação RDB - Resgate RDB",
            "amount": rendimento_liquido,
            "type": "Extra",
            "recurrence": "Única",
            "owner": owner_filter if owner_filter != "Todos" else "Família",
            "_temp_id": "SYNTHETIC_ROW_DO_NOT_EDIT"
        }])
        display_income = pd.concat([synth_row, display_income], ignore_index=True)
    # -----------------------------------------------------

    # --- Filtros visuais (Search + Sort)
    col_search, col_sort_toggles = st.columns([2, 3])
    with col_search:
        search_term_inc = st.text_input("🔍 Buscar Receita", placeholder="Ex: Salário, Rendimento...", key="search_income")
    
    # --- EDIÇÃO EM MASSA (TOGGLE) ---
    with col_sort_toggles:
        st.write("") # Spacer
        bulk_edit_mode = st.checkbox("✅ Ativar Edição em Massa", key="bulk_mode_toggle", help="Permite alterar várias linhas de uma vez. Marque para habilitar checkboxes.")
    
    if search_term_inc and 'source' in display_income.columns:
         display_income = display_income[display_income['source'].astype(str).str.contains(search_term_inc, case=False, na=False)]

    # Ordenação (Igual transações)
    st.caption("Ordenar por:")
    col_sort_inc = st.columns(5) # Aumentar colunas
    sort_opts_inc = ["Data", "Mês Ref.", "Fonte", "Valor", "Pessoa"]
    sort_cols_map_inc = {"Data": "date", "Mês Ref.": "reference_date", "Fonte": "source", "Valor": "amount", "Pessoa": "owner"}
    
    active_sorts_inc = []
    sort_ascending_inc = []
    
    for i, col_name in enumerate(sort_opts_inc):
        with col_sort_inc[i]:
             clicked = st.checkbox(col_name, key=f"sort_inc_{col_name}")
             if clicked:
                 active_sorts_inc.append(sort_cols_map_inc[col_name])
                 # Direção para cada coluna
                 direction = st.radio("Direção", ["Asc", "Desc"], key=f"dir_inc_{col_name}", label_visibility="collapsed", horizontal=True)
                 sort_ascending_inc.append(True if direction == "Asc" else False)

    if active_sorts_inc:
        if 'date' in display_income.columns:
             display_income['date'] = pd.to_datetime(display_income['date'], errors='coerce')
        if 'reference_date' in display_income.columns:
             display_income['reference_date'] = pd.to_datetime(display_income['reference_date'], errors='coerce')
        display_income = display_income.sort_values(by=active_sorts_inc, ascending=sort_ascending_inc)

    # Resetar index para editor
    display_income = display_income.reset_index(drop=True)
    
    # --- LÓGICA DE EDIÇÃO EM MASSA ---
    if bulk_edit_mode:
        if "Selecionar" not in display_income.columns:
            display_income.insert(0, "Selecionar", False)
        
        # Configuração das Colunas para Edição em Massa
        column_config_bulk = {
            "Selecionar": st.column_config.CheckboxColumn("Selecionar", default=False, width="small"),
            "date": st.column_config.DateColumn("Data da Transação", format="DD/MM/YYYY", disabled=True),
            "reference_date": st.column_config.DateColumn("Mês de Referência", format="MM/YYYY", disabled=True),
            "source": st.column_config.TextColumn("Fonte de Renda", disabled=True),
            "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", disabled=True),
            "type": st.column_config.TextColumn("Tipo", disabled=True), # Visualização apenas por enquanto
            "owner": st.column_config.TextColumn("Pessoa", disabled=True),
            "_temp_id": None
        }
        
        st.info("ℹ️ Marque a caixa 'Selecionar' nas linhas que deseja alterar. Dica: Clique e arraste para selecionar várias!")
        
        edited_df_bulk = st.data_editor(
            display_income,
            column_config=column_config_bulk,
            hide_index=True,
            use_container_width=True,
            key="bulk_editor_income",
            disabled=["date", "reference_date", "source", "amount", "type", "owner"] # Travar tudo exceto Checkbox
        )
        
        # BARRA DE AÇÕES EM MASSA
        selected_rows = edited_df_bulk[edited_df_bulk["Selecionar"] == True]
        count_selected = len(selected_rows)
        
        if count_selected > 0:
            st.markdown(f"### 📝 Editando {count_selected} itens selecionados")
            
            with st.form("bulk_action_form_income"):
                col_b1, col_b2, col_b3 = st.columns(3)
                
                with col_b1:
                    new_bulk_type = st.selectbox("Novo Tipo", ["(Manter Atual)", "Fixo", "Variável", "Extra"])
                with col_b2:
                    new_bulk_owner = st.selectbox("Nova Pessoa", ["(Manter Atual)", "Pamela", "Renato", "Família"])
                with col_b3:
                    new_bulk_date = st.date_input("Nova Data", value=None)
                
                if st.form_submit_button("🚀 Aplicar Mudanças em Massa"):
                    # Processar Atualização
                    ids_to_update = selected_rows['_temp_id'].tolist()
                    
                    if not ids_to_update:
                         st.warning("Nenhum ID encontrado.")
                    else:
                        # Carregar o DF completo para aplicar as mudanças
                        full_income_to_update = utils.load_income_data()
                        
                        # Recriar _temp_id para o full_income_to_update para encontrar as linhas
                        if not full_income_to_update.empty:
                            full_income_to_update['date'] = pd.to_datetime(full_income_to_update['date'], errors='coerce')
                            if 'reference_date' in full_income_to_update.columns:
                                full_income_to_update['reference_date'] = pd.to_datetime(full_income_to_update['reference_date'], errors='coerce')
                            
                            full_income_to_update['_temp_id'] = full_income_to_update.apply(
                                lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                                                str(row.get('amount', '')), str(row.get('owner', '')),
                                                str(row.get('reference_date', '')))), 
                                axis=1
                            ).astype(str)

                        mask = full_income_to_update['_temp_id'].isin(ids_to_update)
                        
                        changes_made = False
                        if new_bulk_type != "(Manter Atual)":
                            full_income_to_update.loc[mask, 'type'] = new_bulk_type
                            changes_made = True
                            
                        if new_bulk_owner != "(Manter Atual)":
                            full_income_to_update.loc[mask, 'owner'] = new_bulk_owner
                            changes_made = True
                        
                        if new_bulk_date is not None:
                            full_income_to_update.loc[mask, 'date'] = pd.to_datetime(new_bulk_date)
                            changes_made = True
                            
                        if changes_made:
                            # Remover _temp_id antes de salvar
                            full_income_to_update = full_income_to_update.drop(columns=['_temp_id'])
                            utils.save_income_and_refresh_liquidas(full_income_to_update, st.session_state.df, st.session_state.settings)
                            st.session_state.income_df = full_income_to_update # Atualizar globalmente
                            st.success(f"✅ {count_selected} receitas atualizadas com sucesso!")
                            time.sleep(1)
                            st.rerun()
                            
    # --- FIM LÓGICA EM MASSA ---

    # Editor de Receitas
    # Se modo privacidade, usar dataframe estático mascarado
    elif st.session_state.privacy_mode:
         st.dataframe(
             get_privacy_data(display_income), 
             use_container_width=True, 
             hide_index=True,
             column_config={
                "_temp_id": None # Ocultar
             }
         )
         edited_income = display_income # Sem edição
    else:
        # Prevenção pro PyArrow: Garantir que as colunas visíveis de data sejam estritamente datetime64 do Pandas
        if 'date' in display_income.columns:
            display_income['date'] = pd.to_datetime(display_income['date'], errors='coerce')
        if 'reference_date' in display_income.columns:
            display_income['reference_date'] = pd.to_datetime(display_income['reference_date'], errors='coerce')
            
        edited_income = st.data_editor(
            display_income,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
            "date": st.column_config.DateColumn("Data da Transação", format="DD/MM/YYYY"),
            "reference_date": st.column_config.DateColumn("Mês de Referência", format="MM/YYYY"),
            "source": st.column_config.TextColumn("Fonte de Renda"),
            "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "type": st.column_config.SelectboxColumn("Tipo", options=["Fixo", "Variável", "Extra"]),
            "recurrence": st.column_config.SelectboxColumn("Recorrência", options=["Mensal", "Única", "Anual"]),
            "owner": st.column_config.SelectboxColumn("Pessoa", options=["Pamela", "Renato", "Família"]),
            "_temp_id": None # Esconder ID
        }, 
        key="income_editor"
    )
    
    if st.button("💾 Salvar Alterações de Receita"):
        # REFATORAÇÃO: Usar mesmo padrão de Transações (consistência!)
        # 1. Carregar DataFrame completo do disco
        full_income = utils.load_income_data()
        if 'owner' not in full_income.columns: 
            full_income['owner'] = "Família"
        
        # 2. Criar _temp_id no full_income (source of truth)
        if not full_income.empty:
            # Garantir tipos consistentes para hash
            full_income['date'] = pd.to_datetime(full_income['date'], errors='coerce')
            if 'reference_date' in full_income.columns:
                 full_income['reference_date'] = pd.to_datetime(full_income['reference_date'], errors='coerce')
            
            full_income['_temp_id'] = full_income.apply(
                lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                                str(row.get('amount', '')), str(row.get('owner', '')),
                                str(row.get('reference_date', '')))), 
                axis=1
            ).astype(str)
        
        # 3. Aplicar filtros para determinar quais NÃO tocar
        full_income['date'] = pd.to_datetime(full_income['date'], errors='coerce')
        
        # Máscara para receitas fora do filtro = preservar
        # LÓGICA CORRETA: Preservar SE está fora de QUALQUER filtro (OR logic)
        # - Mês diferente OR Ano diferente OR Pessoa diferente
        
        # Inicializar com False (nada preservado por padrão)
        mask_keep = pd.Series([False] * len(full_income), index=full_income.index)
        
        # Preservar se está em mês diferente
        if selected_month_rec != 0:
            mask_keep = mask_keep | (full_income['date'].dt.month != selected_month_rec)
        else:
            # Se "Todos" os meses, não filtrar por mês (manter False para permitir outros filtros)
            pass
        
        # Preservar se está em ano diferente
        if selected_year_rec != 0:
            mask_keep = mask_keep | (full_income['date'].dt.year != selected_year_rec)
        
        # Preservar se pertence a pessoa diferente
        if owner_filter != "Todos":
            mask_keep = mask_keep | (full_income['owner'] != owner_filter)
            
        # [CORREÇÃO CRÍTICA]: Preservar INCONDICIONALMENTE os resgates invisíveis da tabela
        # Como o Resgate não aparece no `display_income`, se ele não for protegido aqui
        # o algoritmo deduzirá que o usuário apagou ele e destruirá o banco inteiro!
        mask_keep = mask_keep | (full_income['source'].astype(str).str.contains('resgate', case=False, na=False))
        
        untouched_income = full_income[mask_keep].copy()
        
        # 4. Detectar deleções comparando hashes
        if '_temp_id' in display_income.columns and not display_income.empty:
            original_ids_shown = set(display_income['_temp_id'].dropna())
            
            if edited_income.empty:
                edited_ids = set()  # Todas deletadas
            elif '_temp_id' in edited_income.columns:
                edited_ids = set(edited_income['_temp_id'].dropna())
            else:
                edited_ids = set()  # Sem hash = assume novas
            
            deleted_ids = original_ids_shown - edited_ids
            
            # Remover deletadas de untouched
            if deleted_ids and '_temp_id' in untouched_income.columns:
                untouched_income = untouched_income[~untouched_income['_temp_id'].isin(deleted_ids)]
        
        # 5. Processar edited_income: separar editadas vs novas
        if not edited_income.empty:
            # Com _temp_id = editadas, sem _temp_id = novas
            if '_temp_id' in edited_income.columns:
                edited_existing = edited_income[edited_income['_temp_id'].notna()].copy()
                new_rows = edited_income[edited_income['_temp_id'].isna()].copy()
            else:
                # Sem coluna hash = todas são novas
                edited_existing = pd.DataFrame()
                new_rows = edited_income.copy()
            
            # Limpar _temp_id das editadas
            if not edited_existing.empty and '_temp_id' in edited_existing.columns:
                edited_existing = edited_existing.drop(columns=['_temp_id'])
            
            # Limpar _temp_id das novas (se houver)
            if not new_rows.empty and '_temp_id' in new_rows.columns:
                new_rows = new_rows.drop(columns=['_temp_id'])
            
            # Combinar: untouched + editadas + novas
            final_income = pd.concat([untouched_income, edited_existing, new_rows], ignore_index=True)
        else:
            # Vazio = só manter untouched
            final_income = untouched_income.copy()
        
        # 6. Limpar _temp_id e IGNORAR linhas sintéticas antes de salvar
        if '_temp_id' in final_income.columns:
            # Nunca salva o ID temporário do Pandas DataFrame no CSV
            final_income = final_income[final_income['_temp_id'] != "SYNTHETIC_ROW_DO_NOT_EDIT"]
            final_income = final_income.drop(columns=['_temp_id'])
            
        # Reforço extra: Garantir que 'Aplicação RDB - Resgate RDB' não passe
        if 'source' in final_income.columns:
            final_income = final_income[final_income['source'] != "Aplicação RDB - Resgate RDB"]
        
        # 7. Salvar
        # 7. Salvar e Atualizar Session State
        utils.save_income_and_refresh_liquidas(final_income, st.session_state.df, st.session_state.settings)
        st.session_state.income_df = final_income # Atualizar globalmente
        
        st.success("✅ Receitas atualizadas com sucesso!")
        st.rerun()

# --- ABA 2: IMPORTAR ---
with tab2:
    st.header("Importar Extratos e Faturas")
    st.markdown("Importe arquivos CSV do seu banco (Nubank, Itaú, etc).")
    
    col_upload1, col_upload2 = st.columns(2)
    
    with col_upload1:
        uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
        
    with col_upload2:
        # Configurações da Importação
        st.subheader("Configurar Importação")
        
        # Data de Referência (Mês/Ano da Fatura)
        months = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                  7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        
        is_extract = False
        if uploaded_file and "extrato" in uploaded_file.name.lower():
            is_extract = True
            
        # Dono da Fatura (Sempre perguntar)
        imp_owner = st.selectbox("De quem é essa fatura/extrato?", ["Família", "Pamela", "Renato"], index=0, key="imp_owner")

        if is_extract:
            st.info("📂 **Modo Extrato Detectado**")
            st.markdown("O mês de referência será definido **automaticamente** pela data de cada transação.")
            # Variáveis para compatibilidade
            imp_month = 0
            imp_year = 0
        else:
            # Tenta adivinhar mês/ano do arquivo se possível (ex: nubank_2026-02.csv)
            default_month = datetime.now().month
            default_year = datetime.now().year
            
            if uploaded_file:
                 extracted_month, extracted_year = utils.extract_date_from_filename(uploaded_file.name)
                 if extracted_month and extracted_year:
                     if 1 <= extracted_month <= 12 and 2020 <= extracted_year <= 2050:
                         default_month = extracted_month
                         default_year = extracted_year
                         st.success(f"🗓️ Detectado: {months[default_month]}/{default_year}")
                     else:
                         st.warning(f"⚠️ Data extraída inválida do arquivo. Usando data atual.")

            imp_month = st.selectbox("Mês de Referência", list(months.keys()), format_func=lambda x: months[x], index=default_month-1, key="imp_month")
            imp_year = st.selectbox("Ano de Referência", range(2024, 2031), index=default_year-2024, key="imp_year")
        
        st.markdown("---")
        
    if uploaded_file:
        if st.button("Processar Arquivo"):
            try:
                # Se for extrato, ref_date = None (usa data da transação)
                if is_extract:
                    ref_date = None
                else:
                    ref_date = date(imp_year, imp_month, 1)
                
                new_data, error = utils.process_uploaded_file(uploaded_file, reference_date=ref_date, owner=imp_owner)
                
                if error:
                    st.error(error)
                else:
                    # new_data agora é um dict {'expenses': df, 'income': df}
                    st.session_state.temp_import_data = new_data
                    st.session_state.temp_import_meta = {"ref": ref_date, "owner": imp_owner}
                    
                    msg = "Arquivo processado!"
                    exp_count = len(new_data['expenses'])
                    inc_count = len(new_data['income'])
                    
                    if exp_count > 0: msg += f" {exp_count} despesas."
                    if inc_count > 0: msg += f" {inc_count} receitas."
                    
                    st.success(msg)

            except Exception as e:
                st.error(f"Erro Crítico ao processar arquivo: {str(e)}")
                # Opcional: imprimir traceback no terminal para debug
                import traceback
                print(traceback.format_exc())
                
    # Se já processou, mostrar preview e botão confirmar
    if 'temp_import_data' in st.session_state and st.session_state.temp_import_data is not None:
        st.divider()
        st.subheader("Pré-visualização dos Dados")
        
        import_data = st.session_state.temp_import_data
        has_expenses = not import_data['expenses'].empty
        has_income = not import_data['income'].empty
        
        # Configuração comum de colunas para preview
        preview_cols = {
            "id": None, "dedup_idx": None,
            "date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "reference_date": st.column_config.DateColumn("Mês de Referência", format="MM/YYYY"),
            "title": st.column_config.TextColumn("Descrição"),
            "source": st.column_config.TextColumn("Fonte"),
            "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "category": st.column_config.TextColumn("Categoria"),
            "owner": st.column_config.TextColumn("Pessoa"),
            "type": st.column_config.TextColumn("Tipo"),
            "recurrence": st.column_config.TextColumn("Recorrência")
        }

        # Preview de Receitas (se houver)
        if has_income:
            st.markdown("### 💰 Receitas a Importar")
            st.dataframe(get_privacy_data(import_data['income'].head(5)), use_container_width=True, column_config=preview_cols)
            if len(import_data['income']) > 5:
                st.caption(f"... e mais {len(import_data['income']) - 5} receitas.")
                
        # Preview de Despesas (se houver)
        if has_expenses:
            st.markdown("### 📝 Despesas a Importar")
            st.dataframe(import_data['expenses'].head(5), use_container_width=True, column_config=preview_cols)
            if len(import_data['expenses']) > 5:
                st.caption(f"... e mais {len(import_data['expenses']) - 5} despesas.")
        
        col_act1, col_act2 = st.columns(2)
        
        with col_act1:
            if st.button("✅ Confirmar e Salvar no Banco de Dados"):
                # 1. Salvar Despesas
                duplicates_exp = 0
                new_exp_count = 0
                
                if has_expenses:
                    current_df = st.session_state.df
                    new_exp_df = import_data['expenses']
                    combined_df, duplicates_exp = utils.merge_and_save(current_df, new_exp_df)
                    st.session_state.df = combined_df # Atualiza estado
                    new_exp_count = len(new_exp_df) - duplicates_exp

                # 2. Salvar Receitas
                duplicates_inc = 0
                new_inc_count = 0
                
                if has_income:
                    # Carregar receitas atuais para mesclar
                    current_income = utils.load_income_data()
                    new_inc_df = import_data['income']
                    
                    combined_inc, duplicates_inc = utils.merge_and_save_income(current_income, new_inc_df)
                    st.session_state.income_df = combined_inc # Atualiza estado para sidebar
                    new_inc_count = len(new_inc_df) - duplicates_inc
                
                # Limpar temp
                del st.session_state.temp_import_data
                
                # === GERAR DADOS LÍQUIDOS ===
                # Recalcular receitas e transações líquidas com os dados atualizados
                try:
                    current_income_full = st.session_state.get('income_df', utils.load_income_data())
                    current_trans_full = st.session_state.df
                    
                    # Receitas líquidas (sem resgates + rendimento sintético)
                    rec_liq = utils.compute_receitas_liquidas(
                        current_income_full, current_trans_full, st.session_state.settings
                    )
                    utils.save_receitas_liquidas(rec_liq)
                    
                    # Transações líquidas (sem aplicações/metas)
                    trans_liq = utils.compute_transacoes_liquidas(
                        current_trans_full, st.session_state.settings
                    )
                    utils.save_transacoes_liquidas(trans_liq)
                    
                    st.info("📊 Dados líquidos atualizados com sucesso!")
                except Exception as e:
                    st.warning(f"⚠️ Dados líquidos não puderam ser gerados: {e}")
                
                # Relatório
                st.success("Importação Concluída!")
                
                if new_exp_count > 0:
                    st.info(f"📝 {new_exp_count} novas despesas adicionadas.")
                if new_inc_count > 0:
                    st.info(f"💰 {new_inc_count} novas receitas adicionadas.")
                    
                if duplicates_exp > 0 or duplicates_inc > 0:
                    st.warning(f"Ignorados (duplicados): {duplicates_exp} despesas, {duplicates_inc} receitas.")
                    
                st.rerun()
                
        with col_act2:
            if st.button("❌ Cancelar"):
                del st.session_state.temp_import_data
                st.rerun()

# --- ABA 3: TRANSAÇÕES ---
with tab3:
    st.header("Gerenciar Transações")
    
    # Se dataframe estiver vazio, cria estrutura para permitir adição
    if df.empty:
        display_df = utils.create_empty_dataframe()
    else:
        display_df = df.copy()

    # --- MÁGICO DE CATEGORIZAÇÃO ---
    if not df.empty:
        import ml_patterns  # Importação do módulo de aprendizado
        
        # Sincronização Automática de Categorias (DESATIVADO A PEDIDO DO USUÁRIO)
        # Motivo: Usuário quer deletar categorias e garantir que elas não voltem sozinhas,
        # mesmo que existam no histórico de transações.
        # unique_cats_in_df = set(df['category'].dropna().unique())
        # # Remove vazios e NaNs da lista de candidatos
        # unique_cats_in_df = {c for c in unique_cats_in_df if isinstance(c, str) and c.strip() and c.lower() not in ['nan', 'none']}
        
        # current_settings_cats = set(settings.get("categories", []))
        # new_cats_found = list(unique_cats_in_df - current_settings_cats)
        
        # if new_cats_found:
        #     new_cats_found.sort()
        #     # st.toast(f"Novas categorias detectadas: {', '.join(new_cats_found)}. Salvando...", icon="💾")
        #     # settings["categories"].extend(new_cats_found)
        #     # settings["categories"] = sorted(list(set(settings["categories"]))) # Remove dups e ordena
        #     # st.session_state.settings = settings # Atualiza session state
        #     # utils.save_settings(settings) # Salva no Google Sheets
        #     # time.sleep(1) # Breve pausa para garantir update visual
        #     # st.rerun() # Recarrega para que o dropdown use a nova lista imediatamente
        pass

    # --- MÁGICO DE CATEGORIZAÇÃO (COM MENU SUSPENSO) ---
    with st.expander("🧙‍♂️ Mágico de Categorização (IA + Aprendizado)", expanded=False):
        st.write("Analisa suas transações usando **Regras fixas** e **Padrões aprendidos**.")
        st.info("💡 **Dica:** Ao clicar em 'Aplicar', o sistema aprende suas correções para o futuro!")

        col_wiz1, col_wiz2 = st.columns(2)
        with col_wiz1:
             wiz_target = st.multiselect("Escopo da Busca:", ["Vazias", "Outros/Geral", "Todas as Categorias"], default=["Vazias"])
        
        # Carregar histórico de aprendizado (Cache resource para não ler toda hora)
        # Carregar histórico de aprendizado
        # Usando utils para evitar erro de escopo no cache do streamlit
        ml_history_df = utils.load_ml_history_cached()

        # Treinar modelo com histórico + dados atuais
        learned_patterns = ml_patterns.learn_patterns_from_data(df, ml_history_df)
        
        # Identificar transações sem categoria ("Outros" ou vazias)
        uncategorized = df[df['category'].isin(['Outros', '', None])].copy()
        
        if not uncategorized.empty:
            st.info(f"Encontrei {len(uncategorized)} transações para analisar.")
            
            if st.button("🔍 Buscar Sugestões"):
                # Aprende com dados históricos
                learned_patterns = ml_patterns.learn_patterns_from_data(df, ml_history_df)
                
                wiz_suggestions = []
                for idx, row in df.iterrows():
                    # Normalizar categoria atual para verificação
                    current_cat = str(row['category']).strip()
                    if current_cat.lower() in ['nan', 'none']: 
                        current_cat = ""

                    # Identificar tipo
                    is_empty = (current_cat == "")
                    is_others = (current_cat in ['Outros', 'Geral'])
                    
                    # Filtro de Inclusão
                    include = False
                    if "Todas as Categorias" in wiz_target: include = True
                    if "Vazias" in wiz_target and is_empty: include = True
                    if "Outros/Geral" in wiz_target and is_others: include = True
                    
                    if not include: continue

                    # 1. Tenta regras fixas primeiro
                    suggested = utils.categorize_transaction(row['title'])
                    
                    # 2. Se regras não deram resultado, usa aprendizado
                    if not suggested or suggested == 'Outros':
                        suggested = ml_patterns.suggest_category_from_learned(
                            title=row['title'], 
                            learned_patterns=learned_patterns,
                            amount=row['amount']
                        )
                    
                    # MUDANÇA: Mostra TODAS as transações do escopo, mesmo sem sugestão
                    # Se não conseguiu sugerir, deixa vazio para edição manual
                    if not suggested or suggested == row['category']:
                        suggested = ""  # Vazio = usuário pode escolher manualmente
                    
                    wiz_suggestions.append({
                        "id": row['id'],
                        "Data": row['date'],
                        "Descrição": row['title'],
                        "Valor": row['amount'],
                        "Pessoa": row.get('owner', 'Família'),  # NOVO: Mostrar pessoa
                        "Categoria Atual": row['category'],
                        "Nova Categoria": suggested,
                        "Aplicar?": True if suggested else False
                    })
                
                if wiz_suggestions:
                    df_wiz = pd.DataFrame(wiz_suggestions)
                    
                    # CORREÇÃO DE ERRO PYARROW: Garantir tipos compatíveis
                    # Converter Data para datetime (coerce errors)
                    if 'Data' in df_wiz.columns:
                        df_wiz['Data'] = pd.to_datetime(df_wiz['Data'], errors='coerce')
                    
                    # Converter Valor para float
                    if 'Valor' in df_wiz.columns:
                        df_wiz['Valor'] = pd.to_numeric(df_wiz['Valor'], errors='coerce').fillna(0.0)
                    
                    # Converter Texto para string (evitar misturar None/float/str)
                    text_cols = ['Descrição', 'Pessoa', 'Categoria Atual', 'Nova Categoria']
                    for col in text_cols:
                        if col in df_wiz.columns:
                            df_wiz[col] = df_wiz[col].astype(str).replace('nan', '').replace('None', '')

                    st.session_state.wiz_suggestions = df_wiz
                    auto_suggestions = len([s for s in wiz_suggestions if s["Nova Categoria"]])
                    st.success(f"Mostrando {len(wiz_suggestions)} transações ({auto_suggestions} com sugestão automática).")
                    st.info(f"📚 Aprendi padrões de {len(learned_patterns)} palavras-chave do seu histórico.")
                else:
                    st.info("Nenhuma transação encontrada no escopo selecionado.")
                    if 'wiz_suggestions' in st.session_state: 
                        del st.session_state.wiz_suggestions
            
            # Mostrar Tabela de Sugestões
            if 'wiz_suggestions' in st.session_state and not st.session_state.wiz_suggestions.empty:
                st.markdown("### Transações para Categorizar")
                st.caption("✏️ Você pode editar a 'Nova Categoria' manualmente. Deixe em branco para não alterar.")
                
                # SANITIZAÇÃO DE EMERGÊNCIA (Antes de Exibir)
                # Garante que, mesmo se o cache estiver sujo, os tipos sejam corrigidos agora.
                wiz_df_display = st.session_state.wiz_suggestions.copy()
                
                if 'Data' in wiz_df_display.columns:
                     wiz_df_display['Data'] = pd.to_datetime(wiz_df_display['Data'], errors='coerce')
                
                if 'Valor' in wiz_df_display.columns:
                     wiz_df_display['Valor'] = pd.to_numeric(wiz_df_display['Valor'], errors='coerce').fillna(0.0)
                
                edited_wiz = st.data_editor(
                    wiz_df_display,
                    column_config={
                        "id": None, 
                        "Descrição": st.column_config.TextColumn("Descrição", width="large", help="Descrição original do banco"),
                        "Categoria Atual": st.column_config.TextColumn("Categoria Atual", width="large"),
                        "Valor": st.column_config.NumberColumn(
                            "Valor (R$)",
                            format="R$ %.2f",
                            width="small"
                        ),
                        "Pessoa": st.column_config.TextColumn("Pessoa", width="small"),
                        "Nova Categoria": st.column_config.SelectboxColumn(
                            "Nova Categoria",
                            options=[""] + settings["categories"],
                            required=False,
                            width="large"
                        ),
                        "Aplicar?": st.column_config.CheckboxColumn("Aplicar?", default=True, width="small")
                    },
                    disabled=["Data", "Descrição", "Valor", "Pessoa", "Categoria Atual"],
                    hide_index=True,
                    use_container_width=False,
                    key="wizard_table"
                )
                
                if st.button("✨ Aplicar Selecionados", key="wizard_apply_btn"):
                    count = 0
                    for index, row in edited_wiz.iterrows():
                        if row["Aplicar?"] and row["Nova Categoria"] and row["Nova Categoria"].strip():
                            # Atualiza somente se tiver uma categoria válida
                            mask = st.session_state.df['id'] == row['id']
                            st.session_state.df.loc[mask, 'category'] = row['Nova Categoria']
                            
                            # PERSISTÊNCIA ML: Salvar o aprendizado na planilha
                            # Salvar descrição original e nova categoria
                            # Dispara em background/thread se possível, mas aqui vamos sequencial para garantir
                            try:
                                gsheets.append_classification(
                                    description=row['title'], 
                                    category=row['Nova Categoria'],
                                    amount=row['amount'],
                                    date=row['date']
                                )
                                # st.toast(f"🧠 Aprendi: {row['title']} -> {row['Nova Categoria']}", icon="🤓")
                            except Exception as e:
                                print(f"Erro ao salvar aprendizado ML: {e}")
                                
                            count += 1
                    
                    if count > 0:
                        utils.save_data_and_refresh_liquidas(st.session_state.df, st.session_state.income_df, st.session_state.settings)
                        st.success(f"✅ {count} transações categorizadas e **salvas automaticamente**!")
                        st.toast(f"Mágico aprendeu {count} novos padrões!", icon="🧙‍♂️")
                        st.info("💡 **Transações categorizadas desaparecem da lista** porque mudaram de categoria. Isso é normal! Veja-as na aba 'Transações' ou clique em 'Buscar Sugestões' novamente.")
                        del st.session_state.wiz_suggestions
                        st.rerun()
                    else:
                        st.warning("Nenhuma transação foi marcada com categoria válida para aplicar.")
    # ------------------------------------

    # ------------------------------------

    # Filtros (Só mostra se tiver dados, mas o editor aparece sempre)
    # --- FILTROS DE TRANSAÇÕES (ESTILO RECEITAS) ---
    col_trans_filter1, col_trans_filter2 = st.columns(2)
    
    with col_trans_filter1:
        # Opção "Todos" para ver histórico completo ou mês específico
        months = {0: "Todos", 1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        current_date_trans = datetime.now()
        selected_month_trans = st.selectbox("Mês", options=list(months.keys()), format_func=lambda x: months[x], index=current_date_trans.month, key="trans_month_filter")
        
    with col_trans_filter2:
        years = [0] + list(range(2024, 2031))
        selected_year_trans = st.selectbox("Ano", options=years, format_func=lambda x: "Todos" if x == 0 else str(x), index=years.index(current_date_trans.year) if current_date_trans.year in years else 0, key="trans_year_filter")
    
    # Filtro Visual de Pessoa
    if owner_filter != "Todos":
        if 'owner' not in display_df.columns: display_df['owner'] = "Família"
        display_df = display_df[display_df['owner'] == owner_filter]
        st.caption(f"Editando transações de: **{owner_filter}**")
        
    # --- NOVO: ESCONDER APLICAÇÕES DA LISTA DE TRANSAÇÕES ---
    # As aplicações devem aparecer apenas como valor líquido em Receitas.
    meta_cats_trans = utils.get_meta_categories(st.session_state.settings)
    cond_meta_trans = display_df['category'].isin(meta_cats_trans) if meta_cats_trans else pd.Series(False, index=display_df.index)
    cond_title_trans = display_df['title'].astype(str).str.contains('aplica', case=False, na=False)
    
    display_df = display_df[~(cond_meta_trans | cond_title_trans)]
    # ---------------------------------------------------------
    
    # Aplicar filtros de Data (Mês/Ano)
    if not display_df.empty:
        # Garantir tipos
        target_col = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
        if target_col not in display_df.columns and target_col == 'reference_date':
            display_df['reference_date'] = display_df['date'] # Fallback
        
        if not pd.api.types.is_datetime64_any_dtype(display_df[target_col]):
            display_df[target_col] = pd.to_datetime(display_df[target_col], errors='coerce')

        if selected_month_trans != 0:
            display_df = display_df[display_df[target_col].dt.month == selected_month_trans]
            
        if selected_year_trans != 0:
            display_df = display_df[display_df[target_col].dt.year == selected_year_trans]

    # --- BUSCA E TOOLS ---
    col_search_trans, col_sort_toggles_trans = st.columns([2, 3])
    with col_search_trans:
        search_term = st.text_input("🔍 Buscar Transação", placeholder="Ex: Mercado, Uber...", key="search_trans")
        
    with col_sort_toggles_trans:
        st.write("") # Spacer
        bulk_edit_mode = st.checkbox("✅ Ativar Edição em Massa", key="bulk_mode_toggle_trans", help="Permite alterar várias linhas de uma vez.")

    # Aplicar Filtro de Busca
    if search_term and not display_df.empty:
        display_df = display_df[display_df['title'].str.contains(search_term, case=False, na=False)]
            
    # --- ORDENAÇÃO (ESTILO RECEITAS) ---
    st.caption("Ordenar por:")
    col_sort_trans = st.columns(5)
    sort_opts_trans = ["Data", "Mês Ref.", "Categoria", "Valor", "Pessoa"]
    # Mapeamento de nomes amigáveis para colunas reais
    sort_cols_map_trans = {
        "Data": "date", 
        "Mês Ref.": "reference_date", 
        "Categoria": "category", 
        "Valor": "amount", 
        "Pessoa": "owner"
    }
    
    active_sorts_trans = []
    sort_ascending_trans = []
    
    for i, col_name in enumerate(sort_opts_trans):
        with col_sort_trans[i]:
             clicked = st.checkbox(col_name, key=f"sort_trans_{col_name}", value=(col_name=="Data")) # Default Data checked
             if clicked:
                 active_sorts_trans.append(sort_cols_map_trans[col_name])
                 # Direção
                 direction = st.radio("Direção", ["Decrescente", "Crescente"], key=f"dir_trans_{col_name}", label_visibility="collapsed", horizontal=True)
                 sort_ascending_trans.append(True if direction == "Crescente" else False)

    if active_sorts_trans and not display_df.empty:
         if 'date' in display_df.columns:
             display_df['date'] = pd.to_datetime(display_df['date'], format='mixed', errors='coerce')
         if 'reference_date' in display_df.columns:
             display_df['reference_date'] = pd.to_datetime(display_df['reference_date'], format='mixed', errors='coerce')
         display_df = display_df.sort_values(by=active_sorts_trans, ascending=sort_ascending_trans)
    
    # SOLUÇÃO DEFINITIVA: Criar hash único APÓS TODOS OS FILTROS
    # Isso garante que rastreamos corretamento os IDs das linhas filtradas
    if not display_df.empty and 'id' in display_df.columns:
        display_df['_row_hash'] = display_df['id'].astype(str)
    elif not display_df.empty:
        # Fallback: usar índice se não houver ID
        display_df['_row_hash'] = display_df.index.astype(str)
    
    # Resetar index para evitar warnings com hide_index=True e num_rows=dynamic
    display_df = display_df.reset_index(drop=True)
    
    # CORREÇÃO DE ERRO PYARROW: Converter date/reference_date para datetime64 (Timestamp)
    # Streamlit/PyArrow não lidam bem com objetos datetime.date puros em edições
    if 'date' in display_df.columns:
         display_df['date'] = pd.to_datetime(display_df['date'], errors='coerce')
    if 'reference_date' in display_df.columns:
         display_df['reference_date'] = pd.to_datetime(display_df['reference_date'], errors='coerce')

    # CRÍTICO: Salvar os hashes ANTES de enviar para o editor

    original_hashes = set(display_df['_row_hash'].dropna()) if '_row_hash' in display_df.columns else set()
    hash_to_id = dict(zip(display_df['_row_hash'], display_df['id'])) if '_row_hash' in display_df.columns and 'id' in display_df.columns else {}

    # --- LÓGICA DE EDIÇÃO EM MASSA (TRANSAÇÕES) ---
    if bulk_edit_mode:
        if "Selecionar" not in display_df.columns:
            display_df.insert(0, "Selecionar", False)
        
        # Configuração das Colunas para Edição em Massa
        column_config_bulk = {
            "Selecionar": st.column_config.CheckboxColumn("Selecionar", default=False, width="small"),
            "date": st.column_config.DateColumn("Data da Transação", format="DD/MM/YYYY", disabled=True),
            "reference_date": st.column_config.DateColumn("Mês de Referência", format="MM/YYYY", disabled=True),
            "title": st.column_config.TextColumn("Descrição", disabled=True),
            "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", disabled=True),
            "category": st.column_config.TextColumn("Categoria", disabled=True), # Visualização apenas por enquanto
            "owner": st.column_config.TextColumn("Pessoa", disabled=True),
            "_temp_id": None,
            "_row_hash": None,
            "id": None
        }
        
        st.info("ℹ️ Marque a caixa 'Selecionar' nas linhas que deseja alterar. Dica: Clique e arraste para selecionar várias!")
        
        edited_df = st.data_editor(
            display_df,
            column_config=column_config_bulk,
            hide_index=True,
            use_container_width=True,
            key="bulk_editor_trans_real",
            disabled=["date", "reference_date", "title", "amount", "category", "owner"] # Travar tudo exceto Checkbox
        )
        
        # BARRA DE AÇÕES EM MASSA
        selected_rows = edited_df[edited_df["Selecionar"] == True]
        count_selected = len(selected_rows)
        
        if count_selected > 0:
            st.markdown(f"### 📝 Editando {count_selected} transações selecionadas")
            
            with st.form("bulk_action_form_trans_real"):
                col_b1, col_b2, col_b3 = st.columns(3)
                
                with col_b1:
                    new_bulk_cat = st.selectbox("Nova Categoria", ["(Manter Atual)"] + settings["categories"])
                with col_b2:
                    new_bulk_owner = st.selectbox("Nova Pessoa", ["(Manter Atual)", "Pamela", "Renato", "Família"])
                with col_b3:
                    new_bulk_date = st.date_input("Nova Data", value=None)
                
                if st.form_submit_button("🚀 Aplicar Mudanças em Massa"):
                    # Processar Atualização
                    ids_to_update = selected_rows['id'].tolist()
                    
                    if not ids_to_update:
                         st.warning("Nenhum ID encontrado.")
                    else:
                        mask = st.session_state.df['id'].isin(ids_to_update)
                        
                        changes_made = False
                        if new_bulk_cat != "(Manter Atual)":
                            st.session_state.df.loc[mask, 'category'] = new_bulk_cat
                            
                            # PERSISTÊNCIA ML
                            try:
                                for _, row in selected_rows.iterrows():
                                    title = row.get('title', '')
                                    if title:
                                         gsheets.append_classification(
                                             description=title, 
                                             category=new_bulk_cat,
                                             amount=row.get('amount'),
                                             date=row.get('date')
                                         )
                            except:
                                pass
                            
                            changes_made = True
                            
                        if new_bulk_owner != "(Manter Atual)":
                            st.session_state.df.loc[mask, 'owner'] = new_bulk_owner
                            changes_made = True
                        
                        if new_bulk_date is not None:
                             st.session_state.df.loc[mask, 'date'] = pd.to_datetime(new_bulk_date)
                             changes_made = True
                            
                        if changes_made:
                            utils.save_data_and_refresh_liquidas(st.session_state.df, st.session_state.income_df, st.session_state.settings)
                            st.success(f"✅ {count_selected} transações atualizadas com sucesso!")
                            time.sleep(1)
                            st.rerun()

    # --- FIM LÓGICA EM MASSA ---
            
    # Editor de Dados (Sempre visível para adição)
    elif st.session_state.privacy_mode:
        st.info("🔒 Modo Privacidade Ativo: Edição desabilitada.")
        st.dataframe(
            get_privacy_data(display_df), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "id": None, 
                "_row_hash": None,
                "dedup_idx": None
            }
        )
        edited_df = display_df # Read-only
    else:
        # Editor Normal
        edited_df = st.data_editor(
            display_df,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "id": None, # Ocultar coluna ID
                "_row_hash": None,  # Ocultar coluna hash
                "dedup_idx": None, # Ocultar dedup_idx (se existir por cache)
                "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                "date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "title": st.column_config.TextColumn("Descrição"),
                "reference_date": st.column_config.DateColumn("Mês de Referência", format="MM/YYYY"),
                "category": st.column_config.SelectboxColumn("Categoria", options=settings["categories"]),
                "owner": st.column_config.SelectboxColumn("Pessoa", options=["Pamela", "Renato", "Família"])
            },
            key="trans_editor"  # Chave única para evitar conflitos
        )
    
    # Botão Salvar
    # Botão Salvar (Lógica Robusta Anti-Duplicação)
    if st.button("💾 Salvar Alterações", key="save_trans_btn"):
        # 1. Identificar IDs visíveis (que o usuário estava vendo/editando)
        # Se display_df (filtrado) tem dados, pegamos os IDs dele.
        # Se edited_df tem dados, ele reflete o estado atual dessas linhas (incluindo deleções que sumiram dele)
        
        # Recarregar dados completos do disco/estado para garantir
        full_df = utils.load_data()
        
        # Garantir ID
        if 'id' not in full_df.columns or full_df['id'].isnull().any():
            # Se faltar ID, regenera (caso extremo)
            full_df['id'] = [str(uuid.uuid4()) for _ in range(len(full_df))]
        
        # 2. Obter IDs que estavam no escopo de edição (display_df antes da edição)
        # PRECISÃO CRÍTICA: Precisamos saber quais IDs foram apresentados no data_editor.
        # O display_df aqui já passou por todos os filtros acima.
        visible_ids = []
        if not display_df.empty and 'id' in display_df.columns:
            visible_ids = display_df['id'].tolist()
            
        # 3. Remover do full_df TUDO que estava visível (para ser substituído pela versão editada)
        if visible_ids:
            # Mantém apenas o que NÃO estava visível
            untouched_df = full_df[~full_df['id'].isin(visible_ids)].copy()
        else:
            untouched_df = full_df.copy()
            
        # 4. Preparar dados editados (edited_df) para reinserção
        # edited_df contém o que sobrou na tela após edições/deleções do usuário
        # Linhas deletadas no editor simplesmente não estão mais no edited_df
        
        if not edited_df.empty:
            # Separar novas linhas (sem ID ou ID NaN)
            if 'id' not in edited_df.columns:
                edited_df['id'] = np.nan
            
            # Novas linhas (adicionadas pelo usuário no editor)
            new_rows_mask = edited_df['id'].isnull() | (edited_df['id'] == "")
            new_rows = edited_df[new_rows_mask].copy()
            
            # Linhas existentes (que sobreviveram à edição)
            existing_rows = edited_df[~new_rows_mask].copy()
            
            # Gerar IDs para novas linhas
            if not new_rows.empty:
                new_rows['id'] = [str(uuid.uuid4()) for _ in range(len(new_rows))]
                
            # Combinar para salvar
            rows_to_save = pd.concat([existing_rows, new_rows], ignore_index=True)
        else:
            rows_to_save = pd.DataFrame()
            
        # 5. Combinar Intocados + EditadosSalvos
        final_df = pd.concat([untouched_df, rows_to_save], ignore_index=True)
        
        # Limpar colunas auxiliares
        cols_to_drop = ['_row_hash', '_temp_id', 'Selecionar']
        final_df = final_df.drop(columns=[c for c in cols_to_drop if c in final_df.columns])
        
        # 6. Salvar
        utils.save_data_and_refresh_liquidas(final_df, st.session_state.income_df, st.session_state.settings)
        st.session_state.df = final_df
        st.success("✅ Dados salvos com sucesso! (Duplicação corrigida)")
        st.rerun()


# --- ABA 4: DASHBOARD (ANTIGA ABA 1) ---
with tab4:
    st.header("Visão Geral das Finanças")
    
    # Filtro de Pessoa já aplicado via owner_filter global
    
    # Filtros Globais do Dashboard
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        months = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                  7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        selected_month = st.selectbox("Selecione o Mês", list(months.keys()), format_func=lambda x: months[x], index=datetime.now().month-1, key="dash_month")
    
    with col_filter2:
        selected_year = st.selectbox("Selecione o Ano", range(2024, 2031), index=2, key="dash_year")


    # view_mode = st.radio(...) # REMOVIDO: Usa global
    date_col = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'

    if not df.empty:
        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
             df[date_col] = pd.to_datetime(df[date_col])
        
        # Filtrar dados (Data + Pessoa)
        mask = (df[date_col].dt.month == selected_month) & (df[date_col].dt.year == selected_year)
        
        if owner_filter != "Todos":
            if 'owner' not in df.columns:
                 df['owner'] = "Família"
            mask = mask & (df['owner'] == owner_filter)
            
        filtered_df = df[mask]
        
        if not filtered_df.empty:
            categories_to_exclude = ['Pagamento/Crédito'] # Excluir pagamentos/faturas pagas da visualização de gastos
            
            # --- NOVO: Excluir Categorias do Tipo "Meta" (Investimento/Guardado) ---
            meta_categories = utils.get_meta_categories(settings)
            
            # Normalizar para lista de exclusão
            if meta_categories:
                categories_to_exclude.extend(meta_categories)
            # -----------------------------------------------------------------------

            # Criar cópia para manipulação segura
            expenses_df = filtered_df.copy()
            
            # Normalizar categoria da transação para garantir match (strip)
            if 'category' in expenses_df.columns:
                 expenses_df['category'] = expenses_df['category'].astype(str).str.strip()

            expenses_df = expenses_df[~expenses_df['category'].isin(categories_to_exclude)]
            
            # --- NOVO: Excluir Aplicações pelo Título (pois elas podem estar cadastradas em "Outros") ---
            cond_aplica_dash = expenses_df['title'].astype(str).str.contains('aplica', case=False, na=False)
            expenses_df = expenses_df[~cond_aplica_dash]
            # -----------------------------------------------------------------------------------------
            
            expenses_df = expenses_df[expenses_df['amount'] > 0] 
            
            total_gastos = expenses_df['amount'].sum()
            qtde_compras = expenses_df['title'].count()
            maior_categoria = expenses_df.groupby('category')['amount'].sum().idxmax() if not expenses_df.empty else "-"
            
            kpi1, kpi2, kpi3 = st.columns(3)
            
            val_total = f"R$ {total_gastos:,.2f}"
            val_maior = maior_categoria
            val_qtde = qtde_compras
            
            if st.session_state.privacy_mode:
                val_total = "****"
                # val_maior = "****" # Categoria pode mostrar? Acho que sim.
                val_qtde = "****"
                
            kpi1.metric("Total de Gastos", val_total)
            kpi2.metric("Maior Categoria", val_maior)
            kpi3.metric("Quantidade de Compras", val_qtde)
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # SEÇÃO 1: ANÁLISE POR CATEGORIA
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.divider()
            st.subheader("📊 Análise por Categoria")
            
            row1_col1, row1_col2 = st.columns([5, 5])  # Proporção igual para dar mais espaço ao gráfico
            
            with row1_col1:
                st.markdown("**Distribuição de Gastos**")
                if not expenses_df.empty:
                    fig_pie = px.pie(
                        expenses_df, 
                        names='category', 
                        values='amount', 
                        hole=0.4, 
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(height=450)  # Maior altura
                    
                    # PRIVACY CHECK FOR CHART
                    if st.session_state.privacy_mode:
                        fig_pie.update_traces(textinfo='none', hoverinfo='none')
                        
                    st.plotly_chart(fig_pie, use_container_width=True, key="dash_pie_chart")
                else:
                    st.info("Sem gastos.")
            
            with row1_col2:
                st.markdown("**Detalhamento Completo por Categoria**")
                if not expenses_df.empty:
                    # Criar tabela resumo de categorias
                    category_summary = expenses_df.groupby('category').agg({
                        'amount': ['sum', 'count', 'mean']
                    }).reset_index()
                    
                    category_summary.columns = ['Categoria', 'Total', 'Qtd', 'Média']
                    category_summary['% do Total'] = (category_summary['Total'] / total_gastos * 100).round(1)
                    
                    # Ordenar por total decrescente
                    category_summary = category_summary.sort_values('Total', ascending=False)
                    
                    # Resetar índice para mostrar ranking
                    category_summary = category_summary.reset_index(drop=True)
                    category_summary.index = category_summary.index + 1  # Começar do 1
                    
                    # Exibir tabela formatada SEM altura fixa para mostrar tudo
                    st.dataframe(
                        get_privacy_data(category_summary),
                        column_config={
                            "Categoria": st.column_config.TextColumn("Categoria", width="medium"),
                            "Total": st.column_config.NumberColumn(
                                "Total Gasto",
                                format="R$ %.2f"
                            ),
                            "Qtd": st.column_config.NumberColumn(
                                "Nº Compras",
                                format="%d"
                            ),
                            "Média": st.column_config.NumberColumn(
                                "Valor Médio",
                                format="R$ %.2f"
                            ),
                            "% do Total": st.column_config.NumberColumn(
                                "% do Total",
                                format="%.1f%%"
                            )
                        },
                        use_container_width=True
                        # Sem height= para mostrar todas as linhas
                    )
                    
                    # Adicionar resumo rápido abaixo da tabela
                    num_categories = len(category_summary)
                    st.caption(f"💡 Mostrando todas as **{num_categories} categorias** rankeadas do maior para o menor gasto")
                else:
                    st.info("Sem dados para exibir.")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # SEÇÃO 2: ANÁLISE POR LOCAL
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.divider()
            st.subheader("🏪 Top 5 Locais de Maior Gasto")
            
            if not expenses_df.empty:
                top_places = expenses_df.copy()
                top_places['clean_title'] = top_places['title'].str.replace(r'(Pg \*|Mp \*|Dl\*)', '', regex=True).str.strip()
                top_places['clean_title'] = top_places['clean_title'].apply(lambda x: x.split('-')[0].strip())
                top5 = top_places.groupby('clean_title')['amount'].sum().nlargest(5).reset_index()
                
                fig_bar_top = px.bar(
                    top5, 
                    x='amount', 
                    y='clean_title', 
                    orientation='h',
                    text_auto='.2s',
                    color='amount',
                    color_continuous_scale='Reds'
                )
                fig_bar_top.update_layout(
                    yaxis={'categoryorder':'total ascending'},
                    xaxis_title="Total Gasto (R$)",
                    yaxis_title="",
                    showlegend=False,
                    height=300
                )
                fig_bar_top.update_traces(texttemplate='R$ %{x:,.2f}', textposition='outside')
                
                # PRIVACY CHECK FOR CHART
                if st.session_state.privacy_mode:
                    fig_bar_top.update_traces(textfont_color='rgba(0,0,0,0)', hoverinfo='none', hovertemplate=None)
                    fig_bar_top.update_layout(xaxis=dict(showticklabels=False), yaxis=dict(showticklabels=True)) # Manter titulos (nomes) visiveis, esconder valores do eixo X
                    
                st.plotly_chart(fig_bar_top, use_container_width=True, key="dash_bar_top5")
            else:
                st.info("Sem dados.")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # SEÇÃO 3: EVOLUÇÃO TEMPORAL
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.divider()
            st.subheader("📈 Evolução de Gastos no Mês")
            
            # CORREÇÃO: Converter date para datetime ANTES do groupby
            if not expenses_df.empty:
                if 'date' in expenses_df.columns:
                    expenses_df['date'] = pd.to_datetime(expenses_df['date'], errors='coerce')
                
                daily_spend = expenses_df.groupby('date')['amount'].sum().reset_index()
                
                fig_timeline = px.bar(
                    daily_spend, 
                    x='date', 
                    y='amount',
                    color='amount',
                    color_continuous_scale='Blues'
                )
                fig_timeline.update_layout(
                    xaxis_title="Data",
                    yaxis_title="Gasto Total (R$)",
                    showlegend=False,
                    height=350
                )
                fig_timeline.update_traces(texttemplate='R$ %{y:,.0f}', textposition='outside')
            
            # PRIVACY CHECK FOR CHART
            if st.session_state.privacy_mode:
                fig_timeline.update_traces(textfont_color='rgba(0,0,0,0)', hoverinfo='none', hovertemplate=None)
                fig_timeline.update_layout(yaxis=dict(showticklabels=False), xaxis=dict(showticklabels=False))
                
            st.plotly_chart(fig_timeline, use_container_width=True, key="dash_daily_chart")
        else:
            st.warning("Nenhum dado encontrado para o período/pessoa selecionados.")
    else:
        st.info("Adicione dados primeiro.")

# --- ABA 4: PLANEJAMENTO ---
# --- ABA 5: PLANEJAMENTO ---
# --- ABA 5: PLANEJAMENTO (METAS) ---
with tab5:
    st.header("🎯 Metas e Orçamentos (Tabela)")
    st.markdown("Defina suas metas mensais ou anuais aqui. O sistema prioriza: **Meta do Mês/Ano** > **Meta Padrão (Mês 0)**.")
    st.info("💡 **Dica**: Use Mês=0 e Ano=0 para definir a meta padrão da categoria (vale para todos os meses).")
    
    # Initialize DF if missing (Safety check)
    if "budgets_df" not in st.session_state.settings:
        st.session_state.settings["budgets_df"] = pd.DataFrame(columns=["Categoria", "Valor", "Mes", "Ano", "Tipo"])
    
    # Preparar DataFrame para edição
    full_df = st.session_state.settings["budgets_df"].copy()
    
    # Garantir coluna Tipo
    if "Tipo" not in full_df.columns: full_df["Tipo"] = "Orçamento"
    
    # Filtro Global da Aba -> AGORA APENAS DO EDITOR
    filter_type_editor = st.selectbox("Filtrar Editor/Tabela de Metas", ["Todos", "Orçamento", "Meta"], key="filter_type_editor_key")
    
    # Aplicar Filtro no Editor
    if filter_type_editor != "Todos":
        current_df = full_df[full_df["Tipo"] == filter_type_editor].copy()
        hidden_df = full_df[full_df["Tipo"] != filter_type_editor].copy()
    else:
        current_df = full_df.copy()
        hidden_df = pd.DataFrame()
    
    # Editor Tabela (Ou DataFrame se Privacy Mode)
    if st.session_state.privacy_mode:
        st.info("🔒 Modo Privacidade Ativo: Edição desabilitada. Desative o olho para editar.")
        st.dataframe(
            get_privacy_data(current_df),
            hide_index=True,
            use_container_width=True
        )
        edited_df = current_df # Sem alterações possíveis
    else:
        edited_df = st.data_editor(
           current_df,
        num_rows="dynamic",
        column_config={
            "Categoria": st.column_config.SelectboxColumn(
                "Categoria",
                options=st.session_state.settings.get("categories", []),
                required=True,
                width="medium"
            ),
            "Valor": st.column_config.NumberColumn(
                "Meta (R$)",
                format="R$ %.2f",
                min_value=0,
                width="small"
            ),
            "Mes": st.column_config.NumberColumn(
                "Mês",
                help="1-12. Use 0 para 'Todos' (Padrão)",
                min_value=0,
                max_value=12,
                step=1,
                format="%d",
                width="small"
            ),
            "Ano": st.column_config.NumberColumn(
                "Ano",
                help="Ex: 2026. Use 0 para 'Todos' (Padrão)",
                min_value=0,
                max_value=2030,
                step=1,
                format="%d",
                width="small"
            ),
            "Tipo": st.column_config.SelectboxColumn(
                "Tipo",
                options=["Orçamento", "Meta"],
                default="Orçamento",
                width="small",
                help="Orçamento: Limite de gasto (Ideal: Valor Real < Meta)\nMeta: Objetivo de ganho/economia (Ideal: Valor Real > Meta)"
            )
        },
        hide_index=True,
        use_container_width=True,
        key="budget_editor_global"
    )
    
    col_save_meta, _ = st.columns([1, 4])
    with col_save_meta:
        if st.button("💾 Salvar", type="primary"):
            # Recombinar dados editados com dados escondidos pelo filtro
            if not hidden_df.empty:
                final_df = pd.concat([hidden_df, edited_df], ignore_index=True)
            else:
                final_df = edited_df
                
            st.session_state.settings["budgets_df"] = final_df
            if utils.save_settings(st.session_state.settings):
                st.toast("Metas salvas com sucesso no Google Sheets!", icon="✅")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Erro ao salvar metas na planilha Google Sheets.")
    
    st.divider()

    # --- DASHBOARD DE ACOMPANHAMENTO (VISUAL) ---
    st.subheader("📊 Visualização Gráfica")
    st.markdown("Filtre o gráfico abaixo para comparar Meta vs Realizado.")

    # Filtros do GRÁFICO
    col_gf1, col_gf2, col_gf3, col_gf4 = st.columns([1, 1, 1, 1.5])
    with col_gf1:
        mon_dash_opts = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        sel_mon_graph = st.selectbox("Mês", list(mon_dash_opts.keys()), format_func=lambda x: mon_dash_opts[x], index=datetime.now().month-1, key="graph_meta_month")
    
    with col_gf2:
        sel_year_graph = st.selectbox("Ano", range(2024, 2031), index=datetime.now().year-2024, key="graph_meta_year")

    with col_gf3:
        filter_type_graph = st.selectbox("Tipo", ["Todos", "Orçamento", "Meta"], key="filter_type_graph_key")
        
    with col_gf4:
        sel_cats_graph = st.multiselect("Categorias", settings.get("categories", []), key="graph_meta_cats")

    # Calcular Comparativo (Gráfico)
    target_date_graph = date(sel_year_graph, sel_mon_graph, 1)
    
    # CRITICAL FIX: Usar edited_df (estado atual da edição) em vez de settings salvo
    # Isso permite preview em tempo real antes de salvar
    # Mas precisamos combinar com o hidden_df se o editor estiver filtrado
    if not hidden_df.empty:
        df_for_view = pd.concat([hidden_df, edited_df], ignore_index=True)
    else:
        df_for_view = edited_df
        
    temp_settings_graph = st.session_state.settings.copy()
    temp_settings_graph["budgets_df"] = df_for_view
    
    monthly_budgets_graph = utils.get_budgets_for_date(temp_settings_graph, target_date_graph)
    
    # filter_type_graph logic applied INSIDE loop to catch real_series items too
    
    # 2. Gastos Reais (Gráfico)
    real_series_graph = pd.Series()
    if not df.empty:
        df_g = df.copy()
        
        target_col_graph = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
        
        if 'date' in df_g.columns: df_g['date'] = pd.to_datetime(df_g['date'], errors='coerce')
        if 'reference_date' in df_g.columns: df_g['reference_date'] = pd.to_datetime(df_g['reference_date'], errors='coerce')
        
        # Fallback se não existir reference_date
        if target_col_graph not in df_g.columns: 
             target_col_graph = 'date'
             
        # Filtro de Data
        mask_g = (df_g[target_col_graph].dt.month == sel_mon_graph) & (df_g[target_col_graph].dt.year == sel_year_graph)
        
        # Filtro de Pessoa
        if owner_filter != "Todos" and 'owner' in df_g.columns: mask_g = mask_g & (df_g['owner'] == owner_filter)
        
        # Filtro de Categoria (Multiselect)
        if sel_cats_graph: mask_g = mask_g & (df_g['category'].isin(sel_cats_graph))
        
        real_series_graph = df_g[mask_g].groupby('category')['amount'].sum()

    # --- INVESTIMENTO PARA METAS (Gráfico) ---
    # Lê o valor assinado pré-computado de receitas_liquidas
    investimento_mensal_graph = 0.0
    try:
        rec_liq_g = utils.load_receitas_liquidas()
        if not rec_liq_g.empty:
            target_col_rl = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
            if target_col_rl not in rec_liq_g.columns: target_col_rl = 'date'
            if not pd.api.types.is_datetime64_any_dtype(rec_liq_g[target_col_rl]):
                rec_liq_g[target_col_rl] = pd.to_datetime(rec_liq_g[target_col_rl], format='mixed', errors='coerce')
            
            mask_rl = (rec_liq_g[target_col_rl].dt.month == sel_mon_graph) & (rec_liq_g[target_col_rl].dt.year == sel_year_graph)
            mask_synth = rec_liq_g['source'].astype(str).str.contains('Aplicação RDB', na=False)
            synth_rows = rec_liq_g[mask_rl & mask_synth]
            if not synth_rows.empty and 'investimento_meta' in synth_rows.columns:
                investimento_mensal_graph = synth_rows['investimento_meta'].sum()
    except Exception:
        pass
    # --------------------------------------------------

    # 3. Cruzar Dados (Gráfico)
    all_cats_graph = set(monthly_budgets_graph.keys()) | set(real_series_graph.index)
    if sel_cats_graph:
        all_cats_graph = all_cats_graph.intersection(set(sel_cats_graph))

    data_graph = []
    for cat in all_cats_graph:
        budget_info = monthly_budgets_graph.get(cat, {})
        cat_type = budget_info.get("Tipo", "Orçamento")
        
        if filter_type_graph != "Todos" and cat_type != filter_type_graph:
            continue
            
        meta_val = budget_info.get("Valor", 0.0)
        real_val = real_series_graph.get(cat, 0.0)
        
        if cat_type == "Meta":
            real_val = investimento_mensal_graph
        
        data_graph.append({"Categoria": cat, "Meta": meta_val, "Realizado": real_val})
    
    if data_graph:
        df_graph_data = pd.DataFrame(data_graph)
        fig_bar = px.bar(
            df_graph_data, 
            x="Categoria", 
            y=["Realizado", "Meta"], 
            barmode="group",
            title=f"Meta vs Realizado - {mon_dash_opts[sel_mon_graph]}/{sel_year_graph}",
            color_discrete_map={"Realizado": "#e74c3c", "Meta": "#2ecc71"}
        )
        
        
        # PRIVACY CHECK FOR CHART
        if st.session_state.privacy_mode:
            fig_bar.update_traces(textfont_color='rgba(0,0,0,0)', hoverinfo='none', hovertemplate=None)
            fig_bar.update_layout(yaxis=dict(showticklabels=False), xaxis=dict(showticklabels=False))
            
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico com os filtros selecionados.")
        
    st.divider()

    # --- DASHBOARD DE ACOMPANHAMENTO (TABELA) ---
    st.subheader("📋 Tabela Detalhada")
    st.markdown("Analise os número exatos.")

    # Filtros da TABELA
    col_tf1, col_tf2, col_tf3, col_tf4 = st.columns([1, 1, 1, 1.5])
    with col_tf1:
        sel_mon_table = st.selectbox("Mês", list(mon_dash_opts.keys()), format_func=lambda x: mon_dash_opts[x], index=datetime.now().month-1, key="table_meta_month")
    
    with col_tf2:
        sel_year_table = st.selectbox("Ano", range(2024, 2031), index=datetime.now().year-2024, key="table_meta_year")

    with col_tf3:
        filter_type_table = st.selectbox("Tipo", ["Todos", "Orçamento", "Meta"], key="filter_type_table_key")
        
    with col_tf4:
        sel_cats_table = st.multiselect("Categorias", settings.get("categories", []), key="table_meta_cats")

    # Calcular Comparativo (Tabela)
    target_date_table = date(sel_year_table, sel_mon_table, 1)
    
    # CRITICAL FIX: Usar edited_df aqui também para consistência
    # Reutilizando logic de combinação do gráfico
    if not hidden_df.empty:
        df_for_view_msg = pd.concat([hidden_df, edited_df], ignore_index=True)
    else:
        df_for_view_msg = edited_df

    temp_settings_table = st.session_state.settings.copy()
    temp_settings_table["budgets_df"] = df_for_view_msg
    
    monthly_budgets_table = utils.get_budgets_for_date(temp_settings_table, target_date_table)
    
    # filter_type_table logic applied INSIDE loop
    
    # 2. Gastos Reais (Tabela)
    real_series_table = pd.Series()
    real_series_table = pd.Series()
    if not df.empty:
        df_t = df.copy()
        
        target_col_table = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
        
        if 'date' in df_t.columns: df_t['date'] = pd.to_datetime(df_t['date'], errors='coerce')
        if 'reference_date' in df_t.columns: df_t['reference_date'] = pd.to_datetime(df_t['reference_date'], errors='coerce')
        
        # Fallback
        if target_col_table not in df_t.columns: 
             target_col_table = 'date'

        mask_t = (df_t[target_col_table].dt.month == sel_mon_table) & (df_t[target_col_table].dt.year == sel_year_table)
        if owner_filter != "Todos" and 'owner' in df_t.columns: mask_t = mask_t & (df_t['owner'] == owner_filter)
        if sel_cats_table: mask_t = mask_t & (df_t['category'].isin(sel_cats_table))
        real_series_table = df_t[mask_t].groupby('category')['amount'].sum()
        
    # --- INVESTIMENTO PARA METAS (Tabela) ---
    investimento_mensal_table = 0.0
    try:
        rec_liq_t = utils.load_receitas_liquidas()
        if not rec_liq_t.empty:
            target_col_rlt = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
            if target_col_rlt not in rec_liq_t.columns: target_col_rlt = 'date'
            if not pd.api.types.is_datetime64_any_dtype(rec_liq_t[target_col_rlt]):
                rec_liq_t[target_col_rlt] = pd.to_datetime(rec_liq_t[target_col_rlt], format='mixed', errors='coerce')
            
            mask_rlt = (rec_liq_t[target_col_rlt].dt.month == sel_mon_table) & (rec_liq_t[target_col_rlt].dt.year == sel_year_table)
            mask_synth_t = rec_liq_t['source'].astype(str).str.contains('Aplicação RDB', na=False)
            synth_rows_t = rec_liq_t[mask_rlt & mask_synth_t]
            if not synth_rows_t.empty and 'investimento_meta' in synth_rows_t.columns:
                investimento_mensal_table = synth_rows_t['investimento_meta'].sum()
    except Exception:
        pass
    # --------------------------------------------------

    # 3. Cruzar Dados (Tabela)
    all_cats_table = set(monthly_budgets_table.keys()) | set(real_series_table.index)
    if sel_cats_table:
        all_cats_table = all_cats_table.intersection(set(sel_cats_table))
        
    data_table = []
    for cat in all_cats_table:
        budget_info = monthly_budgets_table.get(cat, {})
        
        meta_type = budget_info.get("Tipo", "Orçamento")
        
        if filter_type_table != "Todos" and meta_type != filter_type_table:
            continue
            
        meta_val = budget_info.get("Valor", 0.0)
        
        real_val = real_series_table.get(cat, 0.0)
        
        # Logica baseada no Tipo
        if meta_type == "Meta":
            # Valor ASSINADO: Aplicações - Resgates (pode ser negativo)
            real_val = investimento_mensal_table
            
            diff = real_val - meta_val
            pct = (real_val / meta_val * 100) if meta_val > 0 else (100 if real_val > 0 else 0)
            
            if real_val < 0:
                # Resgatou mais do que investiu — MUITO distante da meta
                status = f"🔴 Negativo (R$ {abs(real_val):,.2f} abaixo de zero)"
            elif real_val >= meta_val:
                status = "🟢 Atingida"
            elif real_val >= meta_val * 0.7:
                falta = meta_val - real_val
                status = f"🟡 Faltam R$ {falta:,.2f}"
            else:
                falta = meta_val - real_val
                status = f"🔴 Faltam R$ {falta:,.2f}"
        else:
            # Orçamento de Gasto: BOM é Realizado <= Meta
            diff = meta_val - real_val # Quanto sobrou (Positivo = Bom)
            pct = (real_val / meta_val * 100) if meta_val > 0 else (100 if real_val > 0 else 0)
            
            if real_val > meta_val:
                status = "🔴 Estourou"
            elif real_val > meta_val * 0.9:
                status = "🟡 Alerta"
            else:
                status = "🟢 Dentro"
            
        data_table.append({
            "Categoria": cat,
            "Tipo": meta_type,
            "Meta": meta_val,
            "Realizado": real_val,
            "Diferença": diff, # Nome genérico para "Disponível" ou "Excedente"
            "% Uso": pct,
            "Status": status
        })
    
    if data_table:
        df_table_comp = pd.DataFrame(data_table).sort_values(by="% Uso", ascending=False)
        
        # Métricas Globais (Da Tabela Filtrada)
        # Separar Orçamentos de Metas para não somar laranjas com bananas
        
        df_orc = df_table_comp[df_table_comp['Tipo'] == 'Orçamento']
        df_met = df_table_comp[df_table_comp['Tipo'] == 'Meta']
        
        # Exibir Métricas de Orçamento (Padrão)
        st.markdown("#### Resumo de Orçamentos")
        if not df_orc.empty:
            total_meta_o = df_orc["Meta"].sum()
            total_real_o = df_orc["Realizado"].sum()
            total_diff_o = total_meta_o - total_real_o
            
            col_tm1, col_tm2, col_tm3 = st.columns(3)
            col_tm1.metric("Orçamento Total", f"R$ {total_meta_o:,.2f}")
            col_tm2.metric("Gasto Total", f"R$ {total_real_o:,.2f}", delta=f"{-total_real_o:,.2f}", delta_color="inverse")
            col_tm3.metric("Saldo Disponível", f"R$ {total_diff_o:,.2f}", delta=f"{total_diff_o:,.2f}", delta_color="normal")
        else:
            st.caption("Nenhuma categoria do tipo 'Orçamento' neste filtro.")
            
        # Exibir Métricas de Metas (Novo)
        st.markdown("#### Resumo de Metas de Arrecadação")
        if not df_met.empty:
            total_meta_m = df_met["Meta"].sum()
            total_real_m = df_met["Realizado"].sum()
            total_diff_m = total_real_m - total_meta_m # Excedente
            
            col_mm1, col_mm2, col_mm3 = st.columns(3)
            col_mm1.metric("Meta Total", f"R$ {total_meta_m:,.2f}")
            col_mm2.metric("Realizado Total", f"R$ {total_real_m:,.2f}", delta=f"{total_real_m:,.2f}", delta_color="normal")
            col_mm3.metric("superávit / Déficit", f"R$ {total_diff_m:,.2f}", delta=f"{total_diff_m:,.2f}", delta_color="normal")
        else:
             st.caption("Nenhuma categoria do tipo 'Meta' neste filtro.")
        
        # Tabela Detalhada (Sem barra de progresso, apenas número formatado)
        st.dataframe(
            get_privacy_data(df_table_comp),
            column_config={
                "Meta": st.column_config.NumberColumn(format="R$ %.2f"),
                "Realizado": st.column_config.NumberColumn(format="R$ %.2f"),
                "Diferença": st.column_config.NumberColumn(format="R$ %.2f", help="Saldo Disponível (Orçamento) ou Superávit (Meta)"),
                "% Uso": st.column_config.NumberColumn(
                    "% Atingido",
                    format="%.1f%%"
                ),
                "Status": st.column_config.TextColumn("Status"),
                "Tipo": st.column_config.TextColumn("Tipo")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Sem dados para a tabela com os filtros selecionados.")

# --- ABA 6: PROJEÇÕES ---
with tab6:


# --- REMOVIDO ABA ANTIGA DE PROJEÇÕES (CODIGO JÁ ESTAVA DUPLICADO OU DESNECESSÁRIO, REPOSICIONANDO) ---
# O conteúdo da antiga Tab 6 agora está na Tab 6, mas o código original estava na Tab 6 mesmo.
# Só precisamos ajustar a lógica interna para usar o filtro.

# A Lógica da Tab 6
    st.header("🔮 Projeções Financeiras")
    st.markdown("Comparativo: **Renda Cadastrada (Aba Receitas)** vs **Gastos Reais**.")
    
    # 1. Calcular Renda por Mês (Baseado nas RECEITAS LÍQUIDAS pré-computadas)
    income_df = utils.load_receitas_liquidas()
    income_by_month = pd.Series([0.0]*12, index=range(1, 13))
    
    
    # Garantir que proj_year esteja definido mesmo se não houver renda cadastrada
    col_proj_filter, _ = st.columns(2)
    with col_proj_filter:
         proj_year = st.number_input("Ano da Projeção", 2024, 2030, datetime.now().year, key="proj_year_input")

    # Se receitas_liquidas estiver vazia, usar income_df bruto como fallback
    if income_df.empty:
        income_df = utils.load_income_data()

    if not income_df.empty:
        # Garantir datetime
        if not pd.api.types.is_datetime64_any_dtype(income_df['date']):
            income_df['date'] = pd.to_datetime(income_df['date'])

        # Filtro de Pessoa
        if owner_filter != "Todos":
             if 'owner' not in income_df.columns: income_df['owner'] = "Família"
             income_df = income_df[income_df['owner'] == owner_filter]
        
        # DEFINIR QUAL DATA USAR
        target_col_inc = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
        
        if target_col_inc not in income_df.columns:
            target_col_inc = 'date'
        
        if not pd.api.types.is_datetime64_any_dtype(income_df[target_col_inc]):
            income_df[target_col_inc] = pd.to_datetime(income_df[target_col_inc], errors='coerce')

        # Agrupar pelo mês (os dados já estão limpos - sem resgates, com rendimento sintético)
        monthly_income = income_df[income_df[target_col_inc].dt.year == proj_year].copy()
        monthly_income_grouped = monthly_income.groupby(monthly_income[target_col_inc].dt.month)['amount'].sum()
        
        for m in monthly_income_grouped.index:
            income_by_month[m] = monthly_income_grouped[m]
    
    # 2. Calcular Gastos Reais (Reference Date)
    real_expenses = pd.Series([0.0]*12, index=range(1, 13))
    
    # ---------------------------------------------------------
    # PROTEÇÃO CONTRA BASE VAZIA (SISTEMA ONLINE/CLOUD)
    # ---------------------------------------------------------
    if df.empty or 'reference_date' not in df.columns:
        st.info("ℹ️ **Nenhum dado financeiro encontrado para projeção.**")
        st.markdown("Para ver os gráficos de fluxo de caixa:\n1. Vá na aba **Importar**.\n2. Suba seus arquivos CSV (Faturas/Extratos).")
        st.stop() # Interrompe a execução aqui para não dar erro lá embaixo
    
    # Se chegou aqui, temos dados!
    # CORREÇÃO: Usar cópia local para não poluir o df global com 'ref_dt'
    df_proj = df.copy()
    
    # Prevenção de erro: Cria a coluna se não existir
    if 'reference_date' not in df_proj.columns:
         df_proj['reference_date'] = df_proj['date']
    
    # Define qual data usar baseado no filtro global (CORREÇÃO APLICADA)
    target_col_proj = 'reference_date' if view_mode_global == "Mês de Referência" else 'date'
    
    # Fallback de segurança
    if target_col_proj not in df_proj.columns:
         target_col_proj = 'date'

    df_proj['calc_date'] = pd.to_datetime(df_proj[target_col_proj], errors='coerce')
    
    # Normalizar Categoria (Strip) para Filtro de Despesas
    if 'category' in df_proj.columns:
        df_proj['category'] = df_proj['category'].astype(str).str.strip()

    meta_categories = utils.get_meta_categories(st.session_state.settings)
    
    # Filtrar: 
    # 1. Ano correto
    # 2. Não é Pagamento de Fatura (duplicidade)
    # 3. Valor positivo (gasto)
    # 4. NÃO é categoria de "Meta" (dinheiro guardado, não gasto)
    # 5. NÃO contém a palavra "aplica" no título (investimentos cadastrados como Outros)
    
    # Construindo as máscaras condicionalmente
    cond_calc_date = (df_proj['calc_date'].dt.year == proj_year)
    cond_not_credit = (df_proj['category'] != 'Pagamento/Crédito')
    cond_positive = (df_proj['amount'] > 0)
    cond_not_meta = ~df_proj['category'].isin(meta_categories) if meta_categories else pd.Series(True, index=df_proj.index)
    cond_not_aplica = ~df_proj['title'].astype(str).str.contains('aplica', case=False, na=False)
    
    mask_exp = cond_calc_date & cond_not_credit & cond_positive & cond_not_meta & cond_not_aplica
    
    # Filtro opcional de dono
    if owner_filter != "Todos": 
         if 'owner' not in df_proj.columns: df_proj['owner'] = "Família"
         mask_exp = mask_exp & (df_proj['owner'] == owner_filter)
         st.caption(f"Fluxo de Caixa apenas de: **{owner_filter}**")
    else:
         st.caption("Fluxo de Caixa **Consolidado (Família)**")

    expenses_grouped = df_proj[mask_exp].groupby(df_proj['calc_date'].dt.month)['amount'].sum()
    for m in expenses_grouped.index:
        real_expenses[m] = expenses_grouped[m]

    # 3. Montar Gráfico
    months_list = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    
    proj_data = pd.DataFrame({
        "Mês": months_list,
        "Entradas (R$)": income_by_month.values,
        "Saídas (R$)": real_expenses.values
    })
    
    proj_data["Saldo (R$)"] = proj_data["Entradas (R$)"] - proj_data["Saídas (R$)"]
    proj_data["Acumulado (R$)"] = proj_data["Saldo (R$)"].cumsum()
    
    # Métricas do Ano
    total_income_year = proj_data["Entradas (R$)"].sum()
    total_expenses_year = proj_data["Saídas (R$)"].sum()
    total_balance_year = total_income_year - total_expenses_year
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    str_inc = f"R$ {total_income_year:,.2f}"
    str_exp = f"R$ {total_expenses_year:,.2f}"
    str_bal = f"R$ {total_balance_year:,.2f}"
    
    if st.session_state.privacy_mode:
        str_inc = "****"
        str_exp = "****"
        str_bal = "****"
    
    col_kpi1.metric("Receita Total (Ano)", str_inc)
    col_kpi2.metric("Despesa Total (Ano)", str_exp)
    col_kpi3.metric("Saldo Líquido (Ano)", str_bal, delta_color="normal")
    
    st.divider()
    
    st.subheader(f"Fluxo de Caixa - {proj_year}")
    
    # Gráfico Combinado (Barras + Linha Acumulada)
    fig = px.bar(proj_data, x="Mês", y=["Entradas (R$)", "Saídas (R$)"], barmode='group',
                 color_discrete_map={"Entradas (R$)": "#27ae60", "Saídas (R$)": "#c0392b"})
    
    # Adicionar linha de saldo mensal (opcional) ou focar no acumulado?
    # O pedido foi "acumulado do líquido".
    fig.add_scatter(x=proj_data["Mês"], y=proj_data["Acumulado (R$)"], mode='lines+markers', name='Acumulado Líquido', 
                    line=dict(color='#2980b9', width=3))
    
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    # PRIVACY CHECK FOR CHART
    if st.session_state.privacy_mode:
        fig.update_traces(textfont_color='rgba(0,0,0,0)', hoverinfo='none', hovertemplate=None)
        fig.update_layout(yaxis=dict(showticklabels=False), xaxis=dict(showticklabels=False)) # Esconder eixos X e Y
    
    st.plotly_chart(fig, use_container_width=True, key=f"proj_chart_{proj_year}_{owner_filter}")
    
    st.dataframe(get_privacy_data(proj_data), column_config={
        "Entradas (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Saídas (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Saldo (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Acumulado (R$)": st.column_config.NumberColumn(format="R$ %.2f")
    }, use_container_width=True)


