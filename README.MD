# Instruções pra rodar o automacao.py

1. Abrir o chrome com remote debugging ativado:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-devtools"
```
2. Abrir a pagina do arquivo da folha de respostas (https://enem.educacao.mg.gov.br/semchamada/app/folha-resposta/desempate/...)

2. Rodar o automacao.py

```powershell
python automacao.py
```
3. Fazer as marcações com o extrator que ele vai pegar a imagem automaticamente da pagina já

4. Quando marcar o ultimo retangulo do cartao resposta, ele ja extrair as marcações e ja vai preencher automaticamente na pagina la no chrome