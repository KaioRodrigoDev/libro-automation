import cv2
import numpy as np
import sys
from extrator import ExtratorCartaoResposta
from imagem_utils import resolver_caminho_imagem

blocos_salvos = []
bloco_selecionado = None
ponto_selecionado = None
arrastando_bloco = False
ultimo_mouse_bloco = None

arrastando_imagem = False
ultimo_mouse = None
zoom = 1.0
offset_x = 0
offset_y = 0
tamanho_janela = (1280, 720)

raio_ponto = 4
area_selecao = 15
MAX_BLOCOS = 6
ZOOM_MIN = 0.2
ZOOM_MAX = 6.0
ZOOM_STEP = 1.2

def desenhar_poligono(img, pontos, cor):
    if len(pontos) > 1:
        for i in range(len(pontos)):
            pt1 = pontos[i]
            pt2 = pontos[(i + 1) % len(pontos)] if len(pontos) == 4 else pontos[i - 1]
            cv2.line(img, pt1, pt2, cor, 2)
    for p in pontos:
        cv2.circle(img, p, raio_ponto, cor, -1)

def desenhar_interface(imagem_base):
    img = imagem_base.copy()
    for idx, bloco in enumerate(blocos_salvos):
        cor = (255, 0, 0) if (arrastando_bloco and idx == bloco_selecionado) else (0, 255, 0)
        desenhar_poligono(img, bloco, cor)
        centro = tuple(np.mean(np.array(bloco), axis=0).astype(int))
        cv2.putText(
            img,
            str(idx + 1),
            centro,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            cor,
            2
        )
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
    global bloco_selecionado, ponto_selecionado, arrastando_bloco, ultimo_mouse_bloco
    global arrastando_imagem, ultimo_mouse, zoom, offset_x, offset_y

    largura_imagem = param["largura_imagem"]
    altura_imagem = param["altura_imagem"]
    x_img, y_img = tela_para_imagem(x, y, largura_imagem, altura_imagem)

    if event == cv2.EVENT_LBUTTONDOWN:
        for i_bloco, bloco in enumerate(blocos_salvos):
            for i_ponto, p in enumerate(bloco):
                distancia = np.linalg.norm(np.array(p) - np.array((x_img, y_img)))
                if distancia <= area_selecao:
                    bloco_selecionado = i_bloco
                    ponto_selecionado = i_ponto
                    return
        for i_bloco, bloco in enumerate(blocos_salvos):
            pts = np.array(bloco, np.int32)
            if cv2.pointPolygonTest(pts, (x_img, y_img), False) >= 0:
                bloco_selecionado = i_bloco
                arrastando_bloco = True
                ultimo_mouse_bloco = (x_img, y_img)
                return
    elif event == cv2.EVENT_MOUSEMOVE:
        if ponto_selecionado is not None and bloco_selecionado is not None:
            blocos_salvos[bloco_selecionado][ponto_selecionado] = (x_img, y_img)
        elif arrastando_bloco and bloco_selecionado is not None and ultimo_mouse_bloco is not None:
            dx = x_img - ultimo_mouse_bloco[0]
            dy = y_img - ultimo_mouse_bloco[1]
            novo_bloco = []
            for p in blocos_salvos[bloco_selecionado]:
                novo_bloco.append((p[0] + dx, p[1] + dy))
            blocos_salvos[bloco_selecionado] = novo_bloco
            ultimo_mouse_bloco = (x_img, y_img)
        elif arrastando_imagem and ultimo_mouse is not None:
            dx = x - ultimo_mouse[0]
            dy = y - ultimo_mouse[1]
            offset_x -= dx
            offset_y -= dy
            limitar_offsets(largura_imagem, altura_imagem)
            ultimo_mouse = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        ponto_selecionado = None
        arrastando_bloco = False
        bloco_selecionado = None
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
    return [tuple(map(int, p)) for p in ordenados]

def calibrar_posicoes(caminho_imagem):
    global blocos_salvos, arrastando_imagem, ultimo_mouse, zoom, offset_x, offset_y

    blocos_salvos = [
        [(149, 1346), (310, 1346), (304, 1827), (140, 1833)],
        [(370, 1343), (525, 1346), (528, 1833), (358, 1830)],
        [(591, 1340), (749, 1334), (752, 1827), (585, 1830)],
        [(809, 1340), (967, 1343), (982, 1827), (812, 1833)],
        [(1027, 1337), (1188, 1340), (1203, 1827), (1036, 1824)],
        [(1248, 1337), (1412, 1337), (1433, 1830), (1272, 1830)]
    ]

    arrastando_imagem = False
    ultimo_mouse = None
    zoom = 1.0
    offset_x = 0
    offset_y = 0

    imagem = cv2.imread(caminho_imagem)
    if imagem is None:
        raise FileNotFoundError(f"Erro: Imagem '{caminho_imagem}' não encontrada.")

    print("=== Ajuste Fino das Colunas ===")
    print("- G: Girar a imagem em 90 graus.")
    print("- Clique e segure no centro de um retângulo para MOVER A COLUNA INTEIRA.")
    print("- Clique e arraste nas bordas/pontas para ajustar o ângulo individual.")
    print("- Scroll do mouse controla o zoom | Botão direito arrasta a tela.")
    print("- ENTER ou ESPAÇO para confirmar o ajuste e iniciar extração.")
    print("- ESC finaliza sem salvar.\n")

    nome_janela = "Ajustar colunas"
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

        preview = desenhar_interface(imagem)
        viewport = criar_viewport(preview)

        cv2.putText(viewport, f"Zoom: {zoom:.2f}x", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(viewport, "G: Girar | ENTER: Salvar", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        cv2.imshow(nome_janela, viewport)
        tecla = cv2.waitKey(20) & 0xFF

        if tecla == 27:  # ESC
            cv2.destroyAllWindows()
            return []

        elif tecla in [ord('g'), ord('G')]:
            imagem = cv2.rotate(imagem, cv2.ROTATE_90_CLOCKWISE)
            cv2.imwrite(caminho_imagem, imagem)
            print("Imagem girada 90 graus!")
            cv2.setMouseCallback(nome_janela, mouse_callback, {"largura_imagem": imagem.shape[1], "altura_imagem": imagem.shape[0]})

        elif tecla in [ord('n'), ord('N')]:
            gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
            gray = cv2.bitwise_not(gray)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            coords = np.column_stack(np.where(thresh > 0))
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            (h, w) = imagem.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            imagem = cv2.warpAffine(imagem, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
            cv2.imwrite(caminho_imagem, imagem)
            print(f"Inclinação de {angle:.2f} graus corrigida!")
            cv2.setMouseCallback(nome_janela, mouse_callback, {"largura_imagem": imagem.shape[1], "altura_imagem": imagem.shape[0]})

        elif tecla in [13, 32]:  # ENTER ou ESPAÇO
            blocos_salvos = [ordenar_pontos(b) for b in blocos_salvos]
            print("Configuração de blocos salva com sucesso!")
            break

    cv2.destroyAllWindows()
    return blocos_salvos

def executar_fluxo_completo(caminho_imagem):
    try:
        coordenadas = calibrar_posicoes(caminho_imagem)
        if not coordenadas:
            print("\nOperação cancelada ou sem coordenadas.")
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
