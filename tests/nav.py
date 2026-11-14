"""Navegação nos testes: o app usa st.navigation; a troca de página passa pela chave "goto" (st.switch_page).

Editais mostra cards; o detalhe abre com "Ver detalhes". Para os testes antigos (que esperavam o detalhe do primeiro
edital logo de cara), goto('Editais') abre o primeiro card, como o usuário faria.
"""

LEGACY = {"Vínculos": "Editais", "Painel": "Início", "Match Inteligente": "Editais", "Radar de Editais": "Editais"}


def goto(app, page, open_first=True):
    app.session_state["goto"] = LEGACY.get(page, page)
    app.run()
    if open_first and LEGACY.get(page, page) == "Editais":
        first = next((b for b in app.button if b.label == "Ver detalhes"), None)
        if first is not None:
            first.click().run()
    return app
