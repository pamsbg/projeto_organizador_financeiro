"""
Teste da lógica de save de Receitas
"""
import pandas as pd
from datetime import date

def test_income_save():
    print("="*60)
    print("TESTE DE SAVE DE RECEITAS")
    print("="*60)
    
    # Simular full_income_df carregado
    full_income = pd.DataFrame({
        'date': [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)],
        'source': ['Salario', 'Salario', 'Salario'],
        'amount': [15000, 15000, 15000],
        'type': ['Fixo', 'Fixo', 'Fixo'],
        'recurrence': ['Mensal', 'Mensal', 'Mensal'],
        'owner': ['Pamela', 'Pamela', 'Pamela']
    })
    
    # Criar _temp_id
    full_income['_temp_id'] = full_income.apply(
        lambda row: hash((str(row.get('date', '')), str(row.get('source', '')), 
                        str(row.get('amount', '')), str(row.get('owner', '')))), 
        axis=1
    ).astype(str)
    
    print("\n1. Full Income:")
    print(full_income)
    
    # Simular filtro: selected_month = 2 (Fevereiro)
    selected_month = 2
    selected_year = 0  # Todos
    owner_filter = "Todos"
    
    # Criar máscara keep (inverter lógica)
    full_income['date'] = pd.to_datetime(full_income['date'])
    mask_keep = pd.Series([True] * len(full_income), index=full_income.index)
    
    if selected_month != 0:
        mask_keep = mask_keep & (full_income['date'].dt.month != selected_month)
    
    untouched = full_income[mask_keep]
    
    print(f"\n2. Filtro: Mês={selected_month}")
    print(f"   Untouched (fora do filtro): {len(untouched)} linhas")
    print(untouched)
    
    # Simular display_income (o que o usuário vê)
    display_income = full_income[full_income['date'].dt.month == selected_month].copy()
    print(f"\n3. Display (dentro do filtro): {len(display_income)} linhas")
    print(display_income)
    
    # Simular edited_income (usuário deletou a linha de Fevereiro)
    edited_income = pd.DataFrame()  # DELETOU TUDO!
    
    # Detectar deleções
    original_ids = set(display_income['_temp_id'].dropna())
    edited_ids = set() if edited_income.empty else set(edited_income['_temp_id'].dropna())
    deleted_ids = original_ids - edited_ids
    
    print(f"\n4. Deleções detectadas: {deleted_ids}")
    
    # Remover de untouched
    if deleted_ids:
        untouched = untouched[~untouched['_temp_id'].isin(deleted_ids)]
    
    print(f"\n5. Untouched após remoção: {len(untouched)} linhas")
    print(untouched)
    
    # Final
    final_income = untouched.copy()
    final_income = final_income.drop(columns=['_temp_id'])
    
    print(f"\n6. RESULTADO FINAL: {len(final_income)} linhas")
    print(final_income)
    
    if len(final_income) == 2:  # Janeiro e Março
        print("\n✅ TESTE PASSOU!")
        return True
    else:
        print(f"\n❌ TESTE FALHOU! Esperava 2 linhas, obteve {len(final_income)}")
        return False

if __name__ == "__main__":
    test_income_save()
