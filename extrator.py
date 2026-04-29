import cv2
import numpy as np
import sys

from imagem_utils import resolver_caminho_imagem

class ExtratorCartaoResposta:
    def __init__(self, caminho_imagem, linhas=15, colunas=5):
        self.caminho_imagem = caminho_imagem
        self.linhas = linhas
        self.colunas = colunas
        self.imagem_original = None
        self.imagem_processada = None

    def carregar_e_pre_processar(self):
        self.imagem_original = cv2.imread(self.caminho_imagem)

        if self.imagem_original is None:
            raise FileNotFoundError(f"Imagem não encontrada: {self.caminho_imagem}")

        self.imagem_processada = cv2.cvtColor(self.imagem_original, cv2.COLOR_BGR2GRAY)

    def ordenar_pontos(self, pontos):
        pontos = np.array(pontos, dtype="float32")

        retangulo = np.zeros((4, 2), dtype="float32")

        soma = pontos.sum(axis=1)
        diff = np.diff(pontos, axis=1)

        retangulo[0] = pontos[np.argmin(soma)]   # topo esquerdo
        retangulo[1] = pontos[np.argmin(diff)]   # topo direito
        retangulo[2] = pontos[np.argmax(soma)]   # baixo direito
        retangulo[3] = pontos[np.argmax(diff)]   # baixo esquerdo

        return retangulo

    def recortar_bloco_inclinado(self, pontos_bloco):
        pontos_ordenados = self.ordenar_pontos(pontos_bloco)

        tl, tr, br, bl = pontos_ordenados

        largura_topo = np.linalg.norm(tr - tl)
        largura_base = np.linalg.norm(br - bl)
        largura = int(max(largura_topo, largura_base))

        altura_esq = np.linalg.norm(bl - tl)
        altura_dir = np.linalg.norm(br - tr)
        altura = int(max(altura_esq, altura_dir))

        destino = np.array([
            [0, 0],
            [largura - 1, 0],
            [largura - 1, altura - 1],
            [0, altura - 1]
        ], dtype="float32")

        matriz = cv2.getPerspectiveTransform(pontos_ordenados, destino)

        roi = cv2.warpPerspective(
            self.imagem_processada,
            matriz,
            (largura, altura)
        )

        return roi

    def extrair_respostas_por_bloco(self, pontos_bloco):
        roi_cinza = self.recortar_bloco_inclinado(pontos_bloco)

        h, w = roi_cinza.shape[:2]

        desfoque = cv2.GaussianBlur(roi_cinza, (5, 5), 0)

        _, roi_bin = cv2.threshold(
            desfoque,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        kernel = np.ones((3, 3), np.uint8)

        roi_limpa = cv2.morphologyEx(
            roi_bin,
            cv2.MORPH_OPEN,
            kernel,
            iterations=1
        )

        passo_y = h // self.linhas
        passo_x = w // self.colunas

        respostas_bloco = []

        for linha in range(self.linhas):
            linha_pixels = []

            for coluna in range(self.colunas):
                inicio_y = linha * passo_y
                fim_y = (linha + 1) * passo_y

                inicio_x = coluna * passo_x
                fim_x = (coluna + 1) * passo_x

                bolha_roi = roi_limpa[inicio_y:fim_y, inicio_x:fim_x]

                total_pixels_preenchidos = cv2.countNonZero(bolha_roi)

                linha_pixels.append(total_pixels_preenchidos)

            max_pixels = max(linha_pixels)

            limiar_ruido = (passo_x * passo_y) * 0.02

            if max_pixels > limiar_ruido:
                alternativa_marcada = np.argmax(linha_pixels)
                respostas_bloco.append(chr(65 + alternativa_marcada))
            else:
                respostas_bloco.append("Nula/Branco")

        return respostas_bloco

    def executar(self, blocos_coordenadas):
        self.carregar_e_pre_processar()

        gabarito_final = []

        for pontos_bloco in blocos_coordenadas:
            respostas = self.extrair_respostas_por_bloco(pontos_bloco)
            gabarito_final.extend(respostas)

        return gabarito_final


if __name__ == "__main__":
    origem_imagem = sys.argv[1] if len(sys.argv) > 1 else None
    caminho_imagem = resolver_caminho_imagem(origem_imagem)
    extrator = ExtratorCartaoResposta(caminho_imagem)

    coords_blocos_exemplo = [[(207, 1122), (354, 1112), (335, 1542), (176, 1552)], [(400, 1114), (542, 1104), (544, 1528), (390, 1539)], [(593, 1103), (729, 1091), (754, 1518), (598, 1527)], [(782, 1089), (918, 1083), (963, 1504), (811, 1512)], [(972, 1080), (1109, 1073), (1175, 1491), (1023, 1500)], [(1162, 1068), (1302, 1060), (1389, 1479), (1234, 1490)]]

    respostas = extrator.executar(coords_blocos_exemplo)

    print(respostas)
