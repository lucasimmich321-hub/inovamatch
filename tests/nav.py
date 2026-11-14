"""Navegação nos testes: o app usa st.navigation; a troca de página passa pela chave "goto" (st.switch_page)."""

LEGACY = {"Vínculos": "Editais", "Painel": "Início", "Match Inteligente": "Editais", "Radar de Editais": "Editais"}


def goto(app, page):
    app.session_state["goto"] = LEGACY.get(page, page)
    return app.run()
