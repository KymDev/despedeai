from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, flash
import os
from datetime import datetime
from io import BytesIO
from weasyprint import HTML
import re
import unicodedata
from flask import send_from_directory
import threading
import time

# Importa os novos módulos
from calculadora_trabalhista import CalculadoraTrabalhista
from gerador_documentos import GeradorDocumentos
from sistema_pix import SistemaPIX, WebhookPIX
from sistema_entrega import SistemaEntrega

app = Flask(__name__)
app.secret_key = 'despede_ai_secret_key_2025'  # Para flash messages

# Inicializa os sistemas
calculadora = CalculadoraTrabalhista()
gerador_docs = GeradorDocumentos()
sistema_pix = SistemaPIX()
sistema_entrega = SistemaEntrega()
webhook_pix = WebhookPIX(sistema_pix)

# Caminho para os modelos
MODELOS_PATH = os.path.join(os.getcwd(), "modelos")

# Lista de categorias e suas variações
def listar_modelos():
    categorias = {}
    for categoria in os.listdir(MODELOS_PATH):
        cat_path = os.path.join(MODELOS_PATH, categoria)
        if os.path.isdir(cat_path):
            categorias[categoria] = [
                f for f in os.listdir(cat_path) if f.endswith(".txt")
            ]
    return categorias

# Função para sanitizar nomes de arquivo
def sanitizar_nome(nome):
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    nome = re.sub(r'[^\w\s-]', '', nome).strip().lower()
    nome = re.sub(r'[-\s]+', '_', nome)
    return nome

# Carrega conteúdo do modelo e substitui placeholders
def gerar_carta(categoria, modelo, dados):
    modelo_path = os.path.join(MODELOS_PATH, categoria, modelo)
    if not os.path.exists(modelo_path):
        return "Modelo não encontrado."

    with open(modelo_path, encoding='utf-8') as f:
        template = f.read()

    # Formatar data de entrega: se fornecida, usar ela, senão data atual
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

@app.route('/', methods=['GET', 'POST'])
def index():
    categorias = listar_modelos()

    if request.method == 'POST':
        nome = request.form['nome']
        cargo = request.form['cargo']
        empresa = request.form['empresa']
        cidade = request.form['cidade']
        categoria = request.form['categoria']
        modelo = request.form['modelo']
        motivo = request.form.get('motivo', '')
        data = request.form.get('data', '')  # data de entrega

        dados = {
            "nome": nome,
            "cargo": cargo,
            "empresa": empresa,
            "cidade": cidade,
            "motivo": motivo,
            "data": data,
        }

        carta = gerar_carta(categoria, modelo, dados)

        return render_template("resultado.html", carta=carta, nome=nome)

    return render_template("index.html", categorias=categorias)

@app.route('/calculadora')
def calculadora_trabalhista():
    """Página da calculadora trabalhista"""
    return render_template("calculadora.html")

@app.route('/calcular-rescisao', methods=['POST'])
def calcular_rescisao():
    """Processa cálculo da rescisão trabalhista"""
    try:
        # Coleta dados do formulário
        dados = {
            'salario': float(request.form['salario']),
            'data_admissao': datetime.strptime(request.form['data_admissao'], '%Y-%m-%d'),
            'data_demissao': datetime.strptime(request.form['data_demissao'], '%Y-%m-%d'),
            'tipo_demissao': request.form['tipo_demissao'],
            'saldo_fgts': float(request.form.get('saldo_fgts', 0)),
            'horas_extras_mes': float(request.form.get('horas_extras_mes', 0)),
            'adicional_noturno': float(request.form.get('adicional_noturno', 0)),
            'adicional_periculosidade': float(request.form.get('adicional_periculosidade', 0)),
            'dependentes_ir': int(request.form.get('dependentes_ir', 0)),
            'aviso_trabalhado': request.form.get('aviso_trabalhado') == 'on'
        }
        
        # Dados do usuário para personalização
        dados_usuario = {
            'nome': request.form.get('nome', ''),
            'cargo': request.form.get('cargo', ''),
            'empresa': request.form.get('empresa', ''),
            'cidade': request.form.get('cidade', ''),
            'salario': dados['salario'],
            'data_admissao': dados['data_admissao'].strftime('%d/%m/%Y'),
            'data_demissao': dados['data_demissao'].strftime('%d/%m/%Y'),
            'tipo_demissao': dados['tipo_demissao']
        }
        
        # Calcula rescisão
        resultado = calculadora.calcular_rescisao_completa(dados)
        
        return render_template("resultado_calculo.html", 
                             resultado=resultado, 
                             dados_usuario=dados_usuario)
        
    except Exception as e:
        flash(f'Erro no cálculo: {str(e)}', 'error')
        return redirect(url_for('calculadora_trabalhista'))

@app.route('/comprar-kit', methods=['POST'])
def comprar_kit():
    """Inicia processo de compra do Kit Premium"""
    try:
        # Coleta dados do cálculo e usuário
        dados_calculo = request.form.get('dados_calculo')
        dados_usuario = request.form.get('dados_usuario')
        email = request.form.get('email')
        
        if not email:
            flash('E-mail é obrigatório para compra', 'error')
            return redirect(url_for('calculadora_trabalhista'))
        
        # Valor do kit (promoção)
        valor_kit = 19.99
        
        # Cria transação PIX
        import json
        dados_usuario_dict = json.loads(dados_usuario) if dados_usuario else {}
        
        transacao = sistema_pix.criar_transacao(
            email=email,
            valor=valor_kit,
            dados_usuario=dados_usuario_dict
        )
        
        return render_template("pagamento_pix.html", 
                             transacao=transacao,
                             dados_usuario=dados_usuario_dict,
                             dados_calculo=dados_calculo)
        
    except Exception as e:
        flash(f'Erro ao processar compra: {str(e)}', 'error')
        return redirect(url_for('calculadora_trabalhista'))

@app.route('/verificar-pagamento/<txid>')
def verificar_pagamento(txid):
    """Verifica status do pagamento PIX"""
    try:
        status = sistema_pix.verificar_pagamento(txid)
        
        if status['status'] == 'pago':
            # Inicia processo de geração e entrega
            threading.Thread(
                target=processar_entrega_kit,
                args=(status['transacao_id'],)
            ).start()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'status': 'erro', 'message': str(e)})

def processar_entrega_kit(transacao_id):
    """Processa geração e entrega do kit (executa em background)"""
    try:
        # Obtém dados da transação
        transacao = sistema_pix.obter_transacao(transacao_id)
        
        if not transacao:
            return
        
        # Simula dados de cálculo (em produção, seria salvo na transação)
        dados_calculo_exemplo = {
            'verbas': {
                'saldo_salario': {'valor': 1500.00, 'dias_trabalhados': 15},
                'ferias_proporcionais': {'total': 2000.00, 'valor_ferias': 1500.00, 'um_terco': 500.00, 'meses_trabalhados': 6},
                'decimo_terceiro': {'valor': 1000.00, 'meses_trabalhados': 6},
                'aviso_previo': {'valor': 1500.00, 'dias': 30, 'tipo': 'Indenizado'},
                'multa_fgts': {'valor': 800.00, 'percentual': 40, 'aplicavel': True}
            },
            'resumo': {
                'total_bruto': 6800.00,
                'desconto_inss': 400.00,
                'desconto_irrf': 200.00,
                'total_descontos': 600.00,
                'total_liquido': 6200.00
            }
        }
        
        # Gera kit completo
        kit_zip = gerador_docs.gerar_kit_completo(dados_calculo_exemplo, transacao['dados_usuario'])
        
        # Processa entrega
        resultado_entrega = sistema_entrega.processar_entrega_completa(
            transacao_id=transacao_id,
            arquivo_kit=kit_zip,
            dados_usuario=transacao['dados_usuario'],
            email_destino=transacao['email']
        )
        
        if resultado_entrega['success']:
            # Atualiza status da transação
            sistema_pix.atualizar_status_transacao(transacao_id, 'entregue')
        
    except Exception as e:
        print(f"Erro na entrega do kit: {e}")

@app.route('/download/<download_token>')
def download_kit(download_token):
    """Processa download do kit"""
    try:
        resultado = sistema_entrega.processar_download(download_token)
        
        if 'error' in resultado:
            flash(resultado['error'], 'error')
            return render_template("download_erro.html", erro=resultado['error'])
        
        # Retorna arquivo para download
        return send_file(
            resultado['arquivo_path'],
            as_attachment=True,
            download_name=os.path.basename(resultado['arquivo_path'])
        )
        
    except Exception as e:
        flash(f'Erro no download: {str(e)}', 'error')
        return render_template("download_erro.html", erro=str(e))

@app.route('/webhook/pix', methods=['POST'])
def webhook_pix_endpoint():
    """Endpoint para webhook do PIX (simulação)"""
    try:
        dados = request.get_json()
        resultado = webhook_pix.processar_webhook(dados)
        
        if resultado:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error'}), 400
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Rota para simular confirmação de pagamento (apenas para testes)
@app.route('/simular-pagamento/<txid>')
def simular_pagamento(txid):
    """Simula confirmação de pagamento para testes"""
    try:
        if sistema_pix.confirmar_pagamento(txid):
            flash('Pagamento confirmado com sucesso!', 'success')
        else:
            flash('Erro ao confirmar pagamento', 'error')
            
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/politicas')
def politicas():
    """Página de políticas comerciais e informações legais"""
    return render_template("politicas.html")

@app.route('/ads.txt')
def serve_ads_txt():
    return send_from_directory(app.root_path, 'ads.txt')

# Rota para retornar modelos disponíveis para uma categoria (JSON)
@app.route('/modelos')
def modelos():
    categoria = request.args.get('categoria')
    categorias = listar_modelos()
    modelos = categorias.get(categoria, [])
    return jsonify(modelos)

@app.route('/gerar-pdf', methods=['POST'])
def gerar_pdf():
    conteudo = request.form['carta']
    nome = request.form['nome']
    nome_sanitizado = sanitizar_nome(nome)

    html = render_template("pdf_template.html", conteudo=conteudo.replace('\n', '<br>'))

    pdf_io = BytesIO()
    HTML(string=html).write_pdf(pdf_io)
    pdf_io.seek(0)

    return send_file(
        pdf_io,
        as_attachment=True,
        download_name=f"carta_demissao_{nome_sanitizado}.pdf",
        mimetype="application/pdf"
    )

# Task para limpeza automática (executar periodicamente)
def limpeza_automatica():
    """Limpa transações e arquivos expirados"""
    while True:
        try:
            # Limpa a cada 6 horas
            time.sleep(6 * 60 * 60)
            
            # Limpa transações expiradas
            sistema_pix.limpar_transacoes_expiradas()
            
            # Limpa arquivos expirados
            sistema_entrega.limpar_arquivos_expirados()
            
        except Exception as e:
            print(f"Erro na limpeza automática: {e}")

# Inicia thread de limpeza
threading.Thread(target=limpeza_automatica, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)

