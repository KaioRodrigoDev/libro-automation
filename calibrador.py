import cv2
import numpy as np
import glob

pontos = []
ponto_selecionado = None

raio_ponto = 2
area_selecao = 8
MAX_BLOCOS = 6


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


def mouse_callback(event, x, y, flags, param):
    global ponto_selecionado

    if event == cv2.EVENT_LBUTTONDOWN:
        if len(pontos) < 4:
            pontos.append((x, y))
            return

        for i, p in enumerate(pontos):
            distancia = np.linalg.norm(np.array(p) - np.array((x, y)))

            if distancia <= area_selecao:
                ponto_selecionado = i
                break

    elif event == cv2.EVENT_MOUSEMOVE:
        if ponto_selecionado is not None:
            pontos[ponto_selecionado] = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        ponto_selecionado = None


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
    global pontos

    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        raise FileNotFoundError(f"Erro: Imagem '{caminho_imagem}' não encontrada.")

    blocos_salvos = []

    print("=== Modo de Calibração com Inclinação ===")
    print("- Para cada coluna, clique nos 4 vértices.")
    print("- Ajuste arrastando cada ponto.")
    print("- ENTER ou ESPAÇO salva a coluna atual.")
    print("- R reseta a coluna atual.")
    print("- U remove a última coluna salva.")
    print("- ESC finaliza.\n")

    nome_janela = "Selecionar colunas inclinadas"
    cv2.namedWindow(nome_janela)
    cv2.setMouseCallback(nome_janela, mouse_callback)

    while True:
        preview = desenhar_interface(imagem, blocos_salvos, pontos)
        cv2.imshow(nome_janela, preview)

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


if __name__ == "__main__":
    arquivos = glob.glob("image.*")

    if not arquivos:
        raise FileNotFoundError("Nenhuma imagem encontrada com nome 'image.*'")

    caminho_imagem = arquivos[0]  # pega a primeira que encontrar

    calibrar_posicoes(caminho_imagem)