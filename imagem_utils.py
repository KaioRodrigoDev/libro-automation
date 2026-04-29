import glob
import mimetypes
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests


def _eh_url(valor):
    parsed = urlparse(valor)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _descobrir_extensao(url, content_type):
    extensao_url = Path(urlparse(url).path).suffix
    if extensao_url:
        return extensao_url

    extensao_tipo = mimetypes.guess_extension((content_type or "").split(";")[0].strip())
    return extensao_tipo or ".img"


def baixar_imagem(url):
    resposta = requests.get(url, timeout=30)
    resposta.raise_for_status()

    extensao = _descobrir_extensao(url, resposta.headers.get("Content-Type"))

    with tempfile.NamedTemporaryFile(delete=False, suffix=extensao) as arquivo_temp:
        arquivo_temp.write(resposta.content)
        return arquivo_temp.name


def resolver_caminho_imagem(origem=None):
    if origem:
        if _eh_url(origem):
            return baixar_imagem(origem)

        if os.path.exists(origem):
            return origem

        raise FileNotFoundError(f"Imagem não encontrada: {origem}")

    arquivos = glob.glob("image.*")
    if arquivos:
        return arquivos[0]

    raise FileNotFoundError(
        "Nenhuma imagem encontrada com nome 'image.*'. "
        "Informe um caminho local ou uma URL da imagem."
    )
