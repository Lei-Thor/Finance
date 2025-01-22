import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from dateutil.relativedelta import relativedelta
from itertools import groupby
import os
from PIL import Image, ImageTk
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


# Função para salvar uma compra no banco de dados
def replicate_recurring_entries(month, year):
    """
    Verifica e replica lançamentos recorrentes (salários e contas com frequência zero) para o mês especificado,
    garantindo que contas sejam registradas em meses novos e existentes sem duplicações.
    """
    try:
        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        # Data de início do mês
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

        # Inserir salários no mês especificado
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

        # Inserir contas no mês especificado, garantindo valores negativos e sem duplicação
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

        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao replicar lançamentos recorrentes: {str(e)}")

def save_compra():
    """
    Salva uma compra no banco de dados PostgreSQL com os dados fornecidos pelo usuário,
    permitindo que o usuário forneça o valor das parcelas e a quantidade de parcelas diretamente.
    """
    try:
        # Captura os dados dos campos da interface gráfica
        descricao = entry_descricao.get()
        valor_parcela = abs(float(entry_valor.get()))  # Valor de cada parcela fornecido
        pessoa = entry_pessoa.get().capitalize()
        pagamento = entry_pagamento.get().capitalize()
        total_parcelas = int(entry_parcelas.get()) if pagamento == "Crédito" else 1

        # Calcula o valor total com base nas parcelas
        valor_total = valor_parcela * total_parcelas

        # Determina a data inicial com base no usuário
        data = datetime.now()
        if pagamento == "Crédito":
            if pessoa == "Yuri":
                data = data.replace(day=14) if data.day < 14 else data.replace(day=14) + relativedelta(months=1)
            elif pessoa == "Marcos":
                data = data.replace(day=26) if data.day < 26 else data.replace(day=26) + relativedelta(months=1)

        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        for parcela in range(1, total_parcelas + 1):
            # Insere a parcela no banco
            valor = -valor_parcela  # Parcelas são negativas
            cursor.execute("""
                INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas)
                VALUES (%s, %s, %s, 'Compra', %s, %s, %s, %s)
            """, (data, descricao, valor, pessoa, pagamento, parcela, total_parcelas))

            # Incrementa a data para a próxima parcela
            data += relativedelta(months=1)

            # Replicar lançamentos recorrentes no novo mês criado
            replicate_recurring_entries(data.month, data.year)

        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

        tk.messagebox.showinfo("Sucesso", "Compra registrada com sucesso!")
    except Exception as e:
        tk.messagebox.showerror("Erro", f"Erro ao registrar a compra: {str(e)}")



# Função para criar a aba de Compras
def create_compras_tab(notebook):
    """
    Cria a aba de Compras no notebook e adiciona funcionalidade de visualização e registro de compras.
    """
    compras_tab = ttk.Frame(notebook)
    notebook.add(compras_tab, text="Compras")

    # Botão para visualizar compras
    btn_visualizar = tk.Button(compras_tab, text="Visualizar Compras", command=lambda: visualize_data())
    btn_visualizar.pack(pady=10)

    # Botão para registrar compras
    btn_registrar = tk.Button(compras_tab, text="Registrar Compra", command=open_register_compra_window)
    btn_registrar.pack(pady=10)

def open_register_compra_window():
    """
    Abre a janela para registrar uma nova compra.
    """
    window = tk.Toplevel()
    window.title("Registrar Compra")

    # Layout dos campos de entrada
    tk.Label(window, text="Descrição:", font=("Times New Roman", 12)).grid(row=0, column=0, padx=10, pady=5)
    global entry_descricao
    entry_descricao = tk.Entry(window, font=("Times New Roman", 12))
    entry_descricao.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="Valor:", font=("Times New Roman", 12)).grid(row=1, column=0, padx=10, pady=5)
    global entry_valor
    entry_valor = tk.Entry(window, font=("Times New Roman", 12))
    entry_valor.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(window, text="Pessoa:", font=("Times New Roman", 12)).grid(row=2, column=0, padx=10, pady=5)
    global entry_pessoa
    entry_pessoa = tk.Entry(window, font=("Times New Roman", 12))
    entry_pessoa.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(window, text="Forma de Pagamento:", font=("Times New Roman", 12)).grid(row=3, column=0, padx=10, pady=5)
    global entry_pagamento
    entry_pagamento = tk.Entry(window, font=("Times New Roman", 12))
    entry_pagamento.grid(row=3, column=1, padx=10, pady=5)

    tk.Label(window, text="Parcelas:", font=("Times New Roman", 12, "bold")).grid(row=4, column=0, padx=10, pady=5)
    global entry_parcelas
    entry_parcelas = tk.Entry(window)
    entry_parcelas.grid(row=4, column=1, padx=10, pady=5)

    # Botão de Salvar
    tk.Button(window, text="Salvar", font=("Times New Roman", 12, "bold"), bg="green", fg="white", command=save_compra).grid(row=5, column=0, columnspan=2, pady=10)

def format_currency(value):
    """Format a number as currency."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def visualize_data():
    """
    Visualiza os dados organizados por mês e ano, mantendo cálculos e totais.
    """

    def load_month_data(cursor, month, year):
        cursor.execute("""
            SELECT data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas
            FROM Movimentacoes
            WHERE EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s
            ORDER BY data
        """, (month, year))
        return cursor.fetchall()

    def calculate_totals(data, previous_month_total=0, previous_savings=0):
        total_recebimentos = sum(row[2] for row in data if row[3] in ["Recebimento", "Salário"])
        total_gastos = sum(row[2] for row in data if row[3] in ["Conta", "Compra"])
        total_poupanca = sum(row[2] for row in data if row[3] == "Poupança") - sum(row[2] for row in data if row[3] == "Retirada")
        total_gastos_y = sum(row[2] for row in data if row[3] in ["Conta", "Compra"] and row[4] == "Yuri")
        total_gastos_m = sum(row[2] for row in data if row[3] in ["Conta", "Compra"] and row[4] == "Marcos")
        total_recebimentos_y = sum(row[2] for row in data if row[3] in ["Recebimento", "Salário"] and row[4] == "Yuri")
        total_recebimentos_m = sum(row[2] for row in data if row[3] in ["Recebimento", "Salário"] and row[4] == "Marcos")

        current_savings = previous_savings + total_poupanca
        total_mes = previous_month_total + total_recebimentos + total_gastos - total_poupanca

        credito_yuri = sum(row[2] for row in data if row[5] == "Crédito" and row[4] == "Yuri")
        credito_marcos = sum(row[2] for row in data if row[5] == "Crédito" and row[4] == "Marcos")

        return {
            "total_poupanca": current_savings,
            "total_recebimentos": total_recebimentos,
            "total_gastos": total_gastos,
            "total_mes": total_mes,
            "credito_yuri": credito_yuri,
            "credito_marcos": credito_marcos,
            "total_gastos_y": total_gastos_y,
            "total_gastos_m": total_gastos_m,
            "total_recebimentos_y": total_recebimentos_y,
            "total_recebimentos_m": total_recebimentos_m
        }

    
    def update_view():
        # Limpa o conteúdo existente no notebook
        for tab in notebook.tabs():
            notebook.forget(tab)

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
            tab = tk.Frame(notebook, borderwidth=2, relief="solid")
            notebook.add(tab, text=f"{int(month):02d}/{int(year)}")
            notebook.pack(expand=1, fill="both")

            canvas = tk.Canvas(tab)
            scrollbar_y = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
            scrollbar_x = ttk.Scrollbar(tab, orient="horizontal", command=canvas.xview)
            scrollable_frame = ttk.Frame(canvas)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar_y.pack(side="right", fill="y")
            scrollbar_x.pack(side="bottom", fill="x")
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

            columns = ["Data", "Descrição", "Valor", "Tipo", "Pessoa", "Pagamento", "Parcela Atual", "Total Parcelas"]
            tree = ttk.Treeview(scrollable_frame, columns=columns, show="headings")
            tree.pack(expand=1, fill="both", padx=5, pady=5)

            for col in columns:
                tree.heading(col, text=col, anchor="center")
                tree.column(col, anchor="center", width=120)

            month_data = load_month_data(cursor, int(month), int(year))
            for row in month_data:
                formatted_row = (
                    row[0].strftime("%d/%m/%Y") if row[0] else "N/A",
                    row[1] or "N/A",
                    f"R$ {row[2]:,.2f}" if row[2] is not None else "0",
                    row[3] or "N/A",
                    row[4] or "N/A",
                    row[5] or "N/A",
                    row[6] or "N/A",
                    row[7] or "N/A",
                )
                item = tree.insert("", "end", values=formatted_row)
                if row[2] > 0:
                    tree.tag_configure("positive", background="lightgreen")
                    tree.item(item, tags="positive")
                elif row[2] < 0:
                    tree.tag_configure("negative", background="lightcoral")
                    tree.item(item, tags="negative")

                if row[3] == "Poupança":
                    tree.tag_configure("poupanca", background="lightblue")
                    tree.item(item, tags="poupanca")
                elif row[3] == "Retirada":
                    tree.tag_configure("retirada", background="yellow")
                    tree.item(item, tags="retirada")

            totals = calculate_totals(month_data, previous_month_total, previous_savings)

            def get_limit(pessoa):
                cursor.execute("""
                    SELECT valor FROM Limites
                    WHERE EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s AND pessoa = %s
                """, (month, year, pessoa))
                result = cursor.fetchone()
                return result[0] if result else 0

            limite_yuri = get_limit("Yuri")
            limite_marcos = get_limit("Marcos")

            limite_restante_yuri = limite_yuri + totals["total_gastos_y"]
            limite_restante_marcos = limite_marcos + totals["total_gastos_m"]

            footer_frame = tk.Frame(scrollable_frame, relief="groove", borderwidth=2)
            footer_frame.pack(fill="x", pady=10, padx=5)

            def add_footer_section(title, items):
                section_frame = tk.Frame(footer_frame)
                section_frame.pack(side="left", padx=10, pady=5)

                title_label = tk.Label(section_frame, text=f"{title}:", font=("Times New Roman", 12, "bold"))
                title_label.pack(anchor="w", padx=5)

                for label, value in items:
                    color = "green" if value > 0 else "red"
                    item_label = tk.Label(section_frame, text=f"{label}: R$ {value:,.2f}", font=("Times New Roman", 12), fg=color)
                    item_label.pack(anchor="w", padx=5)

            add_footer_section("Poupança", [("Total", totals["total_poupanca"])])
            add_footer_section("Entradas", [("Yuri", totals["total_recebimentos_y"]), ("Marcos", totals["total_recebimentos_m"]), ("Total", totals["total_recebimentos"])])
            add_footer_section("Saídas", [("Yuri", totals["total_gastos_y"]), ("Marcos", totals["total_gastos_m"]), ("Total", totals["total_gastos"])])
            add_footer_section("Crédito", [("Yuri", totals["credito_yuri"]), ("Marcos", totals["credito_marcos"])])
            add_footer_section("Limites", [("Yuri", limite_restante_yuri), ("Marcos", limite_restante_marcos)])
            add_footer_section("Totais", [("Mês Anterior", previous_month_total), ("Mês Corrente", totals["total_mes"])])

            previous_month_total = totals["total_mes"]
            previous_savings = totals["total_poupanca"]

        cursor.close()
        conn.close()

    view_window = tk.Toplevel()
    view_window.title("Visualizar Dados")
    notebook = ttk.Notebook(view_window)
    notebook.pack(expand=1, fill="both")

    # Atualiza a visualização automaticamente ao detectar alterações no banco
    def refresh_data():
        update_view()
        view_window.after(5000, refresh_data)  # Atualiza a cada 5 segundos

    refresh_data()

def definir_limite():
    """
    Abre uma janela para definir o limite de gastos de uma pessoa em um mês específico.
    """
    window = tk.Toplevel()
    window.title("Definir Limite de Gastos")

    tk.Label(window, text="Pessoa:", font=("Times New Roman", 12)).grid(row=0, column=0, padx=10, pady=5)
    pessoa_entry = tk.Entry(window, font=("Times New Roman", 12))
    pessoa_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="Mês (MM/AAAA):", font=("Times New Roman", 12)).grid(row=1, column=0, padx=10, pady=5)
    mes_entry = tk.Entry(window, font=("Times New Roman", 12))
    mes_entry.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(window, text="Valor Limite:", font=("Times New Roman", 12)).grid(row=2, column=0, padx=10, pady=5)
    valor_entry = tk.Entry(window, font=("Times New Roman", 12))
    valor_entry.grid(row=2, column=1, padx=10, pady=5)

    def salvar_limite():
        pessoa = pessoa_entry.get().capitalize()
        mes_ano = mes_entry.get()
        valor = float(valor_entry.get())

        try:
            mes, ano = map(int, mes_ano.split("/"))
            data_limite = datetime(ano, mes, 1)

            # Conexão com o banco PostgreSQL
            conn = connect_to_database()
            cursor = conn.cursor()

            # Insere ou atualiza o limite no banco
            cursor.execute("""
                INSERT INTO Limites (data, pessoa, valor)
                VALUES (%s, %s, %s)
                ON CONFLICT (data, pessoa) DO UPDATE SET valor = EXCLUDED.valor
            """, (data_limite, pessoa, valor))

            conn.commit()
            cursor.close()
            conn.close()

            tk.messagebox.showinfo("Sucesso", "Limite definido com sucesso!")
            window.destroy()
        except Exception as e:
            tk.messagebox.showerror("Erro", f"Erro ao definir o limite: {str(e)}")

    tk.Button(window, text="Salvar", font=("Times New Roman", 12, "bold"), bg="green", fg="white", command=salvar_limite).grid(row=3, column=0, columnspan=2, pady=10)




def save_conta():
    """
    Salva uma conta no banco de dados PostgreSQL com os dados fornecidos pelo usuário.
    """
    try:
        # Captura os dados da interface gráfica
        descricao = entry_conta_descricao.get()
        pessoa = entry_conta_pessoa.get().capitalize()
        dia_vencimento = int(entry_conta_vencimento.get())
        valor = abs(float(entry_conta_valor.get()))  # Valores positivos para contas
        frequencia = int(entry_conta_frequencia.get())
        pagamento = entry_conta_pagamento.get().capitalize()

        # Validação do dia de vencimento
        if not (1 <= dia_vencimento <= 31):
            tk.messagebox.showerror("Erro", "O dia de vencimento deve estar entre 1 e 31.")
            return

        # Calcula a data inicial com base no dia de vencimento e mês/ano atual
        hoje = datetime.now()
        vencimento = hoje.replace(day=dia_vencimento)
        if hoje.day > dia_vencimento:  # Ajusta para o próximo mês, se o dia já passou
            vencimento += relativedelta(months=1)

        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        # Inserção no banco para o mês atual
        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa, pagamento, parcela_atual, total_parcelas)
            VALUES (%s, %s, %s, 'Conta', %s, %s, NULL, %s)
        """, (vencimento, descricao, -valor, pessoa, pagamento, frequencia))

        # Se a frequência for 0, replica a conta para meses existentes
        if frequencia == 0:
            cursor.execute("""
                SELECT DISTINCT EXTRACT(MONTH FROM data) AS mes, EXTRACT(YEAR FROM data) AS ano
                FROM Movimentacoes
                ORDER BY ano, mes
            """
            )
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
                    """, (data_conta, descricao, -valor, pessoa, pagamento))

        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

        tk.messagebox.showinfo("Sucesso", "Conta registrada com sucesso!")
    except Exception as e:
        tk.messagebox.showerror("Erro", f"Erro ao registrar a conta: {str(e)}")



# Função para abrir a janela de registro de contas
def open_register_conta_window():
    """
    Abre a janela para registrar uma nova conta.
    """
    window = tk.Toplevel()
    window.title("Registrar Conta")

    # Layout dos campos de entrada
    tk.Label(window, text="Descrição:", font=("Times New Roman", 12)).grid(row=0, column=0, padx=10, pady=5)
    global entry_conta_descricao
    entry_conta_descricao = tk.Entry(window, font=("Times New Roman", 12))
    entry_conta_descricao.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="Pessoa:", font=("Times New Roman", 12)).grid(row=1, column=0, padx=10, pady=5)
    global entry_conta_pessoa
    entry_conta_pessoa = tk.Entry(window, font=("Times New Roman", 12))
    entry_conta_pessoa.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(window, text="Dia do Vencimento (1-31):", font=("Times New Roman", 12)).grid(row=2, column=0, padx=10, pady=5)
    global entry_conta_vencimento
    entry_conta_vencimento = tk.Entry(window, font=("Times New Roman", 12))
    entry_conta_vencimento.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(window, text="Valor:", font=("Times New Roman", 12)).grid(row=3, column=0, padx=10, pady=5)
    global entry_conta_valor
    entry_conta_valor = tk.Entry(window, font=("Times New Roman", 12))
    entry_conta_valor.grid(row=3, column=1, padx=10, pady=5)

    tk.Label(window, text="Frequência (dias ou 0):", font=("Times New Roman", 12)).grid(row=4, column=0, padx=10, pady=5)
    global entry_conta_frequencia
    entry_conta_frequencia = tk.Entry(window, font=("Times New Roman", 12))
    entry_conta_frequencia.grid(row=4, column=1, padx=10, pady=5)

    tk.Label(window, text="Pagamento:", font=("Times New Roman", 12)).grid(row=5, column=0, padx=10, pady=5)
    global entry_conta_pagamento
    entry_conta_pagamento = tk.Entry(window, font=("Times New Roman", 12))
    entry_conta_pagamento.grid(row=5, column=1, padx=10, pady=5)

    # Botão de Salvar
    tk.Button(window, text="Salvar", font=("Times New Roman", 12, "bold"), bg="green", fg="white", command=save_conta).grid(row=6, column=0, columnspan=2, pady=10)


def save_salario():
    """
    Salva um salário no banco de dados PostgreSQL apenas para meses existentes no sistema.
    """
    try:
        # Captura os dados da interface gráfica
        valor = abs(float(entry_valor_salario.get()))  # Salário é sempre positivo
        dia = int(entry_dia_salario.get())  # Apenas o dia
        pessoa = entry_pessoa_salario.get().capitalize()

        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        # Obtém os meses e anos existentes no banco
        cursor.execute("""
            SELECT DISTINCT EXTRACT(MONTH FROM data) AS mes, EXTRACT(YEAR FROM data) AS ano
            FROM Movimentacoes
            ORDER BY ano, mes
        """)
        meses_existentes = cursor.fetchall()

        # Adiciona o salário apenas nos meses existentes
        for mes, ano in meses_existentes:
            data_salario = datetime(int(ano), int(mes), dia)
            cursor.execute("""
                SELECT 1 FROM Movimentacoes
                WHERE data = %s AND descricao = 'Salário' AND pessoa = %s
            """, (data_salario, pessoa))
            if not cursor.fetchone():  # Verifica se já existe um salário registrado para essa data e pessoa
                cursor.execute("""
                    INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa)
                    VALUES (%s, 'Salário', %s, 'Recebimento', %s)
                """, (data_salario, valor, pessoa))

        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

        tk.messagebox.showinfo("Sucesso", "Salário registrado com sucesso para os meses existentes!")
    except Exception as e:
        tk.messagebox.showerror("Erro", f"Erro ao registrar o salário: {str(e)}")



def open_register_salario_window():
    """
    Abre a janela para registrar um novo salário.
    """
    window = tk.Toplevel()
    window.title("Registrar Salário")

    # Layout dos campos de entrada
    tk.Label(window, text="Valor:", font=("Times New Roman", 12)).grid(row=0, column=0, padx=10, pady=5)
    global entry_valor_salario
    entry_valor_salario = tk.Entry(window, font=("Times New Roman", 12))
    entry_valor_salario.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="Dia:", font=("Times New Roman", 12)).grid(row=1, column=0, padx=10, pady=5)
    global entry_dia_salario
    entry_dia_salario = tk.Entry(window, font=("Times New Roman", 12))
    entry_dia_salario.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(window, text="Pessoa:", font=("Times New Roman", 12)).grid(row=2, column=0, padx=10, pady=5)
    global entry_pessoa_salario
    entry_pessoa_salario = tk.Entry(window, font=("Times New Roman", 12))
    entry_pessoa_salario.grid(row=2, column=1, padx=10, pady=5)

    # Botão de Salvar
    tk.Button(window, text="Salvar", font=("Times New Roman", 12, "bold"), bg="green", fg="white", command=save_salario).grid(row=3, column=0, columnspan=2, pady=10)

def save_recebimento():
    """
    Salva um recebimento no banco de dados PostgreSQL e define sua recorrência com base na frequência indicada.
    """
    try:
        # Captura os dados da interface gráfica
        valor = abs(float(entry_valor_recebimento.get()))  # Recebimento é sempre positivo
        dia = int(entry_dia_recebimento.get())  # Apenas o dia
        descricao = entry_descricao_recebimento.get().capitalize()
        frequencia = int(entry_frequencia_recebimento.get()) 
        pessoa = entry_pessoa.get() # Quantidade de meses

        # Obtém o mês e ano atuais para iniciar a recorrência
        data_inicial = datetime.now().replace(day=dia)

        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        # Insere o recebimento no mês atual e em meses futuros conforme a frequência
        for i in range(0, frequencia):
            data = data_inicial + relativedelta(months=i)
            cursor.execute("""
                INSERT INTO Movimentacoes (data, descricao, valor, tipo, pessoa)
                VALUES (%s, %s, %s, 'Recebimento', %s)
            """, (data, descricao, valor, pessoa))

        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

        tk.messagebox.showinfo("Sucesso", "Recebimento registrado com sucesso!")
    except Exception as e:
        tk.messagebox.showerror("Erro", f"Erro ao registrar o recebimento: {str(e)}")



def open_register_recebimento_window():
    """
    Abre a janela para registrar um novo recebimento.
    """
    window = tk.Toplevel()
    window.title("Registrar Recebimento")

    # Layout dos campos de entrada
    tk.Label(window, text="Valor:", font=("Times New Roman", 12)).grid(row=0, column=0, padx=10, pady=5)
    global entry_valor_recebimento
    entry_valor_recebimento = tk.Entry(window, font=("Times New Roman", 12))
    entry_valor_recebimento.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="Dia:", font=("Times New Roman", 12)).grid(row=1, column=0, padx=10, pady=5)
    global entry_dia_recebimento
    entry_dia_recebimento = tk.Entry(window, font=("Times New Roman", 12))
    entry_dia_recebimento.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(window, text="Descrição:", font=("Times New Roman", 12)).grid(row=2, column=0, padx=10, pady=5)
    global entry_descricao_recebimento
    entry_descricao_recebimento = tk.Entry(window, font=("Times New Roman", 12))
    entry_descricao_recebimento.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(window, text="Frequência (meses):", font=("Times New Roman", 12)).grid(row=3, column=0, padx=10, pady=5)
    global entry_frequencia_recebimento
    entry_frequencia_recebimento = tk.Entry(window, font=("Times New Roman", 12))
    entry_frequencia_recebimento.grid(row=3, column=1, padx=10, pady=5)

    tk.Label(window, text="Pessoa:", font=("Times New Roman", 12)).grid(row=4, column=0, padx=10, pady=5)
    global entry_pessoa
    entry_pessoa = tk.Entry(window, font=("Times New Roman", 12))
    entry_pessoa.grid(row=4, column=1, padx=10, pady=5)
    # Botão de Salvar
    tk.Button(window, text="Salvar", font=("Times New Roman", 12, "bold"), bg="green", fg="white", command=save_recebimento).grid(row=5, column=0, columnspan=2, pady=10)

def propagate_poupanca():
    """
    Propaga os valores de poupança acumulados para os meses futuros na tabela Movimentacoes.
    """
    try:
        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        # Recupera o total acumulado de poupança até o momento
        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM Movimentacoes
            WHERE tipo = 'Poupança'
        """)
        total_poupanca = cursor.fetchone()[0]

        # Obtém os meses e anos futuros registrados no banco
        cursor.execute("""
            SELECT DISTINCT EXTRACT(MONTH FROM data) AS mes, EXTRACT(YEAR FROM data) AS ano
            FROM Movimentacoes
            WHERE data > CURRENT_DATE
            ORDER BY ano, mes
        """)
        meses_anos_futuros = cursor.fetchall()

        # Propaga o valor acumulado para os meses futuros
        for mes, ano in meses_anos_futuros:
            data_poupanca = datetime(int(ano), int(mes), 1)

            # Verifica se já existe um registro de poupança para o mês
            cursor.execute("""
                SELECT 1 FROM Movimentacoes
                WHERE data = %s AND tipo = 'Poupança'
            """, (data_poupanca,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Movimentacoes (data, descricao, valor, tipo)
                    VALUES (%s, 'Poupança Acumulada', %s, 'Poupança')
                """, (data_poupanca, total_poupanca))

        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

        tk.messagebox.showinfo("Sucesso", "Poupança propagada com sucesso!")
    except Exception as e:
        tk.messagebox.showerror("Erro", f"Erro ao propagar a poupança: {str(e)}")



# Ajuste na função save_poupanca
import decimal

# Ajuste na função save_poupanca
def save_poupanca():
    """
    Salva um registro de poupança no banco de dados PostgreSQL, ajustando a propagação para meses futuros.
    """
    try:
        # Captura os dados da interface gráfica
        valor = float(entry_valor_poupanca.get())  # Valor pode ser positivo ou negativo
        descricao = entry_descricao_poupanca.get()

        # Verifica se a descrição foi preenchida
        if not descricao.strip():
            tk.messagebox.showerror("Erro", "A descrição não pode estar vazia.")
            return

        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        # Insere o registro de poupança
        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo)
            VALUES (CURRENT_DATE, %s, %s, 'Poupança')
        """, (descricao, valor))

        

        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

        tk.messagebox.showinfo("Sucesso", "Poupança registrada com sucesso!")
    except Exception as e:
        tk.messagebox.showerror("Erro", f"Erro ao salvar a poupança: {str(e)}")

# Ajuste na função save_retirada
def save_retirada():
    """
    Retira um valor da poupança e adiciona ao total no banco de dados PostgreSQL, ajustando a propagação para meses futuros.
    """
    try:
        # Captura os dados da interface gráfica
        valor = float(entry_valor_retirada.get())  # Valor pode ser positivo ou negativo
        descricao = entry_descricao_retirada.get()

        # Verifica se a descrição foi preenchida
        if not descricao.strip():
            tk.messagebox.showerror("Erro", "A descrição não pode estar vazia.")
            return

        # Conexão com o banco PostgreSQL
        conn = connect_to_database()
        cursor = conn.cursor()

        # Insere o registro de retirada
        cursor.execute("""
            INSERT INTO Movimentacoes (data, descricao, valor, tipo)
            VALUES (CURRENT_DATE, %s, %s, 'Retirada')
        """, (descricao, valor))


        # Propaga a retirada para meses futuros, ajustando a poupança
        cursor.execute("""
            SELECT DISTINCT EXTRACT(MONTH FROM data) AS mes, EXTRACT(YEAR FROM data) AS ano
            FROM Movimentacoes
            WHERE data > CURRENT_DATE
            ORDER BY ano, mes
        """)
        meses_anos_futuros = cursor.fetchall()

        for mes, ano in meses_anos_futuros:
            data_retirada = datetime(int(ano), int(mes), 1)

    
        # Confirma as alterações no banco
        conn.commit()
        cursor.close()
        conn.close()

        tk.messagebox.showinfo("Sucesso", "Retirada registrada e propagada com sucesso!")
    except Exception as e:
        tk.messagebox.showerror("Erro", f"Erro ao salvar a retirada: {str(e)}")


def open_register_poupanca_window():
    """
    Abre a janela para registrar um novo valor de poupança.
    """
    window = tk.Toplevel()
    window.title("Registrar Poupança")

    # Layout dos campos de entrada
    tk.Label(window, text="Valor:", font=("Times New Roman", 12)).grid(row=0, column=0, padx=10, pady=5)
    global entry_valor_poupanca
    entry_valor_poupanca = tk.Entry(window, font=("Times New Roman", 12))
    entry_valor_poupanca.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="Descrição:", font=("Times New Roman", 12)).grid(row=1, column=0, padx=10, pady=5)
    global entry_descricao_poupanca
    entry_descricao_poupanca = tk.Entry(window, font=("Times New Roman", 12))
    entry_descricao_poupanca.grid(row=1, column=1, padx=10, pady=5)

    # Botão de Salvar
    tk.Button(window, text="Salvar", font=("Times New Roman", 12, "bold"), bg="green", fg="white", command=save_poupanca).grid(row=2, column=0, columnspan=2, pady=10)

def open_register_retirada_window():
    """
    Abre a janela para registrar uma nova retirada.
    """
    window = tk.Toplevel()
    window.title("Registrar Retirada")

    # Layout dos campos de entrada
    tk.Label(window, text="Valor:", font=("Times New Roman", 12)).grid(row=0, column=0, padx=10, pady=5)
    global entry_valor_retirada
    entry_valor_retirada = tk.Entry(window, font=("Times New Roman", 12))
    entry_valor_retirada.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="Descrição:", font=("Times New Roman", 12)).grid(row=1, column=0, padx=10, pady=5)
    global entry_descricao_retirada
    entry_descricao_retirada = tk.Entry(window, font=("Times New Roman", 12))
    entry_descricao_retirada.grid(row=1, column=1, padx=10, pady=5)

    # Botão de Salvar
    tk.Button(window, text="Salvar", font=("Times New Roman", 12, "bold"), bg="red", fg="white", command=save_retirada).grid(row=2, column=0, columnspan=2, pady=10)


    # Adicionando abas
def create_main_menu():
    """
    Cria a janela principal com botões para todas as funções.
    """
    menu_window = tk.Toplevel()
    menu_window.title("Controle Financeiro")

# Adiciona os botões para cada funcionalidade
    tk.Label(menu_window, text="Contole Financeiro do Amorrrrr", font=("Times New Roman", 16, "bold")).pack(pady=10)

    buttons = [
        ("Compra", open_register_compra_window),
        ("Conta", open_register_conta_window),
        ("Salário", open_register_salario_window),
        ("Recebimento", open_register_recebimento_window),
        ("Poupança", open_register_poupanca_window),
        ("Retirada", open_register_retirada_window),
        ("Limite", definir_limite),
        ("Visualizar", visualize_data)
        
    ]

    for text, command in buttons:
        btn = tk.Button(menu_window, text=text, font=("Times New Roman", 14), bg="purple", fg="black", command=command)
        btn.pack(pady=5, padx=10, fill="x")

    # Outros elementos do layout...
if __name__ == "__main__":
    try:
        conn = connect_to_database()
        conn.close()
    except Exception as e:
        print("Erro ao conectar ao banco:", e)

root = tk.Tk()    
create_main_menu()
root.mainloop()

