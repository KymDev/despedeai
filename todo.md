## Tarefas para corrigir o download de PDF

### Fase 1: Análise do código atual
- [x] Ler `app_simplificado.py` para entender as rotas e a lógica de geração/download de PDF.
- [x] Ler `index.html` para entender como as requisições de download são feitas no frontend.
- [x] Ler `requirements.txt` e instalar as dependências.

### Fase 2: Identificação e correção dos problemas de download
- [x] Verificar a rota `/api/baixar-curriculo` e `/api/baixar-carta` no `app_simplificado.py`.
- [x] Garantir que `send_file` esteja configurado corretamente para forçar o download.
- [x] Verificar se o `mimetype` está correto (`application/pdf`).
- [x] Assegurar que o `BytesIO` está sendo lido do início (`pdf_buffer.seek(0)`).
- [x] Analisar o JavaScript no `index.html` para as funções `baixarCurriculo()` e `baixarCarta()`.
- [x] Confirmar que o frontend está tratando a resposta do backend corretamente para iniciar o download (usando `response.blob()` e `window.URL.createObjectURL`).
- [x] Implementar quaisquer correções necessárias no backend (Python) e frontend (HTML/JavaScript).
- [x] Adicionar headers HTTP adicionais para garantir o download (`Content-Disposition`, `Cache-Control`, etc.).
- [x] Melhorar o tratamento de erros no JavaScript com verificação de `content-type`.
- [x] Criar modelos de cartas de demissão para testar a funcionalidade.

### Fase 3: Teste e validação das correções
- [ ] Iniciar a aplicação Flask.
- [ ] Acessar a interface web no navegador.
- [ ] Preencher os formulários de currículo e carta de demissão.
- [ ] Tentar baixar os PDFs gerados e verificar se o download ocorre sem erros.

### Fase 4: Entrega dos arquivos corrigidos
- [ ] Empacotar os arquivos `app_simplificado.py` e `index.html` corrigidos.
- [ ] Notificar o usuário sobre a conclusão e fornecer os arquivos.

