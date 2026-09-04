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

TIMEOUT_SEGUNDOS = 600  # 10 minutos para o utilizador fazer login com calma


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
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://app.meudinheiroweb.com.br")

        print("A aguardar que termines o login (até 10 minutos)...")

        inicio = time.time()
        logado = False
        while time.time() - inicio < TIMEOUT_SEGUNDOS:
            na_app = "meudinheiroweb.com.br" in page.url
            if na_app and page.locator("input[name='email']").count() == 0:
                time.sleep(2)
                if "meudinheiroweb.com.br" in page.url and page.locator("input[name='email']").count() == 0:
                    logado = True
                    break
            time.sleep(2)

        if not logado:
            browser.close()
            print()
            print("❌ Não detectei o login dentro do tempo limite.")
            print("   Corre o programa novamente e tenta outra vez.")
            input("Prime Enter para sair...")
            sys.exit(1)

        print()
        print("✅ Login detectado! A enviar a sessão para a app...")

        storage_state = context.storage_state()
        browser.close()

    try:
        resposta = requests.put(
            f"{ROBOT_API_URL}/sessao",
            headers={"X-API-Key": SESSAO_UPLOAD_KEY, "Content-Type": "application/json"},
            json={"storage_state": storage_state},
            timeout=30,
        )
        if resposta.status_code == 200:
            print()
            print("✅ Sessão renovada com sucesso!")
            print("   O robô já vai usar esta sessão nova na próxima corrida.")
        else:
            print()
            print(f"❌ A app recusou a sessão (código {resposta.status_code}):")
            print(f"   {resposta.text}")
    except Exception as erro:
        print()
        print(f"❌ Não consegui contactar a app: {erro}")
        print("   Verifica a tua ligação à internet e tenta novamente.")

    input("Prime Enter para sair...")


if __name__ == "__main__":
    main()
