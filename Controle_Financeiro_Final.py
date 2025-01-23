import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                           QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                           QMessageBox, QDialog, QTableWidget, QTableWidgetItem,
                           QScrollArea, QFrame, QTabWidget, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from datetime import datetime
from dateutil.relativedelta import relativedelta
import psycopg2

# Configurações do banco PostgreSQL
DB_NAME = "finance"
DB_USER = "postgres"
DB_PASSWORD = "senha"
DB_HOST = "localhost"
DB_PORT = "5432"

def connect_to_database():
    """
    Estabelece conexão com o banco de dados PostgreSQL.
    """
    try:
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return connection
    except Exception as e:
        print("Erro ao conectar ao banco de dados:", e)
        raise

def save_compra(descricao, valor_parcela, pessoa, pagamento, total_parcelas):
    """
    Salva uma compra no banco de dados.
    """
    try:
        data = datetime.now()
        if pagamento == "Crédito":
            if pessoa == "Yuri":
                data = data.replace(day=14) if data.day < 14 else data.replace(day=14) + relativedelta(months=1)
            elif pessoa == "Marcos":
                data = data.replace(day=26) if data.day < 26 else data.replace(day=26) + relativedelta(months=1)

        conn = connect_to_database()
        cursor = conn.cursor()

        for parcela in range(1, total_parcelas + 1):
            valor = -abs(valor_parcela)
            cursor.execute("""
                INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas)
                VALUES (%s, %s, %s, 'Compra', %s, %s, %s, %s)
            """, (data, descricao, valor, pessoa, pagamento, parcela, total_parcelas))

            data += relativedelta(months=1)
            replicate_recurring_entries(data.month, data.year)

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao registrar a compra: {str(e)}")
        return False

def save_conta(descricao, pessoa, dia_vencimento, valor, frequencia, pagamento):
    """
    Salva uma conta no banco de dados.
    """
    try:
        hoje = datetime.now()
        vencimento = hoje.replace(day=dia_vencimento)
        if hoje.day > dia_vencimento:
            vencimento += relativedelta(months=1)

        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, total_parcelas)
            VALUES (%s, %s, %s, 'Conta', %s, %s, %s)
        """, (vencimento, descricao, -abs(valor), pessoa, pagamento, frequencia))

        if frequencia == 0:
            cursor.execute("""
                SELECT DISTINCT EXTRACT(MONTH FROM data) AS mes, EXTRACT(YEAR FROM data) AS ano
                FROM Movimentacoes
                ORDER BY ano, mes
            """)
            meses_anos = cursor.fetchall()

            for mes, ano in meses_anos:
                data_conta = datetime(int(ano), int(mes), dia_vencimento)
                cursor.execute("""
                    SELECT 1 FROM Movimentacoes
                    WHERE data = %s AND descricao = %s AND pessoa = %s
                """, (data_conta, descricao, pessoa))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, total_parcelas)
                        VALUES (%s, %s, %s, 'Conta', %s, %s, 0)
                    """, (data_conta, descricao, -abs(valor), pessoa, pagamento))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao registrar a conta: {str(e)}")
        return False

def save_salario(valor, dia, pessoa):
    """
    Salva um salário no banco de dados.
    """
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT EXTRACT(MONTH FROM data) AS mes, EXTRACT(YEAR FROM data) AS ano
            FROM Movimentacoes
            ORDER BY ano, mes
        """)
        meses_existentes = cursor.fetchall()

        for mes, ano in meses_existentes:
            data_salario = datetime(int(ano), int(mes), dia)
            cursor.execute("""
                SELECT 1 FROM Movimentacoes
                WHERE data = %s AND descricao = 'Salário' AND pessoa = %s
            """, (data_salario, pessoa))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa)
                    VALUES (%s, 'Salário', %s, 'Recebimento', %s)
                """, (data_salario, valor, pessoa))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao registrar o salário: {str(e)}")
        return False

def save_recebimento(valor, dia, descricao, frequencia, pessoa):
    """
    Salva um recebimento no banco de dados.
    """
    try:
        data_inicial = datetime.now().replace(day=dia)
        
        conn = connect_to_database()
        cursor = conn.cursor()

        for i in range(0, frequencia):
            data = data_inicial + relativedelta(months=i)
            cursor.execute("""
                INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa)
                VALUES (%s, %s, %s, 'Recebimento', %s)
            """, (data, descricao, valor, pessoa))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao registrar o recebimento: {str(e)}")
        return False

def save_poupanca(valor, descricao):
    """
    Salva um registro de poupança no banco de dados.
    """
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo)
            VALUES (CURRENT_DATE, %s, %s, 'Poupança')
        """, (descricao, valor))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao salvar a poupança: {str(e)}")
        return False

def save_retirada(valor, descricao):
    """
    Registra uma retirada da poupança no banco de dados.
    """
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo)
            VALUES (CURRENT_DATE, %s, %s, 'Retirada')
        """, (descricao, valor))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao salvar a retirada: {str(e)}")
        return False

def save_limite(pessoa, mes_ano, valor):
    """
    Define o limite de gastos para uma pessoa em um determinado mês.
    """
    try:
        mes, ano = map(int, mes_ano.split("/"))
        data_limite = datetime(ano, mes, 1)

        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Limites (data, pessoa, valor)
            VALUES (%s, %s, %s)
            ON CONFLICT (data, pessoa) DO UPDATE SET valor = EXCLUDED.valor
        """, (data_limite, pessoa, valor))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao definir o limite: {str(e)}")
        return False

def replicate_recurring_entries(month, year):
    """
    Replica lançamentos recorrentes para um determinado mês.
    """
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        start_date = datetime(year, month, 1)

        # Recupera salários recorrentes
        cursor.execute("""
            SELECT descricao, valor, pessoa, EXTRACT(DAY FROM data) AS dia
            FROM Movimentacoes
            WHERE tipo = 'Recebimento' AND descricao = 'Salário'
            GROUP BY descricao, valor, pessoa, dia
        """)
        salarios = cursor.fetchall()

        # Recupera contas com frequência zero
        cursor.execute("""
            SELECT descricao, valor, pessoa, pagamento, EXTRACT(DAY FROM data) AS dia_vencimento
            FROM Movimentacoes
            WHERE tipo = 'Conta' AND total_parcelas = 0
            GROUP BY descricao, valor, pessoa, pagamento, dia_vencimento
        """)
        contas = cursor.fetchall()

        for descricao, valor, pessoa, dia in salarios:
            data_salario = start_date.replace(day=int(dia))
            cursor.execute("""
                SELECT 1 FROM Movimentacoes
                WHERE data = %s AND descricao = %s AND pessoa = %s
            """, (data_salario, descricao, pessoa))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa)
                    VALUES (%s, %s, %s, 'Recebimento', %s)
                """, (data_salario, descricao, valor, pessoa))

        for descricao, valor, pessoa, pagamento, dia_vencimento in contas:
            data_conta = start_date.replace(day=int(dia_vencimento))
            cursor.execute("""
                SELECT 1 FROM Movimentacoes
                WHERE data = %s AND descricao = %s AND pessoa = %s
            """, (data_conta, descricao, pessoa))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, total_parcelas)
                    VALUES (%s, %s, %s, 'Conta', %s, %s, 0)
                """, (data_conta, descricao, -abs(valor), pessoa, pagamento))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao replicar lançamentos recorrentes: {str(e)}")

def get_month_data(month, year):
    """
    Retorna os dados de movimentações de um determinado mês.
    """
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas
            FROM Movimentacoes
            WHERE EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s
            ORDER BY data
        """, (month, year))
        
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return data

    except Exception as e:
        print(f"Erro ao recuperar dados do mês: {str(e)}")
        return []

def get_month_totals(data, previous_month_total=0, previous_savings=0):
    """
    Calcula os totais do mês a partir dos dados fornecidos.
    """
    totals = {
        "Poupança": {"Total": previous_savings},
        "Entradas": {"Yuri": 0, "Marcos": 0, "Total": 0},
        "Saídas": {"Yuri": 0, "Marcos": 0, "Total": 0},
        "Crédito": {"Yuri": 0, "Marcos": 0},
        "Total do Mês": 0
    }

    for record in data:
        _, _, valor, tipo, pessoa, pagamento, _, _ = record

        if tipo in ["Recebimento", "Salário"]:
            totals["Entradas"]["Total"] += valor
            if pessoa in ["Yuri", "Marcos"]:
                totals["Entradas"][pessoa] += valor

        elif tipo in ["Conta", "Compra"]:
            totals["Saídas"]["Total"] += valor
            if pessoa in ["Yuri", "Marcos"]:
                totals["Saídas"][pessoa] += valor

        elif tipo == "Poupança":
            totals["Poupança"]["Total"] += valor

        if pagamento == "Crédito" and pessoa in ["Yuri", "Marcos"]:
            totals["Crédito"][pessoa] += valor

    totals["Total do Mês"] = previous_month_total + totals["Entradas"]["Total"] + totals["Saídas"]["Total"]

    return totals

class StyleHelper:
    @staticmethod
    def get_button_style():
        return """
            QPushButton {
                background-color: purple;
                color: black;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E0B0FF;
            }
        """

    @staticmethod
    def get_input_style():
        return """
            QLineEdit {
                padding: 8px;
                border: 1px solid purple;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #E0B0FF;
            }
        """

    @staticmethod
    def get_table_style():
        return """
            QTableWidget {
                border: 2px solid purple;
                gridline-color: purple;
                alternate-background-color: #E6D5F2;  /* Tom mais forte de roxo claro */
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #D8BFD8;  /* Linha mais visível entre as células */
            }
            QHeaderView::section {
                background-color: purple;
                color: white;
                padding: 8px;
                border: 1px solid #E0B0FF;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #D8BFD8;
                color: black;
            }
        """

    @staticmethod
    def get_summary_style():
        return """
            QFrame {
                background-color: white;
                border: 2px solid purple;
                border-radius: 5px;
                margin: 5px;
                padding: 10px;
            }
            QLabel {
                color: black;
                padding: 5px;
                font-size: 12px;
            }
            QLabel[class="title"] {
                font-weight: bold;
                font-size: 14px;
                color: purple;
            }
        """

class RegisterDialog(QDialog):
    def __init__(self, title, fields, save_function, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setup_ui(fields)
        self.save_function = save_function

    def setup_ui(self, fields):
        layout = QVBoxLayout()
        self.fields = {}

        for field_name, placeholder in fields:
            field_layout = QHBoxLayout()
            label = QLabel(field_name)
            label.setFont(QFont("Arial", 12))
            input_field = QLineEdit()
            input_field.setPlaceholderText(placeholder)
            input_field.setStyleSheet(StyleHelper.get_input_style())
            
            field_layout.addWidget(label)
            field_layout.addWidget(input_field)
            layout.addLayout(field_layout)
            
            self.fields[field_name] = input_field

        save_button = QPushButton("Salvar")
        save_button.setStyleSheet(StyleHelper.get_button_style())
        save_button.clicked.connect(self.save)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save(self):
        try:
            field_values = {name: field.text() for name, field in self.fields.items()}
            self.save_function(field_values)
            QMessageBox.information(self, "Sucesso", "Registro salvo com sucesso!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle Financeiro")
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Título
        title = QLabel("Controle Financeiro do Amorrrrr")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Botões
        buttons_data = [
            ("Compra", self.open_register_compra),
            ("Conta", self.open_register_conta),
            ("Salário", self.open_register_salario),
            ("Recebimento", self.open_register_recebimento),
            ("Poupança", self.open_register_poupanca),
            ("Retirada", self.open_register_retirada),
            ("Limite", self.open_register_limite),
            ("Visualizar", self.visualize_data)
        ]

        for text, callback in buttons_data:
            button = QPushButton(text)
            button.setStyleSheet(StyleHelper.get_button_style())
            button.clicked.connect(callback)
            layout.addWidget(button)

    def open_register_compra(self):
        fields = [
            ("Descrição", "Digite a descrição"),
            ("Valor", "Digite o valor"),
            ("Pessoa", "Digite o nome"),
            ("Pagamento", "Forma de pagamento"),
            ("Parcelas", "Número de parcelas")
        ]
        dialog = RegisterDialog("Registrar Compra", fields, self.save_compra)
        dialog.exec()

    def open_register_conta(self):
        fields = [
            ("Descrição", "Digite a descrição"),
            ("Pessoa", "Digite o nome"),
            ("Dia Vencimento", "Dia do vencimento (1-31)"),
            ("Valor", "Digite o valor"),
            ("Frequência", "Frequência em meses (0 para recorrente)"),
            ("Pagamento", "Forma de pagamento")
        ]
        dialog = RegisterDialog("Registrar Conta", fields, self.save_conta)
        dialog.exec()

    def open_register_salario(self):
        fields = [
            ("Valor", "Digite o valor"),
            ("Dia", "Dia do recebimento"),
            ("Pessoa", "Digite o nome")
        ]
        dialog = RegisterDialog("Registrar Salário", fields, self.save_salario)
        dialog.exec()

    def open_register_recebimento(self):
        fields = [
            ("Valor", "Digite o valor"),
            ("Dia", "Dia do recebimento"),
            ("Descrição", "Digite a descrição"),
            ("Frequência", "Número de meses"),
            ("Pessoa", "Digite o nome")
        ]
        dialog = RegisterDialog("Registrar Recebimento", fields, self.save_recebimento)
        dialog.exec()

    def open_register_poupanca(self):
        fields = [
            ("Valor", "Digite o valor"),
            ("Descrição", "Digite a descrição")
        ]
        dialog = RegisterDialog("Registrar Poupança", fields, self.save_poupanca)
        dialog.exec()

    def open_register_retirada(self):
        fields = [
            ("Valor", "Digite o valor"),
            ("Descrição", "Digite a descrição")
        ]
        dialog = RegisterDialog("Registrar Retirada", fields, self.save_retirada)
        dialog.exec()

    def open_register_limite(self):
        fields = [
            ("Pessoa", "Digite o nome"),
            ("Mês/Ano", "MM/AAAA"),
            ("Valor", "Digite o valor do limite")
        ]
        dialog = RegisterDialog("Definir Limite", fields, self.save_limite)
        dialog.exec()

    def save_compra(self, field_values):
        try:
            result = save_compra(
                field_values["Descrição"],
                float(field_values["Valor"]),
                field_values["Pessoa"].capitalize(),
                field_values["Pagamento"].capitalize(),
                int(field_values["Parcelas"]) if field_values["Pagamento"].capitalize() == "Crédito" else 1
            )
            if not result:
                raise Exception("Erro ao salvar compra")
        except Exception as e:
            raise Exception(f"Erro ao registrar a compra: {str(e)}")

    def save_conta(self, field_values):
        try:
            result = save_conta(
                field_values["Descrição"],
                field_values["Pessoa"].capitalize(),
                int(field_values["Dia Vencimento"]),
                float(field_values["Valor"]),
                int(field_values["Frequência"]),
                field_values["Pagamento"].capitalize()
            )
            if not result:
                raise Exception("Erro ao salvar conta")
        except Exception as e:
            raise Exception(f"Erro ao registrar a conta: {str(e)}")

    def save_salario(self, field_values):
        try:
            result = save_salario(
                float(field_values["Valor"]),
                int(field_values["Dia"]),
                field_values["Pessoa"].capitalize()
            )
            if not result:
                raise Exception("Erro ao salvar salário")
        except Exception as e:
            raise Exception(f"Erro ao registrar o salário: {str(e)}")

    def save_recebimento(self, field_values):
        try:
            result = save_recebimento(
                float(field_values["Valor"]),
                int(field_values["Dia"]),
                field_values["Descrição"],
                int(field_values["Frequência"]),
                field_values["Pessoa"].capitalize()
            )
            if not result:
                raise Exception("Erro ao registrar o recebimento")
        except Exception as e:
            raise Exception(f"Erro ao registrar o recebimento: {str(e)}")

    def save_poupanca(self, field_values):
        try:
            result = save_poupanca(
                float(field_values["Valor"]),
                field_values["Descrição"]
            )
            if not result:
                raise Exception("Erro ao registrar a poupança")
        except Exception as e:
            raise Exception(f"Erro ao registrar a poupança: {str(e)}")

    def save_retirada(self, field_values):
        try:
            result = save_retirada(
                float(field_values["Valor"]),
                field_values["Descrição"]
            )
            if not result:
                raise Exception("Erro ao registrar a retirada")
        except Exception as e:
            raise Exception(f"Erro ao registrar a retirada: {str(e)}")

    def save_limite(self, field_values):
        try:
            result = save_limite(
                field_values["Pessoa"].capitalize(),
                field_values["Mês/Ano"],
                float(field_values["Valor"])
            )
            if not result:
                raise Exception("Erro ao definir o limite")
        except Exception as e:
            raise Exception(f"Erro ao definir o limite: {str(e)}")

    def visualize_data(self):
        dialog = VisualizationDialog(self)
        dialog.exec()

class VisualizationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visualizar Dados")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid purple;
            }
            QTabBar::tab {
                background: purple;
                color: white;
                padding: 8px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: #E0B0FF;
                color: black;
            }
        """)
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def load_data(self):
        try:
            conn = connect_to_database()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT EXTRACT(MONTH FROM data), EXTRACT(YEAR FROM data)
                FROM Movimentacoes
                ORDER BY 2, 1
            """)
            months_years = cursor.fetchall()

            previous_month_total = 0
            previous_savings = 0

            for month, year in months_years:
                tab = QWidget()
                tab_layout = QVBoxLayout()
                
                # Resumo financeiro no topo
                totals_widget = QWidget()
                totals_layout = QHBoxLayout()
                
                # Dados do mês
                cursor.execute("""
                    SELECT data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas
                    FROM Movimentacoes
                    WHERE EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s
                    ORDER BY data
                """, (month, year))
                data = cursor.fetchall()
                
                # Cálculo dos totais
                totals = self.calculate_totals(data, previous_month_total, previous_savings)
                
                # Criação dos frames de totais
                frames_data = [
                    ("Poupança", {"Total": totals["Poupança"]["Total"]}),
                    ("Entradas", {
                        "Yuri": totals["Entradas"]["Yuri"],
                        "Marcos": totals["Entradas"]["Marcos"],
                        "Total": totals["Entradas"]["Total"]
                    }),
                    ("Saídas", {
                        "Yuri": totals["Saídas"]["Yuri"],
                        "Marcos": totals["Saídas"]["Marcos"],
                        "Total": totals["Saídas"]["Total"]
                    }),
                    ("Crédito", {
                        "Yuri": totals["Crédito"]["Yuri"],
                        "Marcos": totals["Crédito"]["Marcos"]
                    }),
                    ("Total", {
                        "Mês Anterior": previous_month_total,
                        "Mês Atual": totals["Total do Mês"]
                    })
                ]
                
                for title, values in frames_data:
                    frame = QFrame()
                    frame.setStyleSheet(StyleHelper.get_summary_style())
                    frame_layout = QVBoxLayout()
                    
                    title_label = QLabel(title)
                    title_label.setProperty("class", "title")
                    title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                    frame_layout.addWidget(title_label)
                    
                    for key, value in values.items():
                        if title in ["Saídas", "Crédito"]:
                            # Para saídas e crédito, mostra o valor como negativo
                            color = "red"
                            value_label = QLabel(f"{key}: R$ -{abs(value):,.2f}")
                        else:
                            # Para outros valores, mantém a lógica anterior
                            color = "green" if value > 0 else "red" if value < 0 else "black"
                            value_label = QLabel(f"{key}: R$ {abs(value):,.2f}")
                        value_label.setStyleSheet(f"color: {color}; font-weight: bold;")
                        frame_layout.addWidget(value_label)
                    
                    frame.setLayout(frame_layout)
                    totals_layout.addWidget(frame)
                
                totals_widget.setLayout(totals_layout)
                tab_layout.addWidget(totals_widget)
                
                # Tabela de movimentações
                table = QTableWidget()
                table.setStyleSheet(StyleHelper.get_table_style())
                table.setAlternatingRowColors(True)
                headers = ["Data", "Descrição", "Valor", "Tipo", "Pessoa", "Pagamento", "Parcela", "Total Parcelas"]
                table.setColumnCount(len(headers))
                table.setHorizontalHeaderLabels(headers)
                table.setRowCount(len(data))
                
                for row, record in enumerate(data):
                    # Define a cor de fundo baseada no tipo de movimentação
                    row_color = None
                    if record[3] == "Poupança":
                        row_color = QColor("#E6F3FF")  # Azul claro
                    elif record[3] == "Retirada":
                        row_color = QColor("#FFF3E6")  # Laranja claro
                    
                    for col, value in enumerate(record):
                        if isinstance(value, datetime):
                            value = value.strftime("%d/%m/%Y")
                            item = QTableWidgetItem(value)
                        elif isinstance(value, float):
                            value = f"R$ {value:,.2f}"
                            item = QTableWidgetItem(value)
                            if value.startswith("-"):
                                item.setForeground(QColor("red"))
                            else:
                                item.setForeground(QColor("green"))
                        else:
                            item = QTableWidgetItem(str(value) if value is not None else "")
                        
                        if row_color:
                            item.setBackground(row_color)
                        
                        table.setItem(row, col, item)
                
                # Ajusta o tamanho das colunas e linhas
                table.resizeColumnsToContents()
                table.resizeRowsToContents()
                table.setShowGrid(True)
                
                # Define altura mínima para as linhas
                for i in range(table.rowCount()):
                    table.setRowHeight(i, 30)
                
                tab_layout.addWidget(table)
                
                tab.setLayout(tab_layout)
                self.tab_widget.addTab(tab, f"{int(month):02d}/{int(year)}")
                
                previous_month_total = totals["Total do Mês"]
                previous_savings = totals["Poupança"]["Total"]

            cursor.close()
            conn.close()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados: {str(e)}")

    def calculate_totals(self, data, previous_month_total, previous_savings):
        totals = {
            "Poupança": {"Total": previous_savings},
            "Entradas": {"Yuri": 0, "Marcos": 0, "Total": 0},
            "Saídas": {"Yuri": 0, "Marcos": 0, "Total": 0},
            "Crédito": {"Yuri": 0, "Marcos": 0},
            "Total do Mês": previous_month_total
        }

        for record in data:
            _, _, valor, tipo, pessoa, pagamento, _, _ = record

            if tipo in ["Recebimento", "Salário"]:
                totals["Entradas"]["Total"] += valor
                if pessoa in ["Yuri", "Marcos"]:
                    totals["Entradas"][pessoa] += valor
                totals["Total do Mês"] += valor

            elif tipo in ["Conta", "Compra"]:
                totals["Saídas"]["Total"] += abs(valor)  # Valor absoluto para exibição
                if pessoa in ["Yuri", "Marcos"]:
                    totals["Saídas"][pessoa] += abs(valor)  # Valor absoluto para exibição
                totals["Total do Mês"] += valor  # Mantém o sinal negativo para o total

            elif tipo == "Poupança":
                totals["Poupança"]["Total"] += valor
                totals["Total do Mês"] += valor

            elif tipo == "Retirada":
                totals["Poupança"]["Total"] -= abs(valor)
                totals["Total do Mês"] -= abs(valor)

            if pagamento == "Crédito" and pessoa in ["Yuri", "Marcos"]:
                totals["Crédito"][pessoa] += abs(valor)  # Valor absoluto para crédito

        return totals

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Definindo o estilo global da aplicação
    app.setStyle("Fusion")
    
    # Configurando a paleta de cores
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    app.setPalette(palette)
    
    window = MainWindow()
    window.setMinimumSize(800, 600)
    window.show()
    
    sys.exit(app.exec())

