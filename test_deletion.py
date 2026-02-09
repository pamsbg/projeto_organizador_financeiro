"""
Script de teste para validar lógica de deleção de transações
"""
import pandas as pd
import sys

def test_deletion_logic():
    """Testa a lógica de deleção simulando o comportamento do Streamlit"""
    
    print("=" * 60)
    print("TESTE DE LÓGICA DE DELEÇÃO")
    print("=" * 60)
    
    # Simular DataFrame completo (st.session_state.df)
    full_df = pd.DataFrame({
        'id': ['id1', 'id2', 'id3', 'id4', 'id5'],
        'title': ['Compra A', 'Compra B', 'Compra C', 'Compra D', 'Compra E'],
        'amount': [100, 200, 300, 400, 500],
        'category': ['Outros', 'Alimentação', 'Outros', 'Transporte', 'Outros']
    })
    
    print("\n1. DataFrame completo (630 transações simuladas):")
    print(f"   Total: {len(full_df)} linhas")
    print(full_df.to_string())
    
    # Simular filtro (busca por "Outros")
    display_df = full_df[full_df['category'] == 'Outros'].copy()
    
    print("\n2. Após aplicar filtro (category == 'Outros'):")
    print(f"   Total: {len(display_df)} linhas")
    print(display_df.to_string())
    
    # SOLUÇÃO: Criar _row_hash ANTES de resetar index
    display_df['_row_hash'] = display_df['id'].astype(str)
    
    # Resetar index (como faz o Streamlit)
    display_df = display_df.reset_index(drop=True)
    
    print("\n3. Após reset_index e criar _row_hash:")
    print(display_df[['id', '_row_hash', 'title']].to_string())
    
    # Salvar hashes e mapeamento ANTES do editor
    original_hashes = set(display_df['_row_hash'].dropna())
    hash_to_id = dict(zip(display_df['_row_hash'], display_df['id']))
    
    print(f"\n4. Hashes salvos ANTES do editor: {original_hashes}")
    print(f"   Mapeamento hash→id: {hash_to_id}")
    
    # Simular st.data_editor retornando sem colunas ocultas E com linha deletada
    # Usuário deletou a linha de index 1 (Compra C)
    edited_df = display_df.iloc[[0, 2]].copy()  # Remove index 1
    # Simular que o editor NÃO retorna 'id' e '_row_hash'
    edited_df = edited_df.drop(columns=['id', '_row_hash'])
    
    print("\n5. Após edição no editor (deletou index 1 - Compra C):")
    print(f"   Total: {len(edited_df)} linhas")
    print(f"   Colunas disponíveis: {list(edited_df.columns)}")
    print(edited_df.to_string())
    
    # LÓGICA DE DETECÇÃO DE DELEÇÃO
    hash_by_index = dict(enumerate(display_df['_row_hash']))
    
    print(f"\n6. Mapeamento index→hash do display_df original:")
    print(f"   {hash_by_index}")
    
    # Reconstruir hashes que ainda existem
    edited_hashes = set()
    if not edited_df.empty:
        for idx in edited_df.index:
            if idx in hash_by_index:
                edited_hashes.add(hash_by_index[idx])
    
    print(f"\n7. Hashes reconstruídos após edição: {edited_hashes}")
    
    # Detectar deleções
    deleted_hashes = original_hashes - edited_hashes
    deleted_ids = set(hash_to_id[h] for h in deleted_hashes if h in hash_to_id)
    
    print(f"\n8. RESULTADO:")
    print(f"   Hashes deletados: {deleted_hashes}")
    print(f"   IDs a deletar: {deleted_ids}")
    
    # Aplicar deleção no DataFrame completo
    full_df_after = full_df[~full_df['id'].isin(deleted_ids)]
    
    print(f"\n9. DataFrame completo APÓS deleção:")
    print(f"   Total: {len(full_df_after)} linhas (era {len(full_df)})")
    print(full_df_after.to_string())
    
    # Validação
    if len(deleted_ids) == 1 and 'id3' in deleted_ids:
        print("\n✅ TESTE PASSOU! Deleção detectada corretamente!")
        return True
    else:
        print(f"\n❌ TESTE FALHOU! Esperado deletar ['id3'], mas deletou {deleted_ids}")
        return False

if __name__ == "__main__":
    success = test_deletion_logic()
    sys.exit(0 if success else 1)
