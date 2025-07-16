from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
import os
from datetime import datetime
from io import BytesIO
import json
import re
import unicodedata
import tempfile
import logging

# Imports adicionais para geração de PDF
from weasyprint import HTML, CSS
from io import StringIO

# Importa a calculadora aprimorada
from calculadora_trabalhista_aprimorada import CalculadoraTrabalhistaAprimorada

app = Flask(__name__)
app.secret_key = 'despede_ai_2025_simplificado'

# Configurar CORS para permitir downloads
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Inicializa a calculadora
calculadora = CalculadoraTrabalhistaAprimorada()

# Caminho para os modelos de cartas
MODELOS_PATH = os.path.join(os.getcwd(), "modelos")

def listar_modelos():
    """Lista os modelos de cartas disponíveis"""
    categorias = {}
    if os.path.exists(MODELOS_PATH):
        for categoria in os.listdir(MODELOS_PATH):
            cat_path = os.path.join(MODELOS_PATH, categoria)
            if os.path.isdir(cat_path):
                categorias[categoria] = [
                    f for f in os.listdir(cat_path) if f.endswith(".txt")
                ]
    return categorias

def sanitizar_nome(nome):
    """Sanitiza nomes de arquivo"""
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    nome = re.sub(r'[^\w\s-]', '', nome).strip().lower()
    nome = re.sub(r'[-\s]+', '_', nome)
    return nome

def gerar_carta(categoria, modelo, dados):
    """Gera carta de demissão baseada no modelo selecionado"""
    modelo_path = os.path.join(MODELOS_PATH, categoria, modelo)
    if not os.path.exists(modelo_path):
        return "Modelo não encontrado."

    with open(modelo_path, encoding='utf-8') as f:
        template = f.read()

    # Formatar data de entrega
    data_entrega = dados.get('data')
    if data_entrega:
        try:
            data_obj = datetime.strptime(data_entrega, '%Y-%m-%d')
            data_formatada = data_obj.strftime('%d de %B de %Y')
        except:
            data_formatada = datetime.today().strftime('%d de %B de %Y')
    else:
        data_formatada = datetime.today().strftime('%d de %B de %Y')

    local_data = f"{dados['cidade']}, {data_formatada}"

    return (
        template
        .replace("{nome}", dados["nome"])
        .replace("{cargo}", dados["cargo"])
        .replace("{empresa}", dados["empresa"])
        .replace("{cidade}", dados["cidade"])
        .replace("{motivo_opcional}", dados.get("motivo", ""))
        .replace("{local_data}", local_data)
    )

@app.route('/')
def index():
    """Página principal - serve o arquivo HTML único"""
    return send_file('index.html')

@app.route('/api/calcular-rescisao', methods=['POST'])
def api_calcular_rescisao():
    """API para cálculo da rescisão trabalhista"""
    try:
        dados_form = request.get_json()
        
        # Converte datas
        data_admissao = datetime.strptime(dados_form['data_admissao'], '%Y-%m-%d')
        data_demissao = datetime.strptime(dados_form['data_demissao'], '%Y-%m-%d')
        
        # Prepara dados para a calculadora
        dados_calculo = {
            'salario': float(dados_form['salario']),
            'data_admissao': data_admissao,
            'data_demissao': data_demissao,
            'tipo_demissao': dados_form['tipo_demissao'],
            'saldo_fgts': float(dados_form.get('saldo_fgts', 0)),
            'horas_extras_mes': float(dados_form.get('horas_extras_mes', 0)),
            'tipo_horas_extras': dados_form.get('tipo_horas_extras', 'normal'),
            'adicional_noturno': float(dados_form.get('adicional_noturno', 0)),
            'adicional_periculosidade': float(dados_form.get('adicional_periculosidade', 0)),
            'adicional_insalubridade': float(dados_form.get('adicional_insalubridade', 0)),
            'tipo_insalubridade': dados_form.get('tipo_insalubridade', 'insalubridade_minimo'),
            'dependentes_ir': int(dados_form.get('dependentes_ir', 0)),
            'aviso_trabalhado': dados_form.get('aviso_trabalhado') == 'true' or dados_form.get('aviso_trabalhado') == True,
            'ferias_vencidas': int(dados_form.get('ferias_vencidas', 0)),
            'decimo_vencido': dados_form.get('decimo_vencido', False),
            'dias_trabalhados_mes': int(dados_form.get('dias_trabalhados_mes')) if dados_form.get('dias_trabalhados_mes') and dados_form.get('dias_trabalhados_mes') != '' else None
        }
        
        # Calcula rescisão
        resultado = calculadora.calcular_rescisao_completa(dados_calculo)
        
        # Converte Decimal para float para JSON
        def decimal_to_float(obj):
            if hasattr(obj, 'quantize'):  # É um Decimal
                return float(obj)
            elif isinstance(obj, dict):
                return {k: decimal_to_float(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [decimal_to_float(item) for item in obj]
            else:
                return obj
        
        resultado_json = decimal_to_float(resultado)
        
        return jsonify({
            'success': True,
            'resultado': resultado_json
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/gerar-carta', methods=['POST'])
def api_gerar_carta():
    """API para geração de carta de demissão"""
    try:
        dados_form = request.get_json()
        
        categoria = dados_form['categoria']
        modelo = dados_form['modelo']
        
        dados_carta = {
            'nome': dados_form['nome'],
            'cargo': dados_form['cargo'],
            'empresa': dados_form['empresa'],
            'cidade': dados_form['cidade'],
            'motivo': dados_form.get('motivo', ''),
            'data': dados_form.get('data', '')
        }
        
        carta_gerada = gerar_carta(categoria, modelo, dados_carta)
        
        return jsonify({
            'success': True,
            'carta': carta_gerada
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/modelos-cartas')
def api_modelos_cartas():
    """API para listar modelos de cartas disponíveis"""
    try:
        categorias = listar_modelos()
        return jsonify({
            'success': True,
            'categorias': categorias
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/gerar-curriculo', methods=['POST'])
def api_gerar_curriculo():
    """API para geração de currículo"""
    try:
        dados_form = request.get_json()
        
        # Aqui implementaremos a lógica de geração de currículo
        # Por enquanto, retorna um placeholder
        curriculo_html = gerar_curriculo_html(dados_form)
        
        return jsonify({
            'success': True,
            'curriculo_html': curriculo_html
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def gerar_curriculo_html(dados):
    """Gera HTML do currículo baseado nos dados fornecidos"""
    
    # Template básico de currículo
    template_curriculo = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Currículo - {dados.get('nome_completo', 'Nome')}</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #fff;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0;
                color: #2c3e50;
                font-size: 2.5em;
            }}
            .header .contato {{
                margin-top: 10px;
                color: #7f8c8d;
            }}
            .secao {{
                margin-bottom: 30px;
            }}
            .secao h2 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 5px;
                margin-bottom: 15px;
            }}
            .experiencia-item, .educacao-item {{
                margin-bottom: 20px;
                padding-left: 20px;
                border-left: 3px solid #3498db;
            }}
            .experiencia-item h3, .educacao-item h3 {{
                margin: 0;
                color: #2c3e50;
            }}
            .experiencia-item .empresa, .educacao-item .instituicao {{
                font-weight: bold;
                color: #3498db;
            }}
            .experiencia-item .periodo, .educacao-item .periodo {{
                color: #7f8c8d;
                font-style: italic;
            }}
            .habilidades {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }}
            .habilidade {{
                background: #3498db;
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9em;
            }}
            @media print {{
                body {{ margin: 0; padding: 15px; }}
                .header {{ page-break-after: avoid; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{dados.get('nome_completo', 'Nome Completo')}</h1>
            <div class="contato">
                <p>
                    📧 {dados.get('email', 'email@exemplo.com')} | 
                    📱 {dados.get('telefone', '(00) 00000-0000')} | 
                    📍 {dados.get('cidade', 'Cidade')}, {dados.get('estado', 'Estado')}
                </p>
                {f"<p>🔗 LinkedIn: {dados.get('linkedin', '')}</p>" if dados.get('linkedin') else ""}
            </div>
        </div>
        
        {f'''
        <div class="secao">
            <h2>📋 Resumo Profissional</h2>
            <p>{dados.get('resumo_profissional', 'Resumo profissional não informado.')}</p>
        </div>
        ''' if dados.get('resumo_profissional') else ''}
        
        <div class="secao">
            <h2>💼 Experiência Profissional</h2>
            {gerar_experiencias_html(dados.get('experiencias', []))}
        </div>
        
        <div class="secao">
            <h2>🎓 Formação Acadêmica</h2>
            {gerar_educacao_html(dados.get('educacao', []))}
        </div>
        
        <div class="secao">
            <h2>🛠️ Habilidades</h2>
            <div class="habilidades">
                {gerar_habilidades_html(dados.get('habilidades', []))}
            </div>
        </div>
        
        {f'''
        <div class="secao">
            <h2>🌐 Idiomas</h2>
            {gerar_idiomas_html(dados.get('idiomas', []))}
        </div>
        ''' if dados.get('idiomas') else ''}
        
        {f'''
        <div class="secao">
            <h2>🏆 Certificações</h2>
            {gerar_certificacoes_html(dados.get('certificacoes', []))}
        </div>
        ''' if dados.get('certificacoes') else ''}
    </body>
    </html>
    """
    
    return template_curriculo

def gerar_experiencias_html(experiencias):
    """Gera HTML para experiências profissionais"""
    if not experiencias:
        return "<p>Nenhuma experiência profissional informada.</p>"
    
    html = ""
    for exp in experiencias:
        html += f"""
        <div class="experiencia-item">
            <h3>{exp.get('cargo', 'Cargo')}</h3>
            <div class="empresa">{exp.get('empresa', 'Empresa')}</div>
            <div class="periodo">{exp.get('periodo', 'Período')}</div>
            <p>{exp.get('descricao', 'Descrição das atividades.')}</p>
        </div>
        """
    return html

def gerar_educacao_html(educacao):
    """Gera HTML para formação acadêmica"""
    if not educacao:
        return "<p>Nenhuma formação acadêmica informada.</p>"
    
    html = ""
    for edu in educacao:
        html += f"""
        <div class="educacao-item">
            <h3>{edu.get('curso', 'Curso')}</h3>
            <div class="instituicao">{edu.get('instituicao', 'Instituição')}</div>
            <div class="periodo">{edu.get('periodo', 'Período')}</div>
        </div>
        """
    return html

def gerar_habilidades_html(habilidades):
    """Gera HTML para habilidades"""
    if not habilidades:
        return "<span class='habilidade'>Nenhuma habilidade informada</span>"
    
    html = ""
    for habilidade in habilidades:
        html += f"<span class='habilidade'>{habilidade}</span>"
    return html

def gerar_idiomas_html(idiomas):
    """Gera HTML para idiomas"""
    if not idiomas:
        return "<p>Nenhum idioma informado.</p>"
    
    html = "<ul>"
    for idioma in idiomas:
        html += f"<li><strong>{idioma.get('idioma', 'Idioma')}:</strong> {idioma.get('nivel', 'Nível')}</li>"
    html += "</ul>"
    return html

def gerar_certificacoes_html(certificacoes):
    """Gera HTML para certificações"""
    if not certificacoes:
        return "<p>Nenhuma certificação informada.</p>"
    
    html = "<ul>"
    for cert in certificacoes:
        html += f"<li><strong>{cert.get('nome', 'Certificação')}:</strong> {cert.get('instituicao', 'Instituição')} ({cert.get('ano', 'Ano')})</li>"
    html += "</ul>"
    return html

def gerar_curriculo_pdf_html(dados):
    """Gera HTML otimizado para PDF do currículo"""
    
    template_pdf = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Currículo - {dados.get('nome_completo', 'Nome')}</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.4;
                color: #333;
                font-size: 11pt;
                margin: 0;
                padding: 0;
            }}
            
            .header {{
                text-align: center;
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 15px;
                margin-bottom: 20px;
                page-break-after: avoid;
            }}
            
            .header h1 {{
                margin: 0 0 10px 0;
                color: #2c3e50;
                font-size: 24pt;
                font-weight: bold;
            }}
            
            .header .contato {{
                margin-top: 8px;
                color: #555;
                font-size: 10pt;
                line-height: 1.3;
            }}
            
            .secao {{
                margin-bottom: 20px;
                page-break-inside: avoid;
            }}
            
            .secao h2 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 3px;
                margin-bottom: 10px;
                font-size: 14pt;
                font-weight: bold;
            }}
            
            .experiencia-item, .educacao-item {{
                margin-bottom: 15px;
                padding-left: 15px;
                border-left: 3px solid #3498db;
                page-break-inside: avoid;
            }}
            
            .experiencia-item h3, .educacao-item h3 {{
                margin: 0 0 3px 0;
                color: #2c3e50;
                font-size: 12pt;
                font-weight: bold;
            }}
            
            .experiencia-item .empresa, .educacao-item .instituicao {{
                font-weight: bold;
                color: #3498db;
                font-size: 11pt;
            }}
            
            .experiencia-item .periodo, .educacao-item .periodo {{
                color: #666;
                font-style: italic;
                font-size: 10pt;
                margin-bottom: 5px;
            }}
            
            .experiencia-item p {{
                margin: 5px 0 0 0;
                font-size: 10pt;
                text-align: justify;
            }}
            
            .habilidades {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 10px;
            }}
            
            .habilidade {{
                background: #3498db;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 9pt;
                display: inline-block;
            }}
            
            .resumo-profissional {{
                text-align: justify;
                font-size: 10pt;
                line-height: 1.4;
                margin-bottom: 15px;
            }}
            
            .idiomas ul, .certificacoes ul {{
                margin: 0;
                padding-left: 20px;
            }}
            
            .idiomas li, .certificacoes li {{
                margin-bottom: 5px;
                font-size: 10pt;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{dados.get('nome_completo', 'Nome Completo')}</h1>
            <div class="contato">
                <div>
                    📧 {dados.get('email', 'email@exemplo.com')} | 
                    📱 {dados.get('telefone', '(00) 00000-0000')}
                </div>
                <div>
                    📍 {dados.get('cidade', 'Cidade')}, {dados.get('estado', 'Estado')}
                    {f" | 🔗 {dados.get('linkedin', '')}" if dados.get('linkedin') else ""}
                </div>
            </div>
        </div>
        
        {f'''
        <div class="secao">
            <h2>📋 Resumo Profissional</h2>
            <div class="resumo-profissional">{dados.get('resumo_profissional', 'Resumo profissional não informado.')}</div>
        </div>
        ''' if dados.get('resumo_profissional') else ''}
        
        <div class="secao">
            <h2>💼 Experiência Profissional</h2>
            {gerar_experiencias_pdf_html(dados.get('experiencias', []))}
        </div>
        
        <div class="secao">
            <h2>🎓 Formação Acadêmica</h2>
            {gerar_educacao_pdf_html(dados.get('educacao', []))}
        </div>
        
        <div class="secao">
            <h2>🛠️ Habilidades</h2>
            <div class="habilidades">
                {gerar_habilidades_pdf_html(dados.get('habilidades', []))}
            </div>
        </div>
        
        {f'''
        <div class="secao idiomas">
            <h2>🌐 Idiomas</h2>
            {gerar_idiomas_html(dados.get('idiomas', []))}
        </div>
        ''' if dados.get('idiomas') else ''}
        
        {f'''
        <div class="secao certificacoes">
            <h2>🏆 Certificações</h2>
            {gerar_certificacoes_html(dados.get('certificacoes', []))}
        </div>
        ''' if dados.get('certificacoes') else ''}
    </body>
    </html>
    """
    
    return template_pdf

def gerar_experiencias_pdf_html(experiencias):
    """Gera HTML otimizado para PDF das experiências profissionais"""
    if not experiencias:
        return "<p>Nenhuma experiência profissional informada.</p>"
    
    html = ""
    for exp in experiencias:
        html += f"""
        <div class="experiencia-item">
            <h3>{exp.get('cargo', 'Cargo')}</h3>
            <div class="empresa">{exp.get('empresa', 'Empresa')}</div>
            <div class="periodo">{exp.get('periodo', 'Período')}</div>
            <p>{exp.get('descricao', 'Descrição das atividades.')}</p>
        </div>
        """
    return html

def gerar_educacao_pdf_html(educacao):
    """Gera HTML otimizado para PDF da formação acadêmica"""
    if not educacao:
        return "<p>Nenhuma formação acadêmica informada.</p>"
    
    html = ""
    for edu in educacao:
        html += f"""
        <div class="educacao-item">
            <h3>{edu.get('curso', 'Curso')}</h3>
            <div class="instituicao">{edu.get('instituicao', 'Instituição')}</div>
            <div class="periodo">{edu.get('periodo', 'Período')}</div>
        </div>
        """
    return html

def gerar_habilidades_pdf_html(habilidades):
    """Gera HTML otimizado para PDF das habilidades"""
    if not habilidades:
        return "<span class='habilidade'>Nenhuma habilidade informada</span>"
    
    html = ""
    for habilidade in habilidades:
        html += f"<span class='habilidade'>{habilidade}</span>"
    return html

@app.route('/api/baixar-curriculo', methods=['POST'])
def api_baixar_curriculo():
    """API para download do currículo em PDF"""
    try:
        logger.info("Iniciando geração de currículo PDF")
        dados_form = request.get_json()
        
        if not dados_form:
            logger.error("Dados do formulário não recebidos")
            return jsonify({'success': False, 'error': 'Dados não recebidos'}), 400
        
        # Gera HTML otimizado para PDF
        html_content = gerar_curriculo_pdf_html(dados_form)
        logger.info("HTML do currículo gerado com sucesso")
        
        # Cria arquivo temporário para o PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            try:
                # Gera PDF usando WeasyPrint
                HTML(string=html_content).write_pdf(temp_file.name)
                logger.info(f"PDF gerado com sucesso: {temp_file.name}")
                
                # Nome do arquivo
                nome_arquivo = f"curriculo_{sanitizar_nome(dados_form.get('nome_completo', 'curriculo'))}.pdf"
                
                # Função para limpar o arquivo temporário após o envio
                def remove_file(response):
                    try:
                        os.unlink(temp_file.name)
                        logger.info(f"Arquivo temporário removido: {temp_file.name}")
                    except Exception as e:
                        logger.error(f"Erro ao remover arquivo temporário: {e}")
                    return response
                
                # Criar resposta com arquivo
                response = send_file(
                    temp_file.name,
                    as_attachment=True,
                    download_name=nome_arquivo,
                    mimetype='application/pdf'
                )
                
                # Headers adicionais para garantir o download
                response.headers['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
                
                # Registrar callback para limpar arquivo
                response.call_on_close(lambda: remove_file(response))
                
                logger.info(f"Enviando PDF: {nome_arquivo}")
                return response
                
            except Exception as pdf_error:
                logger.error(f"Erro ao gerar PDF: {pdf_error}")
                # Limpar arquivo temporário em caso de erro
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                raise pdf_error
        
    except Exception as e:
        logger.error(f"Erro geral ao baixar currículo: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao gerar currículo: {str(e)}'
        }), 500

def gerar_carta_pdf_html(carta_texto, dados_carta):
    """Gera HTML otimizado para PDF da carta de demissão"""
    
    template_pdf = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Carta de Demissão - {dados_carta.get('nome', 'Nome')}</title>
        <style>
            @page {{
                size: A4;
                margin: 3cm 2.5cm;
            }}
            
            body {{
                font-family: 'Times New Roman', serif;
                line-height: 1.8;
                color: #000;
                font-size: 12pt;
                margin: 0;
                padding: 0;
                text-align: justify;
            }}
            
            .carta-container {{
                width: 100%;
                max-width: 100%;
                margin: 0 auto;
            }}
            
            .carta-header {{
                text-align: right;
                margin-bottom: 40px;
                font-size: 12pt;
            }}
            
            .carta-destinatario {{
                margin-bottom: 30px;
                font-size: 12pt;
            }}
            
            .carta-corpo {{
                margin-bottom: 40px;
                text-align: justify;
                line-height: 1.8;
                font-size: 12pt;
            }}
            
            .carta-corpo p {{
                margin-bottom: 20px;
                text-indent: 2cm;
            }}
            
            .carta-assinatura {{
                margin-top: 60px;
                text-align: center;
                font-size: 12pt;
            }}
            
            .linha-assinatura {{
                border-top: 1px solid #000;
                width: 300px;
                margin: 0 auto 10px auto;
            }}
            
            .nome-assinatura {{
                font-weight: bold;
            }}
            
            h1, h2, h3 {{
                font-weight: bold;
                margin: 0;
            }}
            
            .destaque {{
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="carta-container">
            {carta_texto}
        </div>
    </body>
    </html>
    """
    
    return template_pdf

def formatar_carta_para_pdf(carta_texto, dados_carta):
    """Formata o texto da carta para PDF com estrutura adequada"""
    
    # Quebra o texto em parágrafos
    paragrafos = carta_texto.split('\n\n')
    
    # Identifica componentes da carta
    local_data = ""
    destinatario = ""
    corpo = []
    assinatura = ""
    
    for i, paragrafo in enumerate(paragrafos):
        paragrafo = paragrafo.strip()
        if not paragrafo:
            continue
            
        # Primeiro parágrafo geralmente é local e data
        if i == 0 and (',' in paragrafo and any(mes in paragrafo.lower() for mes in ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'])):
            local_data = paragrafo
        # Parágrafo com "Ao" ou empresa geralmente é destinatário
        elif paragrafo.startswith(('Ao', 'À', 'Para')) or dados_carta.get('empresa', '') in paragrafo:
            destinatario = paragrafo
        # Último parágrafo com nome geralmente é assinatura
        elif i == len(paragrafos) - 1 and dados_carta.get('nome', '') in paragrafo:
            assinatura = paragrafo
        # Resto é corpo da carta
        else:
            corpo.append(paragrafo)
    
    # Monta HTML estruturado
    html_formatado = ""
    
    if local_data:
        html_formatado += f'<div class="carta-header">{local_data}</div>'
    
    if destinatario:
        html_formatado += f'<div class="carta-destinatario">{destinatario}</div>'
    
    if corpo:
        html_formatado += '<div class="carta-corpo">'
        for paragrafo in corpo:
            html_formatado += f'<p>{paragrafo}</p>'
        html_formatado += '</div>'
    
    # Assinatura formatada
    html_formatado += '''
    <div class="carta-assinatura">
        <div style="margin-bottom: 60px;">Atenciosamente,</div>
        <div class="linha-assinatura"></div>
        <div class="nome-assinatura">''' + dados_carta.get('nome', 'Nome') + '''</div>
    </div>
    '''
    
    return html_formatado

@app.route('/api/baixar-carta', methods=['POST'])
def api_baixar_carta():
    """API para download da carta de demissão em PDF"""
    try:
        logger.info("Iniciando geração de carta PDF")
        dados_form = request.get_json()
        
        if not dados_form:
            logger.error("Dados do formulário não recebidos")
            return jsonify({'success': False, 'error': 'Dados não recebidos'}), 400
        
        # Gera a carta primeiro
        categoria = dados_form['categoria']
        modelo = dados_form['modelo']
        dados_carta = dados_form['dados']
        
        carta_texto = gerar_carta(categoria, modelo, dados_carta)
        logger.info("Carta gerada com sucesso")
        
        # Formata para PDF
        carta_formatada = formatar_carta_para_pdf(carta_texto, dados_carta)
        
        # Gera HTML otimizado para PDF
        html_content = gerar_carta_pdf_html(carta_formatada, dados_carta)
        logger.info("HTML da carta gerado com sucesso")
        
        # Cria arquivo temporário para o PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            try:
                # Gera PDF usando WeasyPrint
                HTML(string=html_content).write_pdf(temp_file.name)
                logger.info(f"PDF da carta gerado com sucesso: {temp_file.name}")
                
                # Nome do arquivo
                nome_arquivo = f"carta_demissao_{sanitizar_nome(dados_carta.get('nome', 'carta'))}.pdf"
                
                # Função para limpar o arquivo temporário após o envio
                def remove_file(response):
                    try:
                        os.unlink(temp_file.name)
                        logger.info(f"Arquivo temporário removido: {temp_file.name}")
                    except Exception as e:
                        logger.error(f"Erro ao remover arquivo temporário: {e}")
                    return response
                
                # Criar resposta com arquivo
                response = send_file(
                    temp_file.name,
                    as_attachment=True,
                    download_name=nome_arquivo,
                    mimetype='application/pdf'
                )
                
                # Headers adicionais para garantir o download
                response.headers['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
                
                # Registrar callback para limpar arquivo
                response.call_on_close(lambda: remove_file(response))
                
                logger.info(f"Enviando PDF da carta: {nome_arquivo}")
                return response
                
            except Exception as pdf_error:
                logger.error(f"Erro ao gerar PDF da carta: {pdf_error}")
                # Limpar arquivo temporário em caso de erro
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                raise pdf_error
        
    except Exception as e:
        logger.error(f"Erro geral ao baixar carta: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao gerar carta: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)