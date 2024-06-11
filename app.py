from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Inicialização da aplicação Flask
app = Flask(__name__)

# Caminho absoluto para o banco de dados na pasta "3º versão"
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'delivery.db')

# Configurações do banco de dados SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Chave secreta para proteger as sessões
app.secret_key = 'supersecretkey'

# Inicialização do SQLAlchemy com a aplicação Flask
db = SQLAlchemy(app)

# Definição das tabelas do banco de dados usando SQLAlchemy ORM

# Tabela 'Item' para armazenar os itens disponíveis
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    preco = db.Column(db.Float, nullable=False)

# Dentro do modelo Pedido, adicione o campo para armazenar o troco
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    contato = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pendente')
    forma_pagamento = db.Column(db.String(50), nullable=False)  # Novo campo para a forma de pagamento
    pagamento_em_dinheiro = db.Column(db.Float)  # Campo para o valor do pagamento em dinheiro
    troco = db.Column(db.Float)  # Campo para armazenar o troco
    items = db.relationship('PedidoItem', backref='pedido', lazy=True)

# Tabela 'PedidoItem' para armazenar os itens associados a cada pedido
class PedidoItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    item = db.relationship('Item')

# Tabela 'Funcionario' para armazenar os funcionários
class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Rota para a página inicial
@app.route('/')
def index():
    # Recupera todos os itens disponíveis do banco de dados
    items = Item.query.all()
    return render_template('index.html', items=items)

@app.route('/fazer_pedido', methods=['POST'])
def fazer_pedido():
    cliente = request.form['cliente']
    contato = request.form['contato']
    endereco = request.form['endereco']
    forma_pagamento = request.form['forma_pagamento']
    pagamento_em_dinheiro_str = request.form.get('pagamento_em_dinheiro', None)  # Obtém o valor do pagamento em dinheiro como string
    pagamento_em_dinheiro = None
    troco = None

    # Verifica se a forma de pagamento é válida
    formas_pagamento_permitidas = ['pix', 'dinheiro', 'cartao_credito', 'cartao_debito']
    if forma_pagamento not in formas_pagamento_permitidas:
        flash('Forma de pagamento inválida.')
        return redirect(url_for('index'))

    # Verifica se o pagamento é em dinheiro e calcula o troco
    if forma_pagamento == 'dinheiro' and pagamento_em_dinheiro_str:
        try:
            pagamento_em_dinheiro = float(pagamento_em_dinheiro_str)
        except ValueError:
            flash('Valor inválido para pagamento em dinheiro.')
            return redirect(url_for('index'))

        total_pedido = 0
        # Calcula o total do pedido
        for item in Item.query.all():
            quantidade = int(request.form.get(f'quantidade_{item.id}', 0))
            if quantidade > 0:
                total_pedido += quantidade * item.preco

        # Verifica se o valor do pagamento em dinheiro é válido
        if pagamento_em_dinheiro < total_pedido:
            flash('O valor do pagamento em dinheiro é menor que o total do pedido.')
            return redirect(url_for('index'))

        # Calcula o troco apenas se o pagamento em dinheiro for maior ou igual ao total do pedido
        troco = pagamento_em_dinheiro - total_pedido

    # Cria um novo pedido com os detalhes fornecidos
    pedido = Pedido(cliente=cliente, contato=contato, endereco=endereco, forma_pagamento=forma_pagamento, pagamento_em_dinheiro=pagamento_em_dinheiro, troco=troco)
    db.session.add(pedido)

    # Adiciona os itens selecionados ao pedido
    for item in Item.query.all():
        quantidade = int(request.form.get(f'quantidade_{item.id}', 0))
        if quantidade > 0:
            pedido_item = PedidoItem(pedido_id=pedido.id, item_id=item.id, quantidade=quantidade)
            db.session.add(pedido_item)

    # Commit das mudanças no banco de dados
    db.session.commit()
    flash('Pedido realizado com sucesso!')
    return redirect(url_for('confirmacao_pedido', pedido_id=pedido.id))


# Rota para exibir a confirmação de um pedido
@app.route('/confirmacao_pedido/<int:pedido_id>')
def confirmacao_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    total = sum(item.quantidade * item.item.preco for item in pedido.items)
    return render_template('confirmacao.html', pedido=pedido, total=total)

# Rota para exibir todos os pedidos
@app.route('/pedidos')
def pedidos():
    pedidos = Pedido.query.all()
    for pedido in pedidos:
        pedido.total = sum(item.quantidade * item.item.preco for item in pedido.items)
    return render_template('pedidos.html', pedidos=pedidos)

# Rota para atualizar o status de um pedido
@app.route('/atualizar_pedido/<int:pedido_id>', methods=['POST'])
def atualizar_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status = request.form['status']
    db.session.commit()
    return redirect(url_for('pedidos'))

# Rota para a página de login do funcionário
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        funcionario = Funcionario.query.filter_by(username=username).first()
        if funcionario and check_password_hash(funcionario.password, password):
            session['user_id'] = funcionario.id
            return redirect(url_for('pedidos_funcionario'))
        else:
            flash('Login ou senha incorretos.')
    return render_template('login.html')

# Rota para a página de registro de funcionários
@app.route('/registro_funcionario', methods=['GET', 'POST'])
def registro_funcionario():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Verifique se o usuário já existe
        if Funcionario.query.filter_by(username=username).first():
            flash('Nome de usuário já existe. Escolha outro.')
        else:
            # Crie um novo funcionário e adicione ao banco de dados
            novo_funcionario = Funcionario(username=username, password=generate_password_hash(password))
            db.session.add(novo_funcionario)
            db.session.commit()
            flash('Novo funcionário cadastrado com sucesso!')
            return redirect(url_for('login'))
    return render_template('registro_funcionario.html')


# Rota para logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Rota para exibir todos os pedidos para funcionários
@app.route('/funcionario/pedidos')
def pedidos_funcionario():
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar esta página.')
        return redirect(url_for('login'))
    pedidos = Pedido.query.all()
    for pedido in pedidos:
        pedido.total = sum(item.quantidade * item.item.preco for item in pedido.items)
    return render_template('pedidos_funcionario.html', pedidos=pedidos)

# Rota para atualizar o status de um pedido (para funcionários)
@app.route('/funcionario/atualizar_pedido/<int:pedido_id>', methods=['POST'])
def atualizar_pedido_funcionario(pedido_id):
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar esta página.')
        return redirect(url_for('login'))
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status = request.form['status']
    db.session.commit()
    return redirect(url_for('pedidos_funcionario'))

# Rota para remover um pedido (apenas para funcionários)
@app.route('/funcionario/remover_pedido/<int:pedido_id>', methods=['POST'])
def remover_pedido_funcionario(pedido_id):
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar esta página.')
        return redirect(url_for('login'))
    pedido = Pedido.query.get_or_404(pedido_id)
    for item in pedido.items:
        db.session.delete(item)
    db.session.delete(pedido)
    db.session.commit()
    flash('Pedido removido com sucesso!')
    return redirect(url_for('pedidos_funcionario'))

# Executa a aplicação Flask
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
