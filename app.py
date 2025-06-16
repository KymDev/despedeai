from flask import Flask, render_template, request, send_file, jsonify
import os
from datetime import datetime
from io import BytesIO
from weasyprint import HTML
import re
import unicodedata
from flask import send_from_directory


app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)
