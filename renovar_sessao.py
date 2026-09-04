"""
Ferramenta de renovação de sessão do Meu Dinheiro — Select Build.

Corre localmente (Mac/Windows), abre um browser real para o utilizador
fazer login manualmente, e envia a sessão resultante automaticamente
para a app do Robô Select. Não precisa de Terminal nem de saber
programar — é só correr o programa.
"""

import os
import sys
import time

# TEM de ser definido ANTES de importar o playwright, e antes de
# qualquer chamada de instalação/lançamento do browser: em modo
# --onefile do PyInstaller, a pasta por omissão é temporária e
# apagada a cada execução — sem isto, o programa descarregava os
# ~150 MB do Chromium de novo, sempre, e mesmo assim falhava.
PASTA_BROWSERS = os.path.join(os.path.expanduser("~"), ".select-build-renovar-sessao", "browsers")
os.makedirs(PASTA_BROWSERS, exist_ok=True)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PASTA_BROWSERS

sys.stdout.reconfigure(line_buffering=True)  # ver as mensagens em tempo real

import requests
from playwright.sync_api import sync_playwright

# Chave de âmbito estreito — só serve para actualizar a sessão, nada
# mais (ver robotselect_api/main.py, checar_api_key_ou_upload). O valor
# real NUNCA fica neste ficheiro (este repositório é público): é
# substituído aqui só no momento da compilação, a partir de um secret
# do GitHub Actions (ver .github/workflows/build.yml). Quem correr
# "python renovar_sessao.py" directamente do código-fonte, sem passar
# pela compilação, recebe este marcador e a chamada à API falha com
# 401 — o que é o comportamento esperado.
ROBOT_API_URL = "https://robotselect-api-222619808650.us-central1.run.app"
SESSAO_UPLOAD_KEY = "__SESSAO_UPLOAD_KEY_PLACEHOLDER__"

# Mostra um aviso grande dentro da própria janela do browser — é para
# ali que o utilizador está a olhar durante o login, não para o
# Terminal por trás. Sem isto, a janela fechava-se sozinha sem
# nenhuma confirmação visível de que tinha corrido bem (ou mal).
JS_MOSTRAR_AVISO = """([mensagem, cor]) => {
    let el = document.getElementById('__select_build_aviso__');
    if (!el) {
        el = document.createElement('div');
        el.id = '__select_build_aviso__';
        el.style.position = 'fixed';
        el.style.top = '0';
        el.style.left = '0';
        el.style.right = '0';
        el.style.zIndex = '2147483647';
        el.style.padding = '28px 20px';
        el.style.fontSize = '20px';
        el.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        el.style.textAlign = 'center';
        el.style.color = 'white';
        el.style.boxShadow = '0 2px 12px rgba(0,0,0,0.3)';
        document.body.appendChild(el);
    }
    el.style.background = cor;
    el.textContent = mensagem;
}"""


def mostrar_aviso(page, mensagem, cor):
    try:
        page.evaluate(JS_MOSTRAR_AVISO, [mensagem, cor])
    except Exception:
        pass  # A janela pode já ter sido fechada pelo utilizador — sem problema.


def garantir_browser_instalado():
    """Na primeira vez que o programa corre, o Chromium ainda não está
    descarregado — o Playwright trata disso sozinho, só é preciso pedir
    explicitamente (o download é de uns 150 MB, só acontece uma vez)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return
    except Exception:
        pass

    print("Primeira utilização — a preparar o browser (só demora da primeira vez)...")
    # Chama a instalação directamente no mesmo processo (não por
    # sub-processo com "sys.executable") — dentro de um executável já
    # empacotado (PyInstaller), sys.executable é o próprio programa, não
    # um interpretador Python normal, por isso "-m playwright" não
    # funcionaria como sub-processo.
    from playwright.__main__ import main as playwright_cli

    argv_original = sys.argv
    sys.argv = ["playwright", "install", "chromium"]
    try:
        try:
            playwright_cli()
        except SystemExit as saida:
            if saida.code not in (None, 0):
                raise
    finally:
        sys.argv = argv_original
    print("Pronto.")
    print()


def main():
    print("=" * 60)
    print("Select Build — Renovação de Sessão do Meu Dinheiro")
    print("=" * 60)
    print()

    garantir_browser_instalado()

    print("Vai abrir uma janela do browser. Faz login normalmente")
    print("(usa o formulário de Email + Senha, não o botão do Google).")
    print("Se o Meu Dinheiro pedir um código de confirmação por email,")
    print("preenche esse código também — só depois é que o login conta")
    print("como concluído.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://app.meudinheiroweb.com.br")
        mostrar_aviso(
            page,
            "👋 Faz login (inclui o código de confirmação, se for pedido). "
            "Depois volta ao Terminal e prime Enter.",
            "#0d6efd",
        )

        # Confirmação manual em vez de deteção automática: a app pode ter
        # ecrãs intermédios imprevisíveis (ex: pedido de código de
        # confirmação por email), que também não têm o campo de email
        # visível — uma deteção automática apanhava esses ecrãs como
        # "login concluído" e capturava a sessão cedo demais, antes do
        # login estar mesmo terminado. Pedir confirmação ao utilizador
        # é mais simples e mais robusto do que tentar adivinhar todos os
        # ecrãs possíveis.
        print("Quando o login estiver mesmo concluído (já dentro da app),")
        input("volta aqui e prime Enter...")

        # Verificação de cortesia: avisa se ainda parecer estar no ecrã
        # de login, mas não bloqueia — a decisão final é sempre do
        # utilizador.
        try:
            ainda_com_formulario = (
                page.locator("input[name='email']").count() > 0
                or page.locator("input[type='password']").count() > 0
            )
        except Exception:
            ainda_com_formulario = False
        if ainda_com_formulario:
            mostrar_aviso(page, "⚠️ Ainda vejo um formulário de login nesta página.", "#fd7e14")
            print()
            print("⚠️  Ainda parece haver um formulário de login/senha nesta página.")
            input("Confirma que já terminaste o login e prime Enter para continuar...")

        print()
        print("A enviar a sessão para a app...")
        mostrar_aviso(page, "A guardar a sessão, aguarda um momento...", "#0d6efd")

        storage_state = context.storage_state()

        # O envio acontece ainda com o browser aberto, para o resultado
        # (sucesso ou falha) poder ser mostrado na própria janela antes
        # de a fechar — não só no Terminal, que o utilizador pode nem
        # estar a ver.
        sucesso = False
        try:
            resposta = requests.put(
                f"{ROBOT_API_URL}/sessao",
                headers={"X-API-Key": SESSAO_UPLOAD_KEY, "Content-Type": "application/json"},
                json={"storage_state": storage_state},
                timeout=30,
            )
            if resposta.status_code == 200:
                sucesso = True
                print()
                print("✅ Sessão renovada com sucesso!")
                print("   O robô já vai usar esta sessão nova na próxima corrida.")
                mostrar_aviso(
                    page,
                    "✅ Sessão renovada com sucesso! Já podes fechar esta janela.",
                    "#198754",
                )
            else:
                print()
                print(f"❌ A app recusou a sessão (código {resposta.status_code}):")
                print(f"   {resposta.text}")
                mostrar_aviso(
                    page,
                    "❌ A app recusou a sessão. Fecha esta janela e avisa a Select Build.",
                    "#dc3545",
                )
        except Exception as erro:
            print()
            print(f"❌ Não consegui contactar a app: {erro}")
            print("   Verifica a tua ligação à internet e tenta novamente.")
            mostrar_aviso(
                page,
                "❌ Falha de ligação à app. Fecha esta janela e tenta novamente.",
                "#dc3545",
            )

        if sucesso:
            time.sleep(4)  # dá tempo para o utilizador ler o aviso antes de fechar
        browser.close()

    input("Prime Enter para sair...")


if __name__ == "__main__":
    main()
