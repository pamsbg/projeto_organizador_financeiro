"""
Teste para verificar se o código de categorização está alterando corretamente
"""
import pandas as pd
import sys

def test_categorization():
    print("=" * 60)
    print("TESTE DE CATEGORIZAÇÃO")
    print("=" * 60)
    
    # 1. Criar DataFrame simulando st.session_state.df
    df = pd.DataFrame({
        'id': ['id1', 'id2', 'id3', 'id4'],
        'title': ['Uber Trip', 'Mercado', 'Nowpark', 'Restaurante'],
        'amount': [30, 100, 35, 50],
        'category': ['Outros', 'Outros', 'Outros', 'Lazer/Restaurantes']
    })
    
    print("\n1. DataFrame original:")
    print(df)
    print(f"   Total: {len(df)} linhas")
    
    # 2. Simular o que o Mágico faz (linhas 475-476 do app.py)
    changes = [
        {'id': 'id1', 'new_category': 'Transporte (Uber/99)'},
        {'id': 'id3', 'new_category': 'Transporte (Combustível/Manutenção)'}
    ]
    
    count = 0
    for change in changes:
        mask = df['id'] == change['id']
        print(f"\n2. Aplicando mudança para ID {change['id']}:")
        print(f"   Mask encontrou: {mask.sum()} linha(s)")
        df.loc[mask, 'category'] = change['new_category']
        count += 1
    
    print(f"\n3. DataFrame APÓS categorização:")
    print(df)
    print(f"   Total: {len(df)} linhas")
    print(f"   Mudanças aplicadas: {count}")
    
    # Validação
    if len(df) == 4 and df.loc[df['id'] == 'id1', 'category'].values[0] == 'Transporte (Uber/99)':
        print("\n✅ TESTE PASSOU! Nenhum dado foi perdido.")
        return True
    else:
        print(f"\n❌ TESTE FALHOU! Dados foram perdidos ou categorizados incorretamente.")
        print(f"   Esperado: 4 linhas")
        print(f"   Atual: {len(df)} linhas")
        return False

if __name__ == "__main__":
    success = test_categorization()
    sys.exit(0 if success else 1)
