import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from calibrador import executar_fluxo_completo


PORTA_DEBUG = 9222


def conectar_navegador():
    """Conecta ao Chrome já aberto com remote debugging."""
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{PORTA_DEBUG}")
    driver = webdriver.Chrome(options=options)
    return driver


def encontrar_url_imagem(driver):
    """Encontra a URL da imagem do cartão resposta na página."""
    images = driver.find_elements(By.TAG_NAME, "img")

    candidatas = []
    for img in images:
        src = img.get_attribute("src") or ""
        if not src or src.startswith("data:"):
            continue

        natural_width = driver.execute_script(
            "return arguments[0].naturalWidth;", img
        )
        natural_height = driver.execute_script(
            "return arguments[0].naturalHeight;", img
        )

        candidatas.append({
            "src": src,
            "width": natural_width or 0,
            "height": natural_height or 0,
        })

    if not candidatas:
        raise RuntimeError("Nenhuma imagem encontrada na página.")

    # Ordena por área (maior primeiro) - o cartão resposta geralmente é a maior
    candidatas.sort(key=lambda c: c["width"] * c["height"], reverse=True)

    escolhida = candidatas[0]
    print(f"  Imagem selecionada: {escolhida['width']}x{escolhida['height']}")
    return escolhida["src"]


def baixar_imagem_com_cookies(driver, url_imagem):
    """Baixa a imagem usando os cookies do navegador para autenticação."""
    session = requests.Session()

    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])

    resposta = session.get(url_imagem, timeout=30)
    resposta.raise_for_status()

    ext = Path(urlparse(url_imagem).path).suffix or ".png"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
        f.write(resposta.content)
        return f.name


def encontrar_iframe_questoes(driver):
    """Procura o iframe que contém as questões, se houver."""
    # Primeiro tenta no documento principal
    count = driver.execute_script(
        'return document.querySelectorAll("section.questoes mat-radio-group").length;'
    )
    if count > 0:
        return None  # Está no documento principal

    # Procura dentro de iframes
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for i, iframe in enumerate(iframes):
        try:
            driver.switch_to.frame(iframe)
            count = driver.execute_script(
                'return document.querySelectorAll("section.questoes mat-radio-group").length;'
            )
            if count > 0:
                print(f"  Questões encontradas dentro do iframe [{i}]")
                driver.switch_to.default_content()
                return iframe
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()

    return None


def navegar_para_aba_respostas(driver, max_tentativas=10):
    """Clica na aba 'Respostas' e aguarda os elementos carregarem."""
    # Tenta clicar na aba "Respostas"
    clicou = driver.execute_script("""
        const tabs = document.querySelectorAll('.mat-tab-label, [role="tab"]');
        for (const tab of tabs) {
            if (tab.textContent.trim().toLowerCase().includes('resposta')) {
                tab.click();
                return tab.textContent.trim();
            }
        }
        return null;
    """)

    if clicou:
        print(f"  Aba encontrada e clicada: '{clicou}'")
    else:
        print("  Aba 'Respostas' não encontrada, tentando preencher direto...")

    # Aguarda os elementos mat-radio-group aparecerem no DOM
    for i in range(max_tentativas):
        count = driver.execute_script(
            'return document.querySelectorAll("section.questoes mat-radio-group").length;'
        )
        if count > 0:
            print(f"  {count} questões encontradas no DOM.")
            return True
        time.sleep(0.5)

    print("  Timeout: elementos de resposta não apareceram.")
    return False


def preencher_respostas(driver, respostas):
    """Injeta JavaScript para preencher as respostas no site."""

    # Navega para a aba de respostas antes de preencher
    print("  Navegando para a aba de respostas...")
    if not navegar_para_aba_respostas(driver):
        print("  ERRO: Não foi possível encontrar a aba de respostas.")
        return {"preenchidas": 0, "erros": len(respostas), "total": len(respostas)}

    js_code = """
    const respostas = arguments[0];
    const grupos = document.querySelectorAll("section.questoes mat-radio-group");

    console.log("Questões encontradas:", grupos.length);
    let preenchidas = 0;
    let erros = 0;

    respostas.forEach((resposta, index) => {
        const grupo = grupos[index];
        if (!grupo) {
            console.warn(`Questão ${index + 1}: grupo não encontrado`);
            erros++;
            return;
        }

        const radio = grupo.querySelector(
            `input[type="radio"][value="${resposta}"]`
        );

        if (!radio) {
            console.warn(`Questão ${index + 1}: resposta ${resposta} não encontrada`);
            erros++;
            return;
        }

        radio.click();
        preenchidas++;
    });

    console.log("Finalizado");
    return {preenchidas: preenchidas, erros: erros, total: respostas.length};
    """

    resultado = driver.execute_script(js_code, respostas)
    return resultado


def main():
    print("=" * 50)
    print("  AUTOMAÇÃO - Extrator + Preenchimento")
    print("=" * 50)
    print(f"\nConectando ao Chrome (porta {PORTA_DEBUG})...")

    try:
        driver = conectar_navegador()
    except Exception as e:
        print(f"\nErro ao conectar ao Chrome: {e}")
        print(
            "\nVocê precisa iniciar o Chrome com remote debugging ativado."
        )
        print("Feche TODAS as janelas do Chrome e execute no terminal:\n")
        print(
            f'  chrome.exe --remote-debugging-port={PORTA_DEBUG}'
        )
        print(
            "\nOu, para o caminho completo:"
        )
        print(
            f'  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"'
            f" --remote-debugging-port={PORTA_DEBUG}"
        )
        sys.exit(1)

    print(f"Conectado! Página: {driver.title}")
    print(f"URL: {driver.current_url}")

    while True:
        print("\n" + "-" * 50)
        print(f"Página atual: {driver.title}")
        print(f"URL: {driver.current_url}\n")

        # 1. Encontrar URL da imagem
        print("Buscando imagens na página...")
        url_imagem = encontrar_url_imagem(driver)
        print(f"\nImagem selecionada: {url_imagem[:120]}")

        # 2. Baixar imagem (com cookies do navegador para autenticação)
        print("\nBaixando imagem...")
        caminho_imagem = baixar_imagem_com_cookies(driver, url_imagem)
        print(f"Imagem salva em: {caminho_imagem}")

        # 3. Abrir calibrador para marcar regiões
        print("\nAbrindo calibrador - marque as regiões das respostas...")
        coordenadas, respostas = executar_fluxo_completo(caminho_imagem)

        if not respostas:
            print("\nNenhuma resposta extraída.")
        else:
            # 4. Mostrar respostas extraídas
            print(f"\nRespostas extraídas ({len(respostas)}):")
            for i in range(0, len(respostas), 15):
                bloco = respostas[i:i + 15]
                nums = [f"{i + j + 1}:{r}" for j, r in enumerate(bloco)]
                print(f"  {', '.join(nums)}")

            # 5. Preencher automaticamente
            print("\nPreenchendo respostas no site...")
            resultado = preencher_respostas(driver, respostas)

            print(f"\nResultado:")
            print(f"  Preenchidas: {resultado['preenchidas']}")
            print(f"  Erros:       {resultado['erros']}")
            print(f"  Total:       {resultado['total']}")
            print("\nProcesso concluído com sucesso!")

        try:
            input("\nTecle Enter para iniciar uma nova extração na página atual (Ctrl+C para sair)...")
        except KeyboardInterrupt:
            print("\n\nEncerrando.")
            break


if __name__ == "__main__":
    main()
