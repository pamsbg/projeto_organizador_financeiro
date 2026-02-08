# 🔒 Como Configurar a Senha no Streamlit Cloud

Agora que seu aplicativo tem uma tela de login, você precisa definir qual é a senha lá no site do Streamlit.

## Passo a Passo

1.  Acesse seu painel no [share.streamlit.io](https://share.streamlit.io/).
2.  Ao lado do seu aplicativo, clique nos **3 pontinhos (⋮)** -> **Settings**.
3.  Vá na aba **Secrets**.
4.  Você verá uma caixa de texto vazia. Cole o seguinte conteúdo nela:

```toml
password = "SUA_SENHA_SECRETA_AQUI"
```

*(Troque `SUA_SENHA_SECRETA_AQUI` pela senha que você quer usar)*

5.  Clique em **Save**.

## Pronto!
A partir de agora, quem acessar seu link verá a tela de bloqueio e precisará dessa senha para entrar.

---
### 🏠 Para Uso Local (No seu computador)
Eu já criei um arquivo `.streamlit/secrets.toml` no seu computador com a senha padrão: **`admin`**.
Você pode abrir esse arquivo e mudar a senha se quiser. Ele **NÃO** é enviado para o GitHub (está protegido), então sua senha local fica segura.
