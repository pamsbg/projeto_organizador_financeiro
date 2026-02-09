"""
Script para testar a correcao do bug de Receitas (sem emojis para Windows)
"""
import pandas as pd
from datetime import date

def test_income_filter_logic():
    """Testa a logica de filtro corrigida"""
    print("="*70)
    print("TESTE: Logica Corrigida de Filtro de Receitas")
    print("="*70)
    
    # Simular banco de dados completo
    full_income = pd.DataFrame({
        'date': [
            date(2026, 1, 1), 
            date(2026, 2, 1), 
            date(2026, 3, 1),
            date(2026, 2, 1)  # Renato em Fevereiro
        ],
        'source': ['Salario', 'Salario', 'Salario', 'Salario'],
        'amount': [15000, 15000, 15000, 14000],
        'type': ['Fixo', 'Fixo', 'Fixo', 'Fixo'],
        'recurrence': ['Mensal', 'Mensal', 'Mensal', 'Mensal'],
        'owner': ['Pamela', 'Pamela', 'Pamela', 'Renato']
    })
    
    # Criar _temp_id
    full_income['_temp_id'] = full_income.apply(
        lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                        str(row.get('amount', '')), str(row.get('owner', '')))), 
        axis=1
    ).astype(str)
    
    print("\nBanco de Dados Inicial:")
    print(full_income[['date', 'source', 'amount', 'owner']])
    
    # TESTE 1: Deletar Pamela de Fevereiro
    print("\n" + "="*70)
    print("TESTE 1: Deletar salario de Pamela em Fevereiro")
    print("="*70)
    
    selected_month_rec = 2  # Fevereiro
    selected_year_rec = 0   # Todos os anos
    owner_filter = "Pamela"
    
    # Aplicar filtros (LOGICA CORRIGIDA COM &)
    full_income['date'] = pd.to_datetime(full_income['date'])
    mask_keep = pd.Series([True] * len(full_income), index=full_income.index)
    
    if selected_month_rec != 0:
        mask_keep = mask_keep & (full_income['date'].dt.month != selected_month_rec)
    
    if selected_year_rec != 0:
        mask_keep = mask_keep & (full_income['date'].dt.year != selected_year_rec)
    
    if owner_filter != "Todos":
        mask_keep = mask_keep & (full_income['owner'] != owner_filter)  # CORRIGIDO: & ao inves de |
    
    untouched = full_income[mask_keep].copy()
    
    print(f"\nFiltros aplicados:")
    print(f"   - Mes: {selected_month_rec} (Fevereiro)")
    print(f"   - Pessoa: {owner_filter}")
    
    print(f"\nRegistros PRESERVADOS (fora do filtro):")
    print(untouched[['date', 'source', 'amount', 'owner']])
    
    # Simular display_income (o que o usuario ve e pode editar)
    display_mask = (full_income['date'].dt.month == selected_month_rec) & (full_income['owner'] == owner_filter)
    display_income = full_income[display_mask].copy()
    
    print(f"\nRegistros EDITAVEIS (dentro do filtro):")
    print(display_income[['date', 'source', 'amount', 'owner']])
    
    # Usuario DELETA TUDO que ve (Pamela Fevereiro)
    edited_income = pd.DataFrame()  # Vazio = deletou
    
    # Detectar delecoes
    original_ids = set(display_income['_temp_id'].dropna())
    edited_ids = set() if edited_income.empty else set(edited_income['_temp_id'].dropna())
    deleted_ids = original_ids - edited_ids
    
    print(f"\nIDs deletados: {len(deleted_ids)}")
    
    # Remover deletados de untouched
    if deleted_ids and '_temp_id' in untouched.columns:
        untouched = untouched[~untouched['_temp_id'].isin(deleted_ids)]
    
    # Resultado final
    final_income = untouched.drop(columns=['_temp_id'])
    
    print(f"\nRESULTADO FINAL apos salvar:")
    print(final_income[['date', 'source', 'amount', 'owner']])
    
    # Validacao
    expected_rows = 3  # Janeiro-Pamela, Marco-Pamela, Fevereiro-Renato
    success = len(final_income) == expected_rows
    
    if success:
        has_jan_pamela = any((final_income['date'].dt.month == 1) & (final_income['owner'] == 'Pamela'))
        has_mar_pamela = any((final_income['date'].dt.month == 3) & (final_income['owner'] == 'Pamela'))
        has_feb_renato = any((final_income['date'].dt.month == 2) & (final_income['owner'] == 'Renato'))
        no_feb_pamela = not any((final_income['date'].dt.month == 2) & (final_income['owner'] == 'Pamela'))
        
        all_correct = has_jan_pamela and has_mar_pamela and has_feb_renato and no_feb_pamela
        
        if all_correct:
            print("\nTESTE 1 PASSOU!")
            print("   [OK] Janeiro-Pamela preservado")
            print("   [OK] Marco-Pamela preservado")
            print("   [OK] Fevereiro-Renato preservado")
            print("   [OK] Fevereiro-Pamela deletado corretamente")
        else:
            print(f"\nTESTE 1 FALHOU! Dados incorretos.")
            success = False
    else:
        print(f"\nTESTE 1 FALHOU! Esperava {expected_rows} linhas, obteve {len(final_income)}")
    
    return success

if __name__ == "__main__":
    success = test_income_filter_logic()
    exit(0 if success else 1)
