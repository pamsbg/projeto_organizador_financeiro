"""
Teste com a logica CORRIGIDA (OR)
"""
import pandas as pd
from datetime import date

def test_corrected_logic():
    # Banco completo
    full_income = pd.DataFrame({
        'date': [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 2, 1)],
        'source': ['Salario', 'Salario', 'Salario', 'Salario'],
        'amount': [15000, 15000, 15000, 14000],
        'owner': ['Pamela', 'Pamela', 'Pamela', 'Renato']
    })
    
    full_income['_temp_id'] = full_income.apply(
        lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                        str(row.get('amount', '')), str(row.get('owner', '')))), 
        axis=1
    ).astype(str)
    
    print("Banco Inicial:")
    print(full_income[['date', 'source', 'amount', 'owner']])
    
    # Filtros
    selected_month_rec = 2
    selected_year_rec = 0
    owner_filter = "Pamela"
    
    # LOGICA CORRIGIDA COM OR
    full_income['date'] = pd.to_datetime(full_income['date'])
    mask_keep = pd.Series([False] * len(full_income), index=full_income.index)
    
    if selected_month_rec != 0:
        mask_keep = mask_keep | (full_income['date'].dt.month != selected_month_rec)
    
    if selected_year_rec != 0:
        mask_keep = mask_keep | (full_income['date'].dt.year != selected_year_rec)
    
    if owner_filter != "Todos":
        mask_keep = mask_keep | (full_income['owner'] != owner_filter)
    
    untouched = full_income[mask_keep].copy()
    
    print(f"\nFiltros: Mes={selected_month_rec}, Owner={owner_filter}")
    print("\nRegistros PRESERVADOS:")
    print(untouched[['date', 'source', 'amount', 'owner']])
    
    # Display (o que o usuario ve)
    display_mask = (full_income['date'].dt.month == selected_month_rec) & (full_income['owner'] == owner_filter)
    display_income = full_income[display_mask].copy()
    
    print("\nRegistros EDITAVEIS:")
    print(display_income[['date', 'source', 'amount', 'owner']])
    
    # Usuario deleta tudo
    edited_income = pd.DataFrame()
    
    # Detectar delecoes
    original_ids = set(display_income['_temp_id'].dropna())
    edited_ids = set()
    deleted_ids = original_ids - edited_ids
    
    if deleted_ids and '_temp_id' in untouched.columns:
        untouched = untouched[~untouched['_temp_id'].isin(deleted_ids)]
    
    final_income = untouched.drop(columns=['_temp_id'])
    
    print("\nRESULTADO FINAL:")
    print(final_income[['date', 'source', 'amount', 'owner']])
    
    # Validar
    expected = 3
    if len(final_income) == expected:
        has_jan_pamela = any((final_income['date'].dt.month == 1) & (final_income['owner'] == 'Pamela'))
        has_mar_pamela = any((final_income['date'].dt.month == 3) & (final_income['owner'] == 'Pamela'))
        has_feb_renato = any((final_income['date'].dt.month == 2) & (final_income['owner'] == 'Renato'))
        no_feb_pamela = not any((final_income['date'].dt.month == 2) & (final_income['owner'] == 'Pamela'))
        
        if has_jan_pamela and has_mar_pamela and has_feb_renato and no_feb_pamela:
            print("\n[SUCESSO] Teste passou!")
            print("  [OK] Janeiro-Pamela preservado")
            print("  [OK] Marco-Pamela preservado")
            print("  [OK] Fevereiro-Renato preservado")
            print("  [OK] Fevereiro-Pamela deletado")
            return True
    
    print(f"\n[FALHA] Esperava {expected} linhas, obteve {len(final_income)}")
    return False

if __name__ == "__main__":
    success = test_corrected_logic( )
    exit(0 if success else 1)
