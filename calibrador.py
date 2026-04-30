import cv2
import numpy as np
import sys

from extrator import ExtratorCartaoResposta
from imagem_utils import resolver_caminho_imagem

pontos = []
ponto_selecionado = None
arrastando_imagem = False
ultimo_mouse = None
zoom = 1.0
offset_x = 0
offset_y = 0
tamanho_janela = (1280, 720)

raio_ponto = 2
area_selecao = 8
MAX_BLOCOS = 6
ZOOM_MIN = 0.2
ZOOM_MAX = 6.0
ZOOM_STEP = 1.2


def desenhar_poligono(img, pontos, cor):
    if len(pontos) > 1:
        for i in range(len(pontos)):
            pt1 = pontos[i]
            pt2 = pontos[(i + 1) % len(pontos)] if len(pontos) == 4 else pontos[i - 1]
            cv2.line(img, pt1, pt2, cor, 1)

    for p in pontos:
        cv2.circle(img, p, raio_ponto, cor, -1)


def desenhar_interface(imagem_base, blocos_salvos, bloco_atual):
    img = imagem_base.copy()

    # Blocos já salvos em verde
    for idx, bloco in enumerate(blocos_salvos):
        desenhar_poligono(img, bloco, (0, 255, 0))

        centro = tuple(np.mean(np.array(bloco), axis=0).astype(int))
        cv2.putText(
            img,
            str(idx + 1),
            centro,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (0, 255, 0),
            1
        )

    # Bloco atual em vermelho
    desenhar_poligono(img, bloco_atual, (0, 0, 255))

    return img


def limitar_offsets(largura_imagem, altura_imagem):
    global offset_x, offset_y

    largura_zoom = max(1, int(largura_imagem * zoom))
    altura_zoom = max(1, int(altura_imagem * zoom))
    largura_view, altura_view = tamanho_janela

    offset_x = max(0, min(offset_x, max(0, largura_zoom - largura_view)))
    offset_y = max(0, min(offset_y, max(0, altura_zoom - altura_view)))


def atualizar_tamanho_janela(nome_janela):
    global tamanho_janela

    try:
        _, _, largura, altura = cv2.getWindowImageRect(nome_janela)
        if largura > 0 and altura > 0:
            tamanho_janela = (largura, altura)
    except cv2.error:
        pass


def tela_para_imagem(x, y, largura_imagem, altura_imagem):
    x_img = int((x + offset_x) / zoom)
    y_img = int((y + offset_y) / zoom)

    x_img = max(0, min(x_img, largura_imagem - 1))
    y_img = max(0, min(y_img, altura_imagem - 1))

    return x_img, y_img


def criar_viewport(imagem):
    largura_view, altura_view = tamanho_janela

    imagem_zoom = cv2.resize(
        imagem,
        None,
        fx=zoom,
        fy=zoom,
        interpolation=cv2.INTER_LINEAR
    )

    altura_zoom, largura_zoom = imagem_zoom.shape[:2]
    x_fim = min(offset_x + largura_view, largura_zoom)
    y_fim = min(offset_y + altura_view, altura_zoom)

    recorte = imagem_zoom[offset_y:y_fim, offset_x:x_fim]
    viewport = np.zeros((altura_view, largura_view, 3), dtype=np.uint8)
    viewport[:recorte.shape[0], :recorte.shape[1]] = recorte

    return viewport


def mouse_callback(event, x, y, flags, param):
    global ponto_selecionado, arrastando_imagem, ultimo_mouse, zoom, offset_x, offset_y

    largura_imagem = param["largura_imagem"]
    altura_imagem = param["altura_imagem"]
    x_img, y_img = tela_para_imagem(x, y, largura_imagem, altura_imagem)

    if event == cv2.EVENT_LBUTTONDOWN:
        if len(pontos) < 4:
            pontos.append((x_img, y_img))
            return

        for i, p in enumerate(pontos):
            distancia = np.linalg.norm(np.array(p) - np.array((x_img, y_img)))

            if distancia <= area_selecao:
                ponto_selecionado = i
                break

    elif event == cv2.EVENT_MOUSEMOVE:
        if ponto_selecionado is not None:
            pontos[ponto_selecionado] = (x_img, y_img)
        elif arrastando_imagem and ultimo_mouse is not None:
            dx = x - ultimo_mouse[0]
            dy = y - ultimo_mouse[1]
            offset_x -= dx
            offset_y -= dy
            limitar_offsets(largura_imagem, altura_imagem)
            ultimo_mouse = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        ponto_selecionado = None

    elif event == cv2.EVENT_RBUTTONDOWN:
        arrastando_imagem = True
        ultimo_mouse = (x, y)

    elif event == cv2.EVENT_RBUTTONUP:
        arrastando_imagem = False
        ultimo_mouse = None

    elif event == cv2.EVENT_MOUSEWHEEL:
        zoom_anterior = zoom
        if flags > 0:
            zoom = min(ZOOM_MAX, zoom * ZOOM_STEP)
        else:
            zoom = max(ZOOM_MIN, zoom / ZOOM_STEP)

        if zoom != zoom_anterior:
            offset_x = int(((x + offset_x) / zoom_anterior) * zoom - x)
            offset_y = int(((y + offset_y) / zoom_anterior) * zoom - y)
            limitar_offsets(largura_imagem, altura_imagem)


def ordenar_pontos(pontos):
    pts = np.array(pontos, dtype="float32")

    soma = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    ordenados = [
        pts[np.argmin(soma)],
        pts[np.argmin(diff)],
        pts[np.argmax(soma)],
        pts[np.argmax(diff)],
    ]

    # 🔹 converte aqui
    return [tuple(map(int, p)) for p in ordenados]


def calibrar_posicoes(caminho_imagem):
    global pontos, ponto_selecionado, arrastando_imagem, ultimo_mouse, zoom, offset_x, offset_y
    pontos = []
    ponto_selecionado = None
    arrastando_imagem = False
    ultimo_mouse = None
    zoom = 1.0
    offset_x = 0
    offset_y = 0

    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        raise FileNotFoundError(f"Erro: Imagem '{caminho_imagem}' não encontrada.")

    blocos_salvos = []

    print("=== Modo de Calibração com Inclinação ===")
    print("- Para cada coluna, clique nos 4 vértices.")
    print("- Ajuste arrastando cada ponto.")
    print("- Scroll do mouse controla o zoom.")
    print("- Botao direito arrasta a imagem.")
    print("- ENTER ou ESPAÇO salva a coluna atual.")
    print("- R reseta a coluna atual.")
    print("- U remove a última coluna salva.")
    print("- ESC finaliza.\n")

    nome_janela = "Selecionar colunas inclinadas"
    cv2.namedWindow(nome_janela, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(nome_janela, *tamanho_janela)
    cv2.setMouseCallback(
        nome_janela,
        mouse_callback,
        {"largura_imagem": imagem.shape[1], "altura_imagem": imagem.shape[0]}
    )

    while True:
        atualizar_tamanho_janela(nome_janela)
        limitar_offsets(imagem.shape[1], imagem.shape[0])

        preview = desenhar_interface(imagem, blocos_salvos, pontos)
        viewport = criar_viewport(preview)
        cv2.putText(
            viewport,
            f"Zoom: {zoom:.2f}x",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        cv2.putText(
            viewport,
            "Scroll: zoom | Botao direito: mover",
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1
        )
        cv2.imshow(nome_janela, viewport)

        tecla = cv2.waitKey(20) & 0xFF

        if tecla == 27:  # ESC
            break

        if tecla == ord("r"):
            pontos = []
            print("Coluna atual resetada.")

        if tecla == ord("u"):
            if blocos_salvos:
                removido = blocos_salvos.pop()
                print(f"Última coluna removida: {removido}")

        if tecla in [13, 32]:  # ENTER ou ESPAÇO
            if len(pontos) != 4:
                print("Você precisa marcar exatamente 4 pontos antes de salvar.")
                continue

            bloco_ordenado = ordenar_pontos(pontos)

            blocos_salvos.append(bloco_ordenado)
            print(f"Coluna {len(blocos_salvos)} salva: {bloco_ordenado}")

            pontos = []

            if len(blocos_salvos) >= MAX_BLOCOS:
                print("As 6 colunas foram selecionadas.")
                break

    cv2.destroyAllWindows()

    print("\n=== Coordenadas Extraídas mantendo inclinação ===")
    print(blocos_salvos)

    return blocos_salvos


def executar_fluxo_completo(caminho_imagem):
    try:
        coordenadas = calibrar_posicoes(caminho_imagem)

        if not coordenadas:
            print("\nNenhuma coordenada foi salva. Extração não executada.")
            return [], []

        extrator = ExtratorCartaoResposta(caminho_imagem)
        respostas = extrator.executar(coordenadas)

        print("\n=== Respostas Extraídas ===")
        print(respostas)

        return coordenadas, respostas
    finally:
        cv2.destroyAllWindows()


def solicitar_origem_imagem():
    return input(
        "Informe a URL ou caminho da imagem "
        "(ENTER para usar image.* ou 'sair' para encerrar): "
    ).strip()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        caminho_imagem = resolver_caminho_imagem(sys.argv[1])
        executar_fluxo_completo(caminho_imagem)
    else:
        while True:
            origem_imagem = solicitar_origem_imagem()

            if origem_imagem.lower() in {"sair", "exit"}:
                print("Encerrando o programa.")
                break

            try:
                caminho_imagem = resolver_caminho_imagem(origem_imagem or None)
                executar_fluxo_completo(caminho_imagem)
            except Exception as erro:
                print(f"\nErro ao processar a imagem: {erro}\n")
