import sys
import os

# Adiciona o diretório 'meu_projeto' ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from meu_app.app import app, db, Item

# Cria as tabelas no banco de dados e popula com dados iniciais
with app.app_context():
    db.create_all()

    # Lista de itens de açaí com seus nomes e preços
    items = [
        {"nome": "Açaí Popular 1L", "preco": 12.00},
        {"nome": "Açaí Médio 1L", "preco": 20.00},
        {"nome": "Açaí Grosso 1L", "preco": 30.00},
    ]

    # Adiciona os itens ao banco de dados se não existirem
    for item_data in items:
        # Verifica se o item já existe no banco de dados
        existing_item = Item.query.filter_by(nome=item_data['nome']).first()
        if not existing_item:
            item = Item(nome=item_data['nome'], preco=item_data['preco'])
            db.session.add(item)

    db.session.commit()
    print("Banco de dados populado com sucesso!")
