import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import uuid
import utils
import utils
import os
import time

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

# Título Principal
st.title("💰 Organizador Financeiro Família Guerra Possa")

# Carregar Dados
if 'df' not in st.session_state:
    st.session_state.df = utils.load_data()

df = st.session_state.df

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
        st.session_state.settings = utils.load_settings()
        st.session_state.just_refreshed = True
        st.rerun()

    st.info(f"📂 Dados Carregados: {len(df)} registros")
    
    # Filtro de Pessoa (Global para TODAS as abas)
    owner_filter = st.selectbox("Filtrar por Pessoa", ["Todos", "Pamela", "Renato", "Família"], key="global_owner_filter")
    
    st.header("⚙️ Configurações")
    
    with st.expander("Gerenciar Categorias"):
        new_cat = st.text_input("Nova Categoria")
        if st.button("Adicionar"):
            if new_cat and new_cat not in settings["categories"]:
                settings["categories"].append(new_cat)
                # Adicionar linha padrão no DF de metas se não existir
                if "budgets_df" in settings:
                     new_row = pd.DataFrame([{"Categoria": new_cat, "Valor": 0.0, "Mes": 0, "Ano": 0}])
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
                # Apagar Despesas
                if del_expenses and not df.empty:
                    # Garantir datetime
                    df['dt_obj'] = pd.to_datetime(df['date'], errors='coerce')
                    mask_keep = ~((df['dt_obj'].dt.month == del_month) & (df['dt_obj'].dt.year == del_year))
                    
                    new_df_kept = df[mask_keep].drop(columns=['dt_obj'])
                    st.session_state.df = new_df_kept
                    utils.save_data(new_df_kept)
                    msg_success.append("Despesas")

                # Apagar Receitas
                if del_income:
                    # Carregar receitas atuais para garantir que temos o último estado
                    curr_income = utils.load_income_data()
                    if not curr_income.empty and 'date' in curr_income.columns:
                        curr_income['dt_temp'] = pd.to_datetime(curr_income['date'], errors='coerce')
                        mask_inc_keep = ~((curr_income['dt_temp'].dt.month == del_month) & (curr_income['dt_temp'].dt.year == del_year))
                        new_inc_kept = curr_income[mask_inc_keep].drop(columns=['dt_temp'])
                        utils.save_income_data(new_inc_kept)
                        msg_success.append("Receitas")
                
                if msg_success:
                     st.success(f"Dados de {del_month}/{del_year} ({', '.join(msg_success)}) apagados.")
                     time.sleep(1.5)
                     st.rerun()
                else:
                     st.warning(f"Nenhum dado encontrado para apagar em {del_month}/{del_year}.")
                
        # Opção 2: Reset Total
        if st.button("🔥 APAGAR TUDO (Reset)"):
            utils.save_data(pd.DataFrame(columns=df.columns))
            st.session_state.df = utils.load_data()
            st.success("Todos os dados foram apagados.")
            st.rerun()

# Criar Abas (Ordem Solicitada: Receitas, Importar, Transações, Dashboard, Planejamento, Projeções)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["💰 Receitas", "📥 Importar", "📝 Transações", "📊 Dashboard", "🎯 Metas", "🔮 Projeções"])

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
    
    # Carregar todas as receitas do banco
    full_income_df = utils.load_income_data()
    
    # IMPORTANTE: Criar IDs únicos ANTES de qualquer filtro para rastrear deleções
    # Usa hash do conteúdo para garantir consistência
    if not full_income_df.empty:
        full_income_df['_temp_id'] = full_income_df.apply(
            lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                            str(row.get('amount', '')), str(row.get('owner', '')))), 
            axis=1
        ).astype(str)
    
    # Aplicar filtros APENAS para visualização (não altera o DataFrame original)
    display_income = full_income_df.copy()
    
    if not display_income.empty and 'date' in display_income.columns:
        display_income['date'] = pd.to_datetime(display_income['date'], errors='coerce')
        
        # Filtrar por mês (0 = Todos)
        if selected_month_rec != 0:
            display_income = display_income[display_income['date'].dt.month == selected_month_rec]
        
        # Filtrar por ano (0 = Todos)
        if selected_year_rec != 0:
            display_income = display_income[display_income['date'].dt.year == selected_year_rec]
    
    # Filtro Visual de Pessoa (Se selecionado pessoa específica)
    if owner_filter != "Todos":
        if 'owner' not in display_income.columns: display_income['owner'] = "Família"
        display_income = display_income[display_income['owner'] == owner_filter]
        st.caption(f"Editando receitas de: **{owner_filter}**")
    else:
        st.caption("Editando **Todas** as receitas")

    # --- Filtros e Ordenação Avançada (Receitas) ---
    col_search_inc, _ = st.columns([2, 1])
    with col_search_inc:
        search_term_inc = st.text_input("🔍 Buscar Receita", placeholder="Ex: Salário, Rendimento...", key="search_income")
    
    if search_term_inc and 'source' in display_income.columns:
         display_income = display_income[display_income['source'].astype(str).str.contains(search_term_inc, case=False, na=False)]

    # Ordenação (Igual transações)
    st.caption("Ordenar por:")
    col_sort_inc = st.columns(4)
    sort_opts_inc = ["Data", "Fonte", "Valor", "Pessoa"]
    sort_cols_map_inc = {"Data": "date", "Fonte": "source", "Valor": "amount", "Pessoa": "owner"}
    
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
        if 'date' in display_income.columns: # date já deve ser datetime
             display_income = display_income.sort_values(by=active_sorts_inc, ascending=sort_ascending_inc)

    # Resetar index para evitar colunas estranhas no editor e garantir alinhamento
    display_income = display_income.reset_index(drop=True)

    # Editor de Receitas
    edited_income = st.data_editor(
        display_income,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
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
            full_income['_temp_id'] = full_income.apply(
                lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                                str(row.get('amount', '')), str(row.get('owner', '')))), 
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
        
        # 6. Limpar _temp_id antes de salvar
        if '_temp_id' in final_income.columns:
            final_income = final_income.drop(columns=['_temp_id'])
        
        # 7. Salvar
        utils.save_income_data(final_income)
        
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
        
        # Tenta adivinhar mês/ano do arquivo se possível (ex: nubank_2026-02.csv)
        default_month = datetime.now().month
        default_year = datetime.now().year
        
        if uploaded_file:
             extracted_month, extracted_year = utils.extract_date_from_filename(uploaded_file.name)
             if extracted_month and extracted_year:
                 # Validar que o mês está no range válido
                 if 1 <= extracted_month <= 12 and 2020 <= extracted_year <= 2050:
                     default_month = extracted_month
                     default_year = extracted_year
                     st.success(f"🗓️ Detectado: {months[default_month]}/{default_year}")
                 else:
                     st.warning(f"⚠️ Data extraída inválida do arquivo. Usando data atual.")

        imp_month = st.selectbox("Mês de Referência", list(months.keys()), format_func=lambda x: months[x], index=default_month-1, key="imp_month")
        imp_year = st.selectbox("Ano de Referência", range(2024, 2031), index=default_year-2024, key="imp_year") # Ajuste index conforme range
        
        # Dono da Fatura
        st.markdown("---")
        imp_owner = st.selectbox("De quem é essa fatura?", ["Família", "Pamela", "Renato"], index=0, key="imp_owner")
        
    if uploaded_file:
        if st.button("Processar Arquivo"):
            try:
                # Referência: Primeiro dia do mês selecionado
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
            "reference_date": st.column_config.DateColumn("Mês Ref.", format="DD/MM/YYYY"),
            "title": st.column_config.TextColumn("Descrição"),
            "source": st.column_config.TextColumn("Fonte"),
            "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "category": st.column_config.TextColumn("Categoria"),
            "owner": st.column_config.TextColumn("Pessoa")
        }

        # Preview de Receitas (se houver)
        if has_income:
            st.markdown("### 💰 Receitas a Importar")
            st.dataframe(import_data['income'].head(5), use_container_width=True, column_config=preview_cols)
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
                    new_inc_count = len(new_inc_df) - duplicates_inc
                
                # Limpar temp
                del st.session_state.temp_import_data
                
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

        with st.expander("🧙‍♂️ Mágico de Categorização (Regras + Aprendizado)"):
            st.write("Analisa suas transações usando:")
            st.markdown("- **Regras fixas** (Nowpark → Transporte, Uber → Transporte, etc)")
            st.markdown("- **Padrões aprendidos** das suas categorizações manuais anteriores")
            st.info("💡 **Como funciona:** O Mágico **salva automaticamente** ao clicar em 'Aplicar'. Transações categorizadas desaparecem da lista porque mudaram de categoria (isso é normal!).")
            
            col_wiz1, col_wiz2 = st.columns(2)
            with col_wiz1:
                # Mudança para Multiselect conforme pedido
                wiz_target = st.multiselect("Escopo da Busca:", ["Vazias", "Outros/Geral", "Todas as Categorias"], default=["Vazias"])
            
            if st.button("🔍 Buscar Sugestões"):
                # Aprende com dados históricos
                learned_patterns = ml_patterns.learn_patterns_from_data(df)
                
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
                        suggested = ml_patterns.suggest_category_from_learned(row['title'], learned_patterns)
                    
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
                    st.session_state.wiz_suggestions = pd.DataFrame(wiz_suggestions)
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
                
                edited_wiz = st.data_editor(
                    st.session_state.wiz_suggestions,
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
                            count += 1
                    
                    if count > 0:
                        utils.save_data(st.session_state.df)
                        st.success(f"✅ {count} transações categorizadas e **salvas automaticamente**!")
                        st.info("💡 **Transações categorizadas desaparecem da lista** porque mudaram de categoria. Isso é normal! Veja-as na aba 'Transações' ou clique em 'Buscar Sugestões' novamente.")
                        del st.session_state.wiz_suggestions
                        st.rerun()
                    else:
                        st.warning("Nenhuma transação foi marcada com categoria válida para aplicar.")
    # ------------------------------------

    # ------------------------------------

    # Filtros (Só mostra se tiver dados, mas o editor aparece sempre)
    col_search, col_month, col_year = st.columns([2, 1, 1])
    
    with col_search:
        search_term = st.text_input("🔍 Buscar por título...")
        
    current_date = datetime.now()
    with col_month:
        # Opção "Todos" para ver histórico completo ou mês específico
        months = {0: "Todos", 1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        selected_month_trans = st.selectbox("Mês", options=list(months.keys()), format_func=lambda x: months[x], index=current_date.month)
        
    with col_year:
        years = [0] + list(range(2024, 2031))
        selected_year_trans = st.selectbox("Ano", options=years, format_func=lambda x: "Todos" if x == 0 else str(x), index=years.index(current_date.year) if current_date.year in years else 0)
    
    # Aplicar filtros apenas se tiver dados
    if not display_df.empty:
        # Garantir que a coluna date seja datetime para filtragem
        # Validação segura de tipos
        if 'date' in display_df.columns and not pd.api.types.is_datetime64_any_dtype(display_df['date']):
             display_df['date'] = pd.to_datetime(display_df['date'], errors='coerce')

        if search_term:
            display_df = display_df[display_df['title'].str.contains(search_term, case=False, na=False)]
            
        if selected_month_trans != 0:
            display_df = display_df[display_df['date'].dt.month == selected_month_trans]
            
        if selected_year_trans != 0:
            display_df = display_df[display_df['date'].dt.year == selected_year_trans]
        
        # Ordenação Multi-Coluna (Solicitação do Usuário)
        st.caption("Ordenação Personalizada")
        col_sort1, col_sort2 = st.columns([2, 1])
        with col_sort1:
            # Opções amigáveis para o usuário
            sort_cols = st.multiselect("Ordenar por:", ['DATA', 'VALOR', 'CATEGORIA', 'DESCRIÇÃO', 'PESSOA'], default=['DATA'], key="sort_cols_trans")
        
        sort_directions = []
        if sort_cols:
            with col_sort2:
                st.caption("Direção")
                for col in sort_cols:
                     direction = st.selectbox(f"Ordem de {col}", ["Decrescente", "Crescente"], key=f"sort_dir_trans_{col}", label_visibility="collapsed")
                     sort_directions.append(True if direction == "Crescente" else False)
            
            # Mapeamento de nomes amigáveis para colunas reais
            col_map = {
                'DATA': 'date', 
                'VALOR': 'amount', 
                'CATEGORIA': 'category', 
                'DESCRIÇÃO': 'title', 
                'PESSOA': 'owner'
            }
            real_cols = [col_map[c] for c in sort_cols]
            
            if real_cols:
                display_df = display_df.sort_values(by=real_cols, ascending=sort_directions)
    
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
            
    # Editor de Dados (Sempre visível para adição)
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
            "reference_date": st.column_config.DateColumn("Mês Ref.", format="DD/MM/YYYY"),
            "category": st.column_config.SelectboxColumn("Categoria", options=settings["categories"]),
            "owner": st.column_config.SelectboxColumn("Pessoa", options=["Pamela", "Renato", "Família"])
        },
        key="trans_editor"  # Chave única para evitar conflitos
    )
    
    # Botão Salvar
    if st.button("💾 Salvar Alterações", key="save_trans_btn"):
        # REFATORAÇÃO: Usar mesmo padrão de Receitas que funciona bem
        # 1. Carregar DataFrame completo do disco
        full_df = utils.load_data()
        
        # 2. Criar _row_hash no full_df (mesmo método usado em display_df)
        if not full_df.empty and 'id' in full_df.columns:
            full_df['_row_hash'] = full_df['id'].astype(str)
        
        # 3. Aplicar os MESMOS filtros que foram aplicados em display_df
        # para determinar quais transações NÃO devem ser tocadas
        full_df['date'] = pd.to_datetime(full_df['date'], errors='coerce')
        
        # Máscara para transações que NÃO devem ser alteradas (fora do filtro atual)
        mask_keep = pd.Series([True] * len(full_df), index=full_df.index)
        
        # Inverter lógica dos filtros: marcar como "keep" o que NÃO está no filtro
        if search_term:
            mask_keep = mask_keep & ~(full_df['title'].str.contains(search_term, case=False, na=False))
        
        if selected_month_trans != 0:
            mask_keep = mask_keep & (full_df['date'].dt.month != selected_month_trans)
        
        if selected_year_trans != 0:
            mask_keep = mask_keep & (full_df['date'].dt.year != selected_year_trans)
        
        # Aplicar filtro de pessoa (owner_filter vem do filtro global)
        if owner_filter != "Todos" and 'owner' in full_df.columns:
            mask_keep = mask_keep | (full_df['owner'] != owner_filter)
        
        # Transações fora do filtro = preservar
        untouched_trans = full_df[mask_keep].copy()
        
        # 4. Detectar deleções comparando hashes
        if '_row_hash' in display_df.columns and not display_df.empty:
            original_ids_shown = set(display_df['_row_hash'].dropna())
            
            if edited_df.empty:
                edited_ids = set()  # Todas deletadas
            elif '_row_hash' in edited_df.columns:
                edited_ids = set(edited_df['_row_hash'].dropna())
            else:
                # Fallback: sem hash = assume que são todas novas
                edited_ids = set()
            
            deleted_hashes = original_ids_shown - edited_ids
            
            # Remover deletadas de untouched_trans
            if deleted_hashes and '_row_hash' in untouched_trans.columns:
                untouched_trans = untouched_trans[~untouched_trans['_row_hash'].isin(deleted_hashes)]
        
        # 5. Processar edited_df: separar novas vs editadas
        if not edited_df.empty:
            # Linhas com _row_hash são editadas, sem _row_hash são novas
            if '_row_hash' in edited_df.columns:
                edited_existing = edited_df[edited_df['_row_hash'].notna()].copy()
                new_rows = edited_df[edited_df['_row_hash'].isna()].copy()
            else:
                # Se não tem hash, todas são novas
                edited_existing = pd.DataFrame()
                new_rows = edited_df.copy()
            
            # Gerar IDs para novas
            if not new_rows.empty:
                new_rows['id'] = [str(uuid.uuid4()) for _ in range(len(new_rows))]
                if '_row_hash' in new_rows.columns:
                    new_rows = new_rows.drop(columns=['_row_hash'])
            
            # Limpar _row_hash de editadas
            if not edited_existing.empty and '_row_hash' in edited_existing.columns:
                edited_existing = edited_existing.drop(columns=['_row_hash'])
            
            # Combinar: untouched + editadas + novas
            final_df = pd.concat([untouched_trans, edited_existing, new_rows], ignore_index=True)
        else:
            # Se edited_df vazio, só manter untouched
            final_df = untouched_trans.copy()
        
        # 6. Limpar _row_hash antes de salvar
        if '_row_hash' in final_df.columns:
            final_df = final_df.drop(columns=['_row_hash'])
        
        # 7. Salvar e atualizar session state
        utils.save_data(final_df)
        st.session_state.df = final_df
        st.success("✅ Dados salvos com sucesso!")
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

    view_mode = st.radio("Visualizar por:", ["Mês de Referência (Fatura)", "Data da Compra"], horizontal=True, key="dash_view_mode")
    date_col = 'reference_date' if view_mode == "Mês de Referência (Fatura)" else 'date'

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
            expenses_df = filtered_df[~filtered_df['category'].isin(categories_to_exclude)].copy()
            expenses_df = expenses_df[expenses_df['amount'] > 0] 
            
            total_gastos = expenses_df['amount'].sum()
            qtde_compras = expenses_df['title'].count()
            maior_categoria = expenses_df.groupby('category')['amount'].sum().idxmax() if not expenses_df.empty else "-"
            
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total de Gastos", f"R$ {total_gastos:,.2f}")
            kpi2.metric("Maior Categoria", maior_categoria)
            kpi3.metric("Quantidade de Compras", qtde_compras)
            
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
                        category_summary,
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
        st.session_state.settings["budgets_df"] = pd.DataFrame(columns=["Categoria", "Valor", "Mes", "Ano"])
    
    # Preparar DataFrame para edição
    current_df = st.session_state.settings["budgets_df"].copy()
    
    # Editor Tabela
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
            )
        },
        hide_index=True,
        use_container_width=True,
        key="budget_editor_global"
    )
    
    col_save_meta, _ = st.columns([1, 4])
    with col_save_meta:
        if st.button("💾 Salvar Metas", type="primary"):
            st.session_state.settings["budgets_df"] = edited_df
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
    col_gf1, col_gf2, col_gf3 = st.columns([1, 1, 2])
    with col_gf1:
        mon_dash_opts = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        sel_mon_graph = st.selectbox("Mês (Gráfico)", list(mon_dash_opts.keys()), format_func=lambda x: mon_dash_opts[x], index=datetime.now().month-1, key="graph_meta_month")
    
    with col_gf2:
        sel_year_graph = st.selectbox("Ano (Gráfico)", range(2024, 2031), index=datetime.now().year-2024, key="graph_meta_year")
        
    with col_gf3:
        sel_cats_graph = st.multiselect("Categorias (Gráfico)", settings.get("categories", []), key="graph_meta_cats")

    # Calcular Comparativo (Gráfico)
    target_date_graph = date(sel_year_graph, sel_mon_graph, 1)
    monthly_budgets_graph = utils.get_budgets_for_date(st.session_state.settings, target_date_graph)
    
    # 2. Gastos Reais (Gráfico)
    real_series_graph = pd.Series()
    if not df.empty:
        df_g = df.copy()
        if 'date' in df_g.columns: df_g['date'] = pd.to_datetime(df_g['date'], errors='coerce')
        mask_g = (df_g['date'].dt.month == sel_mon_graph) & (df_g['date'].dt.year == sel_year_graph)
        if owner_filter != "Todos" and 'owner' in df_g.columns: mask_g = mask_g & (df_g['owner'] == owner_filter)
        if sel_cats_graph: mask_g = mask_g & (df_g['category'].isin(sel_cats_graph))
        real_series_graph = df_g[mask_g].groupby('category')['amount'].sum()

    # 3. Cruzar Dados (Gráfico)
    all_cats_graph = set(monthly_budgets_graph.keys()) | set(real_series_graph.index)
    if sel_cats_graph:
        all_cats_graph = all_cats_graph.intersection(set(sel_cats_graph))

    data_graph = []
    for cat in all_cats_graph:
        meta_val = monthly_budgets_graph.get(cat, 0.0)
        real_val = real_series_graph.get(cat, 0.0)
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
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico com os filtros selecionados.")
        
    st.divider()
    
    # --- DASHBOARD DE ACOMPANHAMENTO (TABELA) ---
    st.subheader("📋 Tabela Detalhada")
    st.markdown("Analise os número exatos.")

    # Filtros da TABELA
    col_tf1, col_tf2, col_tf3 = st.columns([1, 1, 2])
    with col_tf1:
        sel_mon_table = st.selectbox("Mês (Tabela)", list(mon_dash_opts.keys()), format_func=lambda x: mon_dash_opts[x], index=datetime.now().month-1, key="table_meta_month")
    
    with col_tf2:
        sel_year_table = st.selectbox("Ano (Tabela)", range(2024, 2031), index=datetime.now().year-2024, key="table_meta_year")
        
    with col_tf3:
        sel_cats_table = st.multiselect("Categorias (Tabela)", settings.get("categories", []), key="table_meta_cats")

    # Calcular Comparativo (Tabela)
    target_date_table = date(sel_year_table, sel_mon_table, 1)
    monthly_budgets_table = utils.get_budgets_for_date(st.session_state.settings, target_date_table)
    
    # 2. Gastos Reais (Tabela)
    real_series_table = pd.Series()
    if not df.empty:
        df_t = df.copy()
        if 'date' in df_t.columns: df_t['date'] = pd.to_datetime(df_t['date'], errors='coerce')
        mask_t = (df_t['date'].dt.month == sel_mon_table) & (df_t['date'].dt.year == sel_year_table)
        if owner_filter != "Todos" and 'owner' in df_t.columns: mask_t = mask_t & (df_t['owner'] == owner_filter)
        if sel_cats_table: mask_t = mask_t & (df_t['category'].isin(sel_cats_table))
        real_series_table = df_t[mask_t].groupby('category')['amount'].sum()

    # 3. Cruzar Dados (Tabela)
    all_cats_table = set(monthly_budgets_table.keys()) | set(real_series_table.index)
    if sel_cats_table:
        all_cats_table = all_cats_table.intersection(set(sel_cats_table))
        
    data_table = []
    for cat in all_cats_table:
        meta_val = monthly_budgets_table.get(cat, 0.0)
        real_val = real_series_table.get(cat, 0.0)
        diff = meta_val - real_val
        pct = (real_val / meta_val * 100) if meta_val > 0 else (100 if real_val > 0 else 0)
        
        status = "🟢 Dentro"
        if real_val > meta_val:
            status = "🔴 Estourou"
        elif real_val > meta_val * 0.9:
            status = "🟡 Alerta"
            
        data_table.append({
            "Categoria": cat,
            "Meta": meta_val,
            "Realizado": real_val,
            "Disponível": diff,
            "% Uso": pct,
            "Status": status
        })
    
    if data_table:
        df_table_comp = pd.DataFrame(data_table).sort_values(by="% Uso", ascending=False)
        
        # Métricas Globais (Da Tabela Filtrada)
        total_meta_t = df_table_comp["Meta"].sum()
        total_real_t = df_table_comp["Realizado"].sum()
        total_diff_t = total_meta_t - total_real_t
        
        col_tm1, col_tm2, col_tm3 = st.columns(3)
        col_tm1.metric("Orçamento (Filtrado)", f"R$ {total_meta_t:,.2f}")
        col_tm2.metric("Gasto (Filtrado)", f"R$ {total_real_t:,.2f}", delta=f"{-total_real_t:,.2f}", delta_color="inverse")
        col_tm3.metric("Saldo (Filtrado)", f"R$ {total_diff_t:,.2f}", delta=f"{total_diff_t:,.2f}", delta_color="normal")
        
        # Tabela Detalhada (Sem barra de progresso, apenas número formatado)
        st.dataframe(
            df_table_comp,
            column_config={
                "Meta": st.column_config.NumberColumn(format="R$ %.2f"),
                "Realizado": st.column_config.NumberColumn(format="R$ %.2f"),
                "Disponível": st.column_config.NumberColumn(format="R$ %.2f"),
                "% Uso": st.column_config.NumberColumn(
                    "% Utilizado",
                    format="%.1f%%"
                ),
                "Status": st.column_config.TextColumn("Status")
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
    
    # 1. Calcular Renda por Mês (Baseado na aba Receitas)
    income_df = utils.load_income_data()
    income_by_month = pd.Series([0.0]*12, index=range(1, 13))
    
    
    # Garantir que proj_year esteja definido mesmo se não houver renda cadastrada
    col_proj_filter, _ = st.columns(2)
    with col_proj_filter:
         proj_year = st.number_input("Ano da Projeção", 2024, 2030, datetime.now().year, key="proj_year_input")

    if not income_df.empty:
        # Garantir datetime
        if not pd.api.types.is_datetime64_any_dtype(income_df['date']):
            income_df['date'] = pd.to_datetime(income_df['date'])

        # Filtrar receitas do ano e DONO
        income_df['year'] = income_df['date'].dt.year
        income_df['month'] = income_df['date'].dt.month
        
        # Filtro de Pessoa
        if owner_filter != "Todos":
             if 'owner' not in income_df.columns: income_df['owner'] = "Família"
             income_df = income_df[income_df['owner'] == owner_filter]
        
        monthly_income = income_df[income_df['year'] == proj_year].groupby('month')['amount'].sum()
        for m in monthly_income.index:
            income_by_month[m] = monthly_income[m]
    
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
    if 'reference_date' in df_proj.columns:
         df_proj['ref_dt'] = pd.to_datetime(df_proj['reference_date'])
    else:
         df_proj['ref_dt'] = pd.to_datetime(df_proj['date'])
    
    mask_exp = (df_proj['ref_dt'].dt.year == proj_year) & (df_proj['category'] != 'Pagamento/Crédito') & (df_proj['amount'] > 0)
    
    # Filtro opcional de dono
    if owner_filter != "Todos": 
         if 'owner' not in df_proj.columns: df_proj['owner'] = "Família"
         mask_exp = mask_exp & (df_proj['owner'] == owner_filter)
         st.caption(f"Fluxo de Caixa apenas de: **{owner_filter}**")
    else:
         st.caption("Fluxo de Caixa **Consolidado (Família)**")

    expenses_grouped = df_proj[mask_exp].groupby(df_proj['ref_dt'].dt.month)['amount'].sum()
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
    col_kpi1.metric("Receita Total (Ano)", f"R$ {total_income_year:,.2f}")
    col_kpi2.metric("Despesa Total (Ano)", f"R$ {total_expenses_year:,.2f}")
    col_kpi3.metric("Saldo Líquido (Ano)", f"R$ {total_balance_year:,.2f}", delta_color="normal")
    
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
    
    st.plotly_chart(fig, use_container_width=True, key=f"proj_chart_{proj_year}_{owner_filter}")
    
    st.dataframe(proj_data.style.format({
        "Entradas (R$)": "R$ {:,.2f}",
        "Saídas (R$)": "R$ {:,.2f}",
        "Saldo (R$)": "R$ {:,.2f}",
        "Acumulado (R$)": "R$ {:,.2f}"
    }), use_container_width=True)


