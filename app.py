import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import uuid
import utils
import os

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
        try:
            # Tenta pegar a senha dos segredos (Cloud ou Local)
            correct_password = st.secrets["password"]
        except (FileNotFoundError, KeyError):
            # Fallback seguro para erro de configuração
            st.error("⚠️ Senha não configurada!")
            st.code(f"Esperado em secrets.toml: password = '...'", language="toml")
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

# --- SIDEBAR: CONFIGURAÇÕES ---
with st.sidebar:
    st.info(f"📂 Dados Carregados: {len(df)} registros")
    
    # Filtro de Pessoa (Global para TODAS as abas)
    owner_filter = st.selectbox("Filtrar por Pessoa", ["Todos", "Pamela", "Renato", "Família"], key="global_owner_filter")
    
    st.header("⚙️ Configurações")
    
    with st.expander("Gerenciar Categorias"):
        new_cat = st.text_input("Nova Categoria")
        if st.button("Adicionar"):
            if new_cat and new_cat not in settings["categories"]:
                settings["categories"].append(new_cat)
                utils.save_settings(settings)
                st.success(f"Categoria '{new_cat}' adicionada!")
                st.rerun()
            elif new_cat in settings["categories"]:
                st.warning("Categoria já existe.")
        
        cat_to_remove = st.selectbox("Remover Categoria", options=settings["categories"])
        if st.button("Remover"):
            if cat_to_remove in settings["categories"]:
                settings["categories"].remove(cat_to_remove)
                # Remove budget associado se existir
                if cat_to_remove in settings["budgets"]:
                    del settings["budgets"][cat_to_remove]
                utils.save_settings(settings)
                st.success(f"Categoria '{cat_to_remove}' removida!")
                st.rerun()

    st.divider()
    with st.expander("🗑️ Zona de Perigo (Apagar Dados)"):
        st.warning("Atenção: Ações aqui não podem ser desfeitas.")
        
        # Opção 1: Limpar Mês/Ano
        st.subheader("Limpar Período")
        del_month = st.selectbox("Mês", range(1, 13), index=datetime.now().month-1, key="del_m")
        del_year = st.selectbox("Ano", range(2024, 2031), index=2, key="del_y")
        
        if st.button("Limpar Dados do Mês/Ano"):
            if not df.empty:
                # Filtrar TUDO que NÃO for do mês/ano selecionado (Date e Reference Date)
                # Aqui vamos usar Reference Date como critério principal se existir, ou Date.
                # Para ser seguro, removemos se QUALQUER uma das datas bater? Ou só Reference?
                # Vamos remover pela Data de Referência (Competência), pois é como organizamos.
                
                df['ref_dt_obj'] = pd.to_datetime(df['reference_date'])
                mask_keep = ~((df['ref_dt_obj'].dt.month == del_month) & (df['ref_dt_obj'].dt.year == del_year))
                
                new_df_kept = df[mask_keep].drop(columns=['ref_dt_obj'])
                st.session_state.df = new_df_kept
                utils.save_data(new_df_kept)
                st.success(f"Dados de {del_month}/{del_year} apagados.")
                st.rerun()
            else:
                st.info("Nada para apagar.")
                
        # Opção 2: Reset Total
        if st.button("🔥 APAGAR TUDO (Reset)"):
            utils.save_data(pd.DataFrame(columns=df.columns))
            st.session_state.df = utils.load_data()
            st.success("Todos os dados foram apagados.")
            st.rerun()

# Criar Abas (Ordem Solicitada: Receitas, Importar, Transações, Dashboard, Planejamento, Projeções)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["💰 Receitas", "📥 Importar", "📝 Transações", "📊 Dashboard", "🎯 Planejamento", "🔮 Projeções"])

# --- ABA 1: RECEITAS (NOVO LOCAL) ---
with tab1:
    st.header("💰 Gerenciar Entradas (Salários, Rendas)")
    st.markdown("Adicione aqui suas fontes de renda. Você pode detalhar por data e pessoa.")
    
    income_df = utils.load_income_data()
    
    # Filtro Visual (Se selecionado pessoa específica)
    if owner_filter != "Todos":
        if 'owner' not in income_df.columns: income_df['owner'] = "Família"
        display_income = income_df[income_df['owner'] == owner_filter]
        st.caption(f"Editando receitas de: **{owner_filter}**")
    else:
        display_income = income_df
        st.caption("Editando **Todas** as receitas")

    # Resetar index para evitar colunas estranhas no editor e garantir alinhamento
    display_income = display_income.reset_index(drop=True)

    # Editor de Receitas
    edited_income = st.data_editor(
        display_income,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,  # <--- CORREÇÃO VISUAL: Esconde a coluna de índice sem nome
        column_config={
            "date": st.column_config.DateColumn("Data de Entrada", format="DD/MM/YYYY"),
            "source": st.column_config.TextColumn("Fonte (Ex: Salário, Aluguel)"),
            "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "type": st.column_config.SelectboxColumn("Tipo", options=["Fixo", "Variável", "Extra"]),
            "recurrence": st.column_config.SelectboxColumn("Recorrência", options=["Mensal", "Única", "Anual"]),
            "owner": st.column_config.SelectboxColumn("Pessoa", options=["Pamela", "Renato", "Família"])
        }, 
        key=f"income_editor_main_{owner_filter}" # Key dinâmica para forçar reset ao mudar filtro
    )
    
    if st.button("Salvar Receitas"):
        # Se estava filtrado, precisa garantir integridade
        if owner_filter != "Todos":
             # 1. Carrega o todo atualizado do disco (para não perder nada que outros mexeram)
             full_income = utils.load_income_data()
             if 'owner' not in full_income.columns: full_income['owner'] = "Família"
             
             # 2. Separa o que NÃO é desse dono (preserva)
             other_people_income = full_income[full_income['owner'] != owner_filter]
             
             # 3. Força a coluna 'owner' nas linhas novas/editadas caso o usuário tenha esquecido
             edited_income['owner'] = owner_filter 
             
             # 4. Junta tudo
             final_income = pd.concat([other_people_income, edited_income], ignore_index=True)
             
             # 5. Salva
             utils.save_income_data(final_income)
        else:
             # Se estava vendo todos, salva direto (o usuário é responsável por preencher o dono na coluna)
             utils.save_income_data(edited_income)
             
        st.success("Receitas atualizadas com sucesso!")
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
            # Referência: Primeiro dia do mês selecionado
            ref_date = date(imp_year, imp_month, 1)
            
            new_data, error = utils.process_uploaded_file(uploaded_file, reference_date=ref_date, owner=imp_owner)
            
            if error:
                st.error(error)
            else:
                st.session_state.temp_import_df = new_data
                st.session_state.temp_import_meta = {"ref": ref_date, "owner": imp_owner}
                st.success(f"Arquivo processado! {len(new_data)} transações encontradas.")
                
    # Se já processou, mostrar preview e botão confirmar
    if 'temp_import_df' in st.session_state and st.session_state.temp_import_df is not None:
        st.divider()
        st.subheader("Pré-visualização dos Dados")
        
        st.dataframe(st.session_state.temp_import_df.head(10), use_container_width=True)
        st.caption("Exibindo as 10 primeiras linhas.")
        
        col_act1, col_act2 = st.columns(2)
        
        with col_act1:
            if st.button("✅ Confirmar e Salvar no Banco de Dados"):
                # Mesclar e Salvar
                current_df = st.session_state.df
                new_df = st.session_state.temp_import_df
                
                combined_df, duplicates = utils.merge_and_save(current_df, new_df)
                
                st.session_state.df = combined_df # Atualiza estado
                
                # Limpar temp
                del st.session_state.temp_import_df
                
                st.success(f"Importação Concluída! {len(new_df) - duplicates} novas transações adicionadas.")
                if duplicates > 0:
                    st.warning(f"{duplicates} transações duplicadas foram ignoradas.")
                st.rerun()
                
        with col_act2:
            if st.button("❌ Cancelar"):
                del st.session_state.temp_import_df
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
        
        with st.expander("🧙‍♂️ Mágico de Categorização (Regras + Aprendizado)"):
            st.write("Analisa suas transações usando:")
            st.markdown("- **Regras fixas** (Nowpark → Transporte, Uber → Transporte, etc)")
            st.markdown("- **Padrões aprendidos** das suas categorizações manuais anteriores")
            
            col_wiz1, col_wiz2 = st.columns(2)
            with col_wiz1:
                wiz_target = st.radio("Escopo da Busca:", ["Apenas 'Outros'", "Todas as Categorias"], index=0)
            
            if st.button("🔍 Buscar Sugestões"):
                # Aprende com dados históricos
                learned_patterns = ml_patterns.learn_patterns_from_data(df)
                
                wiz_suggestions = []
                for idx, row in df.iterrows():
                    # Pular categorias de sistema/pagamento
                    if row['category'] in ['Pagamento/Crédito']: 
                        continue
                    
                    # Filtro de escopo
                    if wiz_target == "Apenas 'Outros'" and row['category'] not in ['Outros', '', 'Geral']: 
                        continue

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
                        "Valor": row['amount'],  # NOVO: Mostrar valor
                        "Categoria Atual": row['category'],
                        "Nova Categoria": suggested,  # Agora é "Nova Categoria" e editável
                        "Aplicar?": True if suggested else False  # Desmarca se não tem sugestão
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
                        "Valor": st.column_config.NumberColumn(
                            "Valor (R$)",
                            format="R$ %.2f"
                        ),
                        "Nova Categoria": st.column_config.SelectboxColumn(
                            "Nova Categoria",
                            options=[""] + settings["categories"],  # "" = não alterar
                            required=False
                        ),
                        "Aplicar?": st.column_config.CheckboxColumn("Aplicar?", default=True)
                    },
                    disabled=["Data", "Descrição", "Valor", "Categoria Atual"],  # "Nova Categoria" é EDITÁVEL agora
                    hide_index=True,
                    use_container_width=True,
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
                        st.success(f"✅ {count} transações categorizadas com sucesso!")
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
            
        if selected_year_trans != 0:
            display_df = display_df[display_df['date'].dt.year == selected_year_trans]
        
        # Ordenação Multi-Coluna (Solicitação do Usuário)
        st.caption("Ordenação Personalizada")
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            # Opções amigáveis para o usuário
            sort_cols = st.multiselect("Ordenar por:", ['DATA', 'VALOR', 'CATEGORIA', 'DESCRIÇÃO', 'PESSOA'], default=['DATA'])
        with col_sort2:
            sort_order = st.radio("Ordem:", ["Crescente", "Decrescente"], horizontal=True, index=1)
            
        if sort_cols:
            ascending = True if sort_order == "Crescente" else False
            
            # Mapeamento de nomes amigáveis para colunas reais
            col_map = {
                'DATA': 'date', 
                'VALOR': 'amount', 
                'CATEGORIA': 'category', 
                'DESCRIÇÃO': 'title', 
                'PESSOA': 'owner'
            }
            real_cols = [col_map[c] for c in sort_cols]
            
            display_df = display_df.sort_values(by=real_cols, ascending=ascending)
    
    # Resetar index para evitar warnings com hide_index=True e num_rows=dynamic
    display_df = display_df.reset_index(drop=True)
            
    # Editor de Dados (Sempre visível para adição)
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": None, # Ocultar coluna ID
            "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "category": st.column_config.SelectboxColumn("Categoria", options=settings["categories"]),
            "owner": st.column_config.SelectboxColumn("Pessoa", options=["Pamela", "Renato", "Família"])
        },
        key="trans_editor"  # Chave única para evitar conflitos
    )
    
    # Botão Salvar
    if st.button("💾 Salvar Alterações", key="save_trans_btn"):
        # CORREÇÃO: Mesclar edited_df de volta no DataFrame completo
        # Se estamos vendo dados filtrados, precisamos atualizar apenas os registros editados
        
        # Identificar novos registros (sem ID)
        new_rows = edited_df[edited_df['id'].isna() | (edited_df['id'] == '')]
        
        # Atualizar registros existentes no df principal
        for idx, row in edited_df.iterrows():
            if pd.notna(row['id']) and row['id'] != '':
                # Atualizar registro existente
                mask = st.session_state.df['id'] == row['id']
                if mask.any():
                    for col in edited_df.columns:
                        st.session_state.df.loc[mask, col] = row[col]
        
        # Adicionar novos registros
        if not new_rows.empty:
            new_rows = new_rows.copy()
            for idx in new_rows.index:
                new_rows.loc[idx, 'id'] = str(uuid.uuid4())
            st.session_state.df = pd.concat([st.session_state.df, new_rows], ignore_index=True)
        
        utils.save_data(st.session_state.df)
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
            
            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                st.subheader("Gastos por Categoria")
                if not expenses_df.empty:
                    fig_pie = px.pie(expenses_df, names='category', values='amount', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_pie, use_container_width=True, key="dash_pie_chart")
                else:
                    st.info("Sem gastos.")
            
            with row1_col2:
                st.subheader("Top 5 Locais")
                if not expenses_df.empty:
                     top_places = expenses_df.copy()
                     top_places['clean_title'] = top_places['title'].str.replace(r'(Pg \*|Mp \*|Dl\*)', '', regex=True).str.strip()
                     top_places['clean_title'] = top_places['clean_title'].apply(lambda x: x.split('-')[0].strip())
                     top5 = top_places.groupby('clean_title')['amount'].sum().nlargest(5).reset_index()
                     fig_bar_top = px.bar(top5, x='amount', y='clean_title', orientation='h', text_auto='.2s')
                     fig_bar_top.update_layout(yaxis={'categoryorder':'total ascending'})
                     st.plotly_chart(fig_bar_top, use_container_width=True, key="dash_top5_chart")
            
            st.subheader("Evolução Diária")
            if not expenses_df.empty:
                daily_spend = expenses_df.groupby('date')['amount'].sum().reset_index()
                fig_bar = px.bar(daily_spend, x='date', y='amount')
                st.plotly_chart(fig_bar, use_container_width=True, key="dash_daily_chart")
        else:
            st.warning("Nenhum dado encontrado para o período/pessoa selecionados.")
    else:
        st.info("Adicione dados primeiro.")

# --- ABA 4: PLANEJAMENTO ---
# --- ABA 5: PLANEJAMENTO ---
with tab5:
    st.header("🎯 Planejamento Mensal de Gastos")
    st.markdown("Defina limites para suas categorias. **As metas agora são por mês!**")
    
    # Seletor de Período para Metas
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        meta_month = st.selectbox("Mês de Planejamento", list(months.keys()), format_func=lambda x: months[x], index=datetime.now().month-1, key="meta_month")
    with col_meta2:
        meta_year = st.number_input("Ano de Planejamento", 2024, 2030, datetime.now().year, key="meta_year")
        
    target_date = date(meta_year, meta_month, 1)
    
    # Carregar Orçamento (Considerando o Dono Selecionado)
    current_budgets = utils.get_budgets_for_date(settings, target_date, owner=owner_filter)
    
    active_categories = settings.get("categories", [])
    budget_data = []
    
    for cat in active_categories:
        budget_data.append({
            "Categoria": cat,
            "Meta (R$)": float(current_budgets.get(cat, 0.0))
        })
        
    budget_df = pd.DataFrame(budget_data)
    
    # --- NOVO: Adicionar Categoria Diretamente no Planejamento ---
    with st.expander("➕ Adicionar Nova Categoria de Meta"):
        new_cat_planning = st.text_input("Nome da Nova Categoria", key="new_cat_planning")
        if st.button("Criar Categoria"):
            if new_cat_planning and new_cat_planning not in settings["categories"]:
                settings["categories"].append(new_cat_planning)
                utils.save_settings(settings)
                st.success(f"Categoria '{new_cat_planning}' criada! Agora defina a meta abaixo.")
                st.rerun()
            elif new_cat_planning in settings["categories"]:
                st.warning("Essa categoria já existe.")
    # -------------------------------------------------------------
    
    # Permitir edição apenas se não for "Todos" (Agregado)
    disable_editing = (owner_filter == "Todos")
    
    if disable_editing:
        st.info("ℹ️ Selecione uma pessoa específica na barra lateral para **editar** as metas. No modo 'Todos', você vê a soma das metas de todos.")
        st.dataframe(budget_df, use_container_width=True, hide_index=True)
        edited_budget_df = budget_df # Apenas leitura
    else:
        edited_budget_df = st.data_editor(
            budget_df,
            column_config={
                "Meta (R$)": st.column_config.NumberColumn("Meta Mensal (R$)", format="R$ %.2f")
            },
            use_container_width=True,
            hide_index=True,
            key=f"budget_editor_{meta_month}_{meta_year}_{owner_filter}"
        )
    
        if st.button("💾 Salvar Metas deste Mês"):
            new_budgets = dict(zip(edited_budget_df["Categoria"], edited_budget_df["Meta (R$)"]))
            settings = utils.update_budget_for_date(settings, target_date, new_budgets, owner=owner_filter)
            utils.save_settings(settings)
            st.session_state.settings = settings
            st.success(f"Metas de {owner_filter} para {months[meta_month]}/{meta_year} salvas!")
            st.rerun()
        
    st.divider()
    st.subheader("Acompanhamento das Metas")
    
    if not df.empty:
        if not pd.api.types.is_datetime64_any_dtype(df['reference_date']):
             df['reference_date'] = pd.to_datetime(df['reference_date'])
             
        mask_meta = (df['reference_date'].dt.month == meta_month) & (df['reference_date'].dt.year == meta_year) & (df['category'] != 'Pagamento/Crédito')
        
        # Filtro de Pessoa no Planejamento
        # Se eu filtrar, vou comparar SÓ OS MEUS gastos com a Meta TOTAL? Ou Meta Proporcional?
        # Por enquanto, compara Gasto Filtrado vs Meta Total (Usuário vê o quanto ELE consumiu da meta).
        if owner_filter != "Todos":
             if 'owner' not in df.columns: df['owner'] = "Família"
             mask_meta = mask_meta & (df['owner'] == owner_filter)
             st.caption(f"Exibindo gastos de: **{owner_filter}** comparados à meta do orçamento.")
        else:
             st.caption("Exibindo gastos **Totais da Família** comparados à meta.")
        
        spent_df = df[mask_meta].groupby('category')['amount'].sum()
        
        for index, row in edited_budget_df.iterrows():
            cat = row['Categoria']
            limit = row['Meta (R$)']
            spent = spent_df.get(cat, 0.0)
            
            if limit > 0:
                progress = max(0.0, min(spent / limit, 1.0))
                st.write(f"**{cat}**: R$ {spent:,.2f} / R$ {limit:,.2f}")
                st.progress(progress)
                if spent >= limit:
                    st.error(f"⚠️ Limite estourado em {cat}!")
            else:
                 if spent > 0:
                     st.write(f"**{cat}**: R$ {spent:,.2f} (Sem meta definida)")

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
    # Prevenção de erro: Cria a coluna se não existir
    df['ref_dt'] = pd.to_datetime(df['reference_date'])
    
    mask_exp = (df['ref_dt'].dt.year == proj_year) & (df['category'] != 'Pagamento/Crédito') & (df['amount'] > 0)
    
    # Filtro opcional de dono
    if owner_filter != "Todos": 
         if 'owner' not in df.columns: df['owner'] = "Família"
         mask_exp = mask_exp & (df['owner'] == owner_filter)
         st.caption(f"Fluxo de Caixa apenas de: **{owner_filter}**")
    else:
         st.caption("Fluxo de Caixa **Consolidado (Família)**")

    expenses_grouped = df[mask_exp].groupby(df['ref_dt'].dt.month)['amount'].sum()
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


