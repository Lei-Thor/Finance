import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configurações do banco PostgreSQL
DB_NAME = "finance"
DB_USER = "postgres"
DB_PASSWORD = "senha"
DB_HOST = "localhost"
DB_PORT = "5432"

def create_database():
    """Cria o banco de dados se ele não existir"""
    try:
        # Conecta ao PostgreSQL sem especificar um banco de dados
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Verifica se o banco de dados já existe
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE {DB_NAME}')
            print(f"Banco de dados '{DB_NAME}' criado com sucesso!")
        else:
            print(f"Banco de dados '{DB_NAME}' já existe.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao criar banco de dados: {e}")
        raise

def setup_tables():
    """Cria as tabelas e insere dados iniciais"""
    try:
        # Conecta ao banco de dados criado
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Criar tabela de Movimentacoes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Movimentacoes (
                id SERIAL PRIMARY KEY,
                data DATE NOT NULL,
                descricao VARCHAR(255) NOT NULL,
                valor DECIMAL(10,2) NOT NULL,
                tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('Compra', 'Conta', 'Recebimento', 'Salário', 'Poupança', 'Retirada')),
                pessoa VARCHAR(50),
                pagamento VARCHAR(50),
                parcela_atual INTEGER,
                total_parcelas INTEGER
            )
        """)

        # Criar tabela de Limites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Limites (
                id SERIAL PRIMARY KEY,
                data DATE NOT NULL,
                pessoa VARCHAR(50) NOT NULL,
                valor DECIMAL(10,2) NOT NULL,
                UNIQUE (data, pessoa)
            )
        """)

        # Inserir dados de exemplo
        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento) 
            VALUES 
                ('2024-01-14', 'Salário', 5000.00, 'Salário', 'Yuri', NULL),
                ('2024-01-26', 'Salário', 5000.00, 'Salário', 'Marcos', NULL)
            ON CONFLICT DO NOTHING
        """)

        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas) 
            VALUES 
                ('2024-01-05', 'Aluguel', -1500.00, 'Conta', 'Yuri', 'Débito', NULL, 0),
                ('2024-01-10', 'Internet', -150.00, 'Conta', 'Marcos', 'Débito', NULL, 0),
                ('2024-01-15', 'Compra Supermercado', -500.00, 'Compra', 'Yuri', 'Crédito', 1, 1),
                ('2024-01-20', 'Academia', -100.00, 'Conta', 'Marcos', 'Débito', NULL, 0)
            ON CONFLICT DO NOTHING
        """)

        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo) 
            VALUES 
                ('2024-01-01', 'Depósito Inicial', 1000.00, 'Poupança')
            ON CONFLICT DO NOTHING
        """)

        cursor.execute("""
            INSERT INTO Limites (data, pessoa, valor) 
            VALUES 
                ('2024-01-01', 'Yuri', 2000.00),
                ('2024-01-01', 'Marcos', 2000.00)
            ON CONFLICT DO NOTHING
        """)

        conn.commit()
        print("Tabelas criadas e dados iniciais inseridos com sucesso!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao configurar tabelas: {e}")
        raise

if __name__ == "__main__":
    print("Iniciando configuração do banco de dados...")
    create_database()
    setup_tables()
    print("Configuração do banco de dados concluída!") 