-- Criar o banco de dados
CREATE DATABASE finance;

-- Conectar ao banco de dados
\c finance;

-- Criar tabela de Movimentacoes
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
);

-- Criar tabela de Limites
CREATE TABLE IF NOT EXISTS Limites (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    pessoa VARCHAR(50) NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    UNIQUE (data, pessoa)
);

-- Inserir alguns dados de exemplo
INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento) 
VALUES 
    ('2024-01-14', 'Salário', 5000.00, 'Salário', 'Yuri', NULL),
    ('2024-01-26', 'Salário', 5000.00, 'Salário', 'Marcos', NULL);

INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas) 
VALUES 
    ('2024-01-05', 'Aluguel', -1500.00, 'Conta', 'Yuri', 'Débito', NULL, 0),
    ('2024-01-10', 'Internet', -150.00, 'Conta', 'Marcos', 'Débito', NULL, 0),
    ('2024-01-15', 'Compra Supermercado', -500.00, 'Compra', 'Yuri', 'Crédito', 1, 1),
    ('2024-01-20', 'Academia', -100.00, 'Conta', 'Marcos', 'Débito', NULL, 0);

INSERT INTO Movimentacoes (data, descricao, valor, tipo) 
VALUES 
    ('2024-01-01', 'Depósito Inicial', 1000.00, 'Poupança');

INSERT INTO Limites (data, pessoa, valor) 
VALUES 
    ('2024-01-01', 'Yuri', 2000.00),
    ('2024-01-01', 'Marcos', 2000.00); 