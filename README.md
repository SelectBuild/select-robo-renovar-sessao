# Renovação de Sessão — Select Build

Ferramenta de computador (Mac/Windows) para renovar a sessão de login do
"Meu Dinheiro" usada pelo robô do Robô Select. Não é preciso saber
programar nem usar o Terminal — é só descarregar e executar.

## Para quem vai usar

1. Descarrega o ficheiro da tua plataforma na página de
   [Releases](../../releases/latest):
   - **Mac:** `RenovarSessaoSelectBuild-mac`
   - **Windows:** `RenovarSessaoSelectBuild-windows.exe`
2. Executa o ficheiro (o sistema operativo pode mostrar um aviso de
   "programa de origem não identificada" — isto é normal, porque a
   ferramenta ainda não tem uma assinatura digital paga; escolhe
   "Executar/Abrir mesmo assim").
3. Vai abrir uma janela de terminal e, a seguir, uma janela de browser.
4. Faz login no Meu Dinheiro com o **formulário de Email + Senha**
   (não uses o botão "Entrar com a Google" — esse é bloqueado).
5. Assim que o login terminar, a ferramenta deteta automaticamente,
   envia a nova sessão para a app do Robô Select, e pode fechar a
   janela.

## Como funciona (nota técnica)

- Escrita em Python + [Playwright](https://playwright.dev/).
- Na primeira execução, descarrega o Chromium (~150 MB) para uma pasta
  própria e persistente no computador do utilizador — só acontece uma
  vez.
- Abre esse Chromium em modo visível para o login manual.
- Depois de detectar o login, extrai os cookies de sessão
  (`context.storage_state()`) e envia-os por HTTPS para o endpoint
  `PUT /sessao` da API do Robô Select, autenticado com uma chave de
  âmbito estreito (só permite substituir a sessão guardada — nada
  mais).
- Compilada com [PyInstaller](https://pyinstaller.org/) num único
  executável, para Mac e Windows, via GitHub Actions (ver
  `.github/workflows/build.yml`).

## Compilar localmente (opcional)

O código-fonte tem um marcador (`__SESSAO_UPLOAD_KEY_PLACEHOLDER__`) em
vez da chave real — o valor verdadeiro só existe como *secret*
encriptado do GitHub Actions e é injectado automaticamente durante a
compilação em CI (ver `.github/workflows/build.yml`). Uma compilação
local sem essa substituição gera um executável que falha com 401 ao
tentar enviar a sessão — normal, é só para testar o resto do fluxo.

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --console --name RenovarSessaoSelectBuild --collect-all playwright renovar_sessao.py
```

O executável fica em `dist/`.
