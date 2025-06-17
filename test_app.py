from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "<h1>DespedeAI - Aplicação funcionando!</h1><p>Teste básico da aplicação atualizada.</p>"

@app.route('/calculadora')
def calculadora():
    return "<h1>Calculadora Trabalhista</h1><p>Funcionalidade em desenvolvimento.</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)

