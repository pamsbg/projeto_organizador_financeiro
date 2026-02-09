"""
Teste simplificado da lógica de deleção
"""
import pandas as pd

def test_simple():
    print("=" * 60)
    print("TESTE SIMPLIFICADO DE DELEÇÃO")
    print("=" * 60)
    
    # 1. Criar DataFrame (simulando st.session_state.df)
    full_df = pd.DataFrame({
        'id': ['id1', 'id2', 'id3'],
        'title': ['A', 'B', 'C'],
        'amount': [100, 200, 300],
        'category': ['Outros', 'Outros', 'Transporte']
    })
    
    print("\n1. DataFrame completo:")
    print(full_df)
    
    # 2. Aplicar filtro (simulando filtros do streamlit)
    display_df = full_df[full_df['category'] == 'Outros'].copy()
    
    print("\n2. Após filtro (category == 'Outros'):")
    print(display_df)
    
    # 3. IMPORTANTE: Criar _row_hash ANTES de reset_index
    display_df['_row_hash'] = display_df['id'].astype(str)
    
    # 4. Reset index (como faz o streamlit)
    display_df = display_df.reset_index(drop=True)
    
    print("\n3. Após reset_index (com _row_hash):")
    print(display_df[['id', '_row_hash', 'title']])
    
    # 5. Salvar hashes e mapeamento
    original_hashes = set(display_df['_row_hash'].dropna())
    hash_to_id = dict(zip(display_df['_row_hash'], display_df['id']))
    
    print(f"\n4. Hashes salvos: {original_hashes}")
    print(f"   Mapeamento: {hash_to_id}")
    
    # 6. Simular editor retornando SEM uma linha (deletou index 0 - "A")
    edited_df = display_df.iloc[[1]].copy()  # Só ficou "C"
    edited_df = edited_df.drop(columns=['id', '_row_hash'])  # Editor oculta essas colunas
    
    print(f"\n5. Editor retornou (deletou 'A'):")
    print(edited_df)
    
    # 7. Reconstru ir hashes
    hash_by_index = dict(enumerate(display_df['_row_hash']))
    
    edited_hashes = set()
    for idx in edited_df.index:
        if idx in hash_by_index:
            edited_hashes.add(hash_by_index[idx])
    
    print(f"\n6. Hash by index: {hash_by_index}")
    print(f"   Edited hashes: {edited_hashes}")
    
    # 8. Detectar deleções
    deleted_hashes = original_hashes - edited_hashes
    deleted_ids = set(hash_to_id[h] for h in deleted_hashes if h in hash_to_id)
    
    print(f"\n7. RESULTADO:")
    print(f"   Hashes deletados: {deleted_hashes}")
    print(f"   IDs deletados: {deleted_ids}")
    
    # 9. Aplicar no DataFrame completo
    full_df_after = full_df[~full_df['id'].isin(deleted_ids)]
    
    print(f"\n8. DataFrame completo APÓS deleção:")
    print(full_df_after)
    
    # Validação
    if deleted_ids == {'id1'}:
        print("\n✅ TESTE PASSOU!")
        return True
    else:
        print(f"\n❌ TESTE FALHOU! Esperava deletar id1, mas deletou {deleted_ids}")
        return False

if __name__ == "__main__":
    test_simple()
