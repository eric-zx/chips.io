
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
import csv


# Tentar importar openpyxl para suporte XLSX
try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

# Para gráficos dinâmicos
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Paleta de cores modernas
COR_PRIMARIA = '#6366f1'
COR_SECUNDARIA = '#8b5cf6'
COR_ACCENT = '#06b6d4'
COR_SUCESSO = '#10b981'
COR_ERRO = '#ef4444'
COR_FUNDO = '#f8fafc'
COR_CARD = '#ffffff'
COR_TEXTO = '#1e293b'
COR_TEXTO_SECUNDARIO = '#64748b'

OPERADORAS = ['Claro', 'Tim', 'Arquia', 'Quectel Tim', 'Quectel Vivo', 'Vivo']

# Botão moderno
class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, width=150, height=40,
    
                 bg_color=COR_PRIMARIA, hover_color=COR_SECUNDARIA,
                 text_color='white', font=('Segoe UI', 10, 'bold')):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, relief=tk.FLAT, bg=parent.cget('bg'))
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = font
        self.text = text
        self.button_id = self.create_rectangle(2, 2, width-2, height-2,
                                               fill=bg_color, outline='', width=0)
        self.text_id = self.create_text(width//2, height//2, text=text,
                                        fill=text_color, font=font)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.tag_bind(self.button_id, '<Button-1>', lambda e: self.command())
        self.tag_bind(self.text_id, '<Button-1>', lambda e: self.command())

    def on_enter(self, event):
        self.itemconfig(self.button_id, fill=self.hover_color)
        self.configure(cursor='hand2')

    def on_leave(self, event):
        self.itemconfig(self.button_id, fill=self.bg_color)
        self.configure(cursor='')

class CardFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        bg = kwargs.pop('bg', COR_CARD)
        super().__init__(parent, bg=bg, **kwargs)
        self.config(relief=tk.FLAT, bd=0)
        self.inner_frame = tk.Frame(self, bg=bg, relief=tk.FLAT)
        self.inner_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

# Banco de dados
class Database:
    def __init__(self, db_name='chips.db'):
        self.db_name = db_name
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iccid TEXT UNIQUE NOT NULL,
                operadora TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Disponível',
                data_entrada TEXT NOT NULL,
                data_saida TEXT,
                retirado_por TEXT,
                observacoes TEXT,
                remessa_id INTEGER,
                FOREIGN KEY (remessa_id) REFERENCES remessas(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS remessas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_remessa TEXT UNIQUE NOT NULL,
                data_remessa TEXT NOT NULL,
                operadora TEXT,
                quantidade INTEGER,
                observacoes TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def limpar_iccid(self, iccid):
        return ''.join(filter(str.isdigit, iccid))

    def adicionar_chip(self, iccid, operadora, remessa_id=None, observacoes=''):
        iccid = self.limpar_iccid(iccid)
        if not iccid.isdigit():
            return False
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chips (iccid, operadora, data_entrada, remessa_id, observacoes)
                VALUES (?, ?, ?, ?, ?)
            ''', (iccid, operadora, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), remessa_id, observacoes))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def adicionar_chips_lote(self, chips, remessa_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        sucesso, falhas = 0, []
        for iccid, operadora in chips:
            iccid = self.limpar_iccid(iccid)
            if not iccid.isdigit():
                falhas.append(iccid)
                continue
            try:
                cursor.execute('''
                    INSERT INTO chips (iccid, operadora, data_entrada, remessa_id)
                    VALUES (?, ?, ?, ?)
                ''', (iccid, operadora, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), remessa_id))
                sucesso += 1
            except sqlite3.IntegrityError:
                falhas.append(iccid)
        conn.commit()
        conn.close()
        return sucesso, falhas

    def gerar_numero_remessa(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        data_atual = datetime.now().strftime('%Y%m%d')
        prefixo = f"REM-{data_atual}"
        cursor.execute('''
            SELECT numero_remessa FROM remessas
            WHERE numero_remessa LIKE ?
            ORDER BY numero_remessa DESC LIMIT 1
        ''', (f"{prefixo}-%",))
        resultado = cursor.fetchone()
        conn.close()
        proximo_num = int(resultado[0].split('-')[-1]) + 1 if resultado else 1
        return f"{prefixo}-{proximo_num:04d}"

    def criar_remessa(self, operadora, quantidade, observacoes=''):
        numero_remessa = self.gerar_numero_remessa()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO remessas (numero_remessa, data_remessa, operadora, quantidade, observacoes)
            VALUES (?, ?, ?, ?, ?)
        ''', (numero_remessa, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), operadora, quantidade, observacoes))
        remessa_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return remessa_id, numero_remessa

    def listar_chips(self, filtro_operadora=None, filtro_status=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = 'SELECT iccid, operadora, status, data_entrada, data_saida, retirado_por FROM chips WHERE 1=1'
        params = []
        if filtro_operadora:
            query += ' AND operadora=?'
            params.append(filtro_operadora)
        if filtro_status:
            query += ' AND status=?'
            params.append(filtro_status)
        query += ' ORDER BY data_entrada DESC'
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def listar_remessas(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, numero_remessa, data_remessa, operadora, quantidade, observacoes FROM remessas ORDER BY data_remessa DESC')
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def estatisticas(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM chips')
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chips WHERE status='Disponível'")
        disponiveis = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chips WHERE status='Retirado'")
        retirados = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM remessas')
        total_remessas = cursor.fetchone()[0]
        conn.close()
        return {'total': total, 'disponiveis': disponiveis, 'retirados': retirados, 'total_remessas': total_remessas}

class MonitoramentoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📱 Sistema de Monitoramento de Chips")
        self.root.geometry("1300x750")
        self.root.configure(bg=COR_FUNDO)
        self.db = Database()
        self.setup_styles()
        self.create_header()
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.criar_aba_cadastro_individual()
        self.criar_aba_cadastro_lote()
        self.criar_aba_retirada()
        self.criar_aba_consulta()
        self.criar_aba_remessas()
        self.criar_aba_estatisticas()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook.Tab', padding=[20, 10], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', COR_PRIMARIA)], foreground=[('selected', 'white')])

    def create_header(self):
        header = tk.Frame(self.root, bg=COR_PRIMARIA, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="📱 Monitoramento de Chips", font=('Segoe UI', 20, 'bold'),
                 bg=COR_PRIMARIA, fg='white').pack(side=tk.LEFT, padx=30)

    # -------------------------
    # ABA CADASTRO INDIVIDUAL
    # -------------------------
    def criar_aba_cadastro_individual(self):
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="➕ Cadastro Individual")

        card = CardFrame(frame)
        card.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        inner = card.inner_frame

        tk.Label(inner, text="ICCID:", font=('Segoe UI', 12, 'bold'), bg=COR_CARD).pack(pady=10)
        self.iccid_entry = ttk.Entry(inner, width=40)
        self.iccid_entry.pack(pady=5)

        tk.Label(inner, text="Operadora:", font=('Segoe UI', 12, 'bold'), bg=COR_CARD).pack(pady=10)
        self.operadora_combo = ttk.Combobox(inner, values=OPERADORAS, width=37, state='readonly')
        self.operadora_combo.pack(pady=5)

        ModernButton(inner, "✓ Cadastrar Chip", self.cadastrar_chip_individual,
                     width=180, height=45, bg_color=COR_SUCESSO, hover_color='#059669').pack(pady=20)

    def cadastrar_chip_individual(self):
        iccid = self.iccid_entry.get().strip()
        operadora = self.operadora_combo.get().strip()
        if not iccid or not operadora:
            messagebox.showerror("Erro", "Preencha todos os campos!")
            return
        if self.db.adicionar_chip(iccid, operadora):
            messagebox.showinfo("Sucesso", f"Chip {iccid} cadastrado!")
            self.iccid_entry.delete(0, tk.END)
            self.operadora_combo.set('')
        else:
            messagebox.showerror("Erro", "ICCID inválido ou já cadastrado!")

    # -------------------------
    # ABA CADASTRO EM LOTE
    # -------------------------
    def criar_aba_cadastro_lote(self):
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📦 Cadastro em Lote")

        card = CardFrame(frame)
        card.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        inner = card.inner_frame

        tk.Label(inner, text="Operadora da Remessa:", font=('Segoe UI', 12, 'bold'), bg=COR_CARD).pack(pady=10)
        self.operadora_remessa = ttk.Combobox(inner, values=OPERADORAS, width=37, state='readonly')
        self.operadora_remessa.pack(pady=5)

        ModernButton(inner, "📁 Importar CSV/XLSX", self.importar_arquivo,
                     width=180, height=45, bg_color=COR_ACCENT, hover_color='#0891b2').pack(pady=10)

        self.chips_text = scrolledtext.ScrolledText(inner, width=80, height=15)
        self.chips_text.pack(pady=10)

        ModernButton(inner, "✓ Cadastrar Lote", self.cadastrar_lote,
                     width=180, height=45, bg_color=COR_SUCESSO, hover_color='#059669').pack(pady=10)

    def importar_arquivo(self):
        arquivo = filedialog.askopenfilename(filetypes=[("CSV/XLSX", "*.csv *.xlsx")])
        if not arquivo:
            return
        linhas = []
        try:
            if arquivo.endswith('.xlsx') and XLSX_AVAILABLE:
                wb = openpyxl.load_workbook(arquivo)
                ws = wb.active
                for row in ws.iter_rows(values_only=True):
                    if row and row[0]:
                        iccid = ''.join(filter(str.isdigit, str(row[0])))
                        operadora = str(row[1]).strip() if len(row) > 1 and row[1] else ''
                        linhas.append(f"{iccid},{operadora}")
            else:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter=';')
                    for row in reader:
                        if row and row[0]:
                            iccid = ''.join(filter(str.isdigit, row[0]))
                            operadora = row[1].strip() if len(row) > 1 else ''
                            linhas.append(f"{iccid},{operadora}")
            self.chips_text.insert('1.0', '\n'.join(linhas))
            messagebox.showinfo("Sucesso", f"{len(linhas)} linhas importadas!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def cadastrar_lote(self):
        operadora = self.operadora_remessa.get().strip()
        linhas = self.chips_text.get('1.0', tk.END).strip().split('\n')
        chips = []
        for linha in linhas:
            partes = [p.strip() for p in linha.split(',')]
            if partes and partes[0]:
                iccid = ''.join(filter(str.isdigit, partes[0]))
                op = partes[1] if len(partes) > 1 and partes[1] else operadora
                if op in OPERADORAS:
                    chips.append((iccid, op))
        if not chips:
            messagebox.showerror("Erro", "Nenhum chip válido encontrado!")
            return
        remessa_id, numero_remessa = self.db.criar_remessa(operadora, len(chips))
        sucesso, falhas = self.db.adicionar_chips_lote(chips, remessa_id)
        messagebox.showinfo("Resultado", f"Remessa {numero_remessa} criada!\n{sucesso} chips cadastrados.\nFalhas: {len(falhas)}")
        self.chips_text.delete('1.0', tk.END)

    # -------------------------
    # ABA RETIRADA EM LOTE
    # -------------------------
    def criar_aba_retirada(self):
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📤 Retirada de Chips")

        card = CardFrame(frame)
        card.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        inner = card.inner_frame

        tk.Label(inner, text="Digite os ICCIDs (um por linha):", font=('Segoe UI', 12, 'bold'), bg=COR_CARD).pack(pady=10)
        self.retirada_text = scrolledtext.ScrolledText(inner, width=60, height=10)
        self.retirada_text.pack(pady=10)

        tk.Label(inner, text="Retirado por:", font=('Segoe UI', 12, 'bold'), bg=COR_CARD).pack(pady=10)
        self.retirado_por_entry = ttk.Entry(inner, width=40)
        self.retirado_por_entry.pack(pady=5)

        ModernButton(inner, "✓ Confirmar Retirada em Lote", self.retirar_chips_lote,
                     width=250, height=50, bg_color=COR_ERRO, hover_color='#dc2626').pack(pady=20)

    def retirar_chips_lote(self):
        iccids = [linha.strip() for linha in self.retirada_text.get('1.0', tk.END).split('\n') if linha.strip()]
        retirado_por = self.retirado_por_entry.get().strip()

        if not iccids or not retirado_por:
            messagebox.showerror("Erro", "Preencha todos os campos!")
            return

        conn = self.db.get_connection()
        cursor = conn.cursor()
        sucesso, falhas = 0, []
        for iccid in iccids:
            iccid_limpo = ''.join(filter(str.isdigit, iccid))
            cursor.execute('''
                UPDATE chips SET status='Retirado', data_saida=?, retirado_por=?
                WHERE iccid=? AND status='Disponível'
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), retirado_por, iccid_limpo))
            if cursor.rowcount > 0:
                sucesso += 1
            else:
                falhas.append(iccid)
        conn.commit()
        conn.close()

        mensagem = f"✓ {sucesso} chips retirados com sucesso!"
        if falhas:
            mensagem += f"\n⚠ {len(falhas)} não encontrados ou já retirados."
        messagebox.showinfo("Resultado", mensagem)

        self.retirada_text.delete('1.0', tk.END)
        self.retirado_por_entry.delete(0, tk.END)

    # -------------------------
    # ABA CONSULTA DE CHIPS
    # -------------------------
    def criar_aba_consulta(self):
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="🔍 Consulta de Chips")
        

        card = CardFrame(frame)
        card.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        inner = card.inner_frame

        filtro_frame = tk.Frame(inner, bg=COR_CARD)
        filtro_frame.pack(pady=10)

        tk.Label(filtro_frame, text="Operadora:", bg=COR_CARD).pack(side=tk.LEFT, padx=5)
        self.filtro_operadora = ttk.Combobox(filtro_frame, values=[''] + OPERADORAS, width=20)
        self.filtro_operadora.pack(side=tk.LEFT, padx=5)

        tk.Label(filtro_frame, text="Status:", bg=COR_CARD).pack(side=tk.LEFT, padx=5)
        self.filtro_status = ttk.Combobox(filtro_frame, values=['', 'Disponível', 'Retirado'], width=18)
        self.filtro_status.pack(side=tk.LEFT, padx=5)

        ModernButton(filtro_frame, "🔍 Buscar", self.atualizar_consulta,
                     width=120, height=35, bg_color=COR_PRIMARIA, hover_color=COR_SECUNDARIA).pack(side=tk.LEFT, padx=10)

        self.tree = ttk.Treeview(inner, columns=('ICCID', 'Operadora', 'Status', 'Entrada', 'Saída', 'Retirado Por'),
                                 show='headings', height=20)
        for col in ('ICCID', 'Operadora', 'Status', 'Entrada', 'Saída', 'Retirado Por'):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=180)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

    def atualizar_consulta(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        filtro_op = self.filtro_operadora.get() or None
        filtro_st = self.filtro_status.get() or None
        chips = self.db.listar_chips(filtro_op, filtro_st)
        for iccid, operadora, status, entrada, saida, retirado_por in chips:
            self.tree.insert('', tk.END, values=(iccid, operadora, status, entrada, saida or '', retirado_por or ''))

    # -------------------------
    # ABA REMESSAS COM EXCLUSÃO
    # -------------------------
    def criar_aba_remessas(self):
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📋 Remessas")
        card = CardFrame(frame)
        card.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        inner = card.inner_frame

        tk.Label(inner, text="📋 Histórico de Remessas", font=('Segoe UI', 16, 'bold'), bg=COR_CARD).pack(pady=10)

        self.remessas_tree = ttk.Treeview(inner, columns=('ID', 'Número', 'Data', 'Operadora', 'Qtd', 'Obs'),
                                          show='headings', height=20)
        for col in ('ID', 'Número', 'Data', 'Operadora', 'Qtd', 'Obs'):
            self.remessas_tree.heading(col, text=col)
            self.remessas_tree.column(col, width=180)
        self.remessas_tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(inner, bg=COR_CARD)
        btn_frame.pack(pady=10)

        ModernButton(btn_frame, "🔄 Atualizar", self.atualizar_remessas,
                     width=150, height=40, bg_color=COR_PRIMARIA, hover_color=COR_SECUNDARIA).pack(side=tk.LEFT, padx=5)

        ModernButton(btn_frame, "🗑 Excluir Remessa", self.excluir_remessa,
                     width=180, height=40, bg_color=COR_ERRO, hover_color='#dc2626').pack(side=tk.LEFT, padx=5)

        self.atualizar_remessas()

    def atualizar_remessas(self):
        for item in self.remessas_tree.get_children():
            self.remessas_tree.delete(item)
        remessas = self.db.listar_remessas()
        for r in remessas:
            self.remessas_tree.insert('', tk.END, values=r)

    def excluir_remessa(self):
        selecionado = self.remessas_tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma remessa para excluir!")
            return

        item = selecionado[0]
        valores = self.remessas_tree.item(item, 'values')
        remessa_id, numero_remessa = valores[0], valores[1]

        resposta = messagebox.askyesno("Confirmar Exclusão",
                                       f"Deseja excluir a remessa {numero_remessa}?\n\n"
                                       "Isso não pode ser desfeito.")
        if not resposta:
            return

        excluir_chips = messagebox.askyesno("Excluir Chips",
                                            "Deseja também excluir os chips vinculados a esta remessa?")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            if excluir_chips:
                cursor.execute("DELETE FROM chips WHERE remessa_id=?", (remessa_id,))
            cursor.execute("DELETE FROM remessas WHERE id=?", (remessa_id,))
            conn.commit()
            messagebox.showinfo("Sucesso", f"Remessa {numero_remessa} excluída com sucesso!")
            self.atualizar_remessas()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao excluir: {str(e)}")
        finally:
            conn.close()

    # -------------------------
    # ABA ESTATÍSTICAS COM GRÁFICO
    # -------------------------
    def criar_aba_estatisticas(self):
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📊 Estatísticas")
        card = CardFrame(frame)
        card.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        inner = card.inner_frame
        tk.Label(inner, text="📊 Estatísticas do Sistema", font=('Segoe UI', 18, 'bold'), bg=COR_CARD).pack(pady=20)
        self.stats_label = tk.Label(inner, text="", font=('Segoe UI', 14), bg=COR_CARD)
        self.stats_label.pack(pady=10)
        ModernButton(inner, "🔄 Atualizar Estatísticas", self.atualizar_estatisticas,
                     width=220, height=45, bg_color=COR_PRIMARIA, hover_color=COR_SECUNDARIA).pack(pady=20)

    def atualizar_estatisticas(self):
        stats = self.db.estatisticas()
        texto = (f"Total de Chips: {stats['total']}\n"
                 f"Disponíveis: {stats['disponiveis']}\n"
                 f"Retirados: {stats['retirados']}\n"
                 f"Total de Remessas: {stats['total_remessas']}")
        self.stats_label.config(text=texto)
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
            valores = [stats['disponiveis'], stats['retirados']]
            labels = ['Disponíveis', 'Retirados']
            ax.pie(valores, labels=labels, autopct='%1.1f%%', colors=[COR_SUCESSO, COR_ERRO], startangle=90)
            ax.set_title('Distribuição de Chips')
            canvas = FigureCanvasTkAgg(fig, master=self.stats_label.master)
            canvas.draw()
            canvas.get_tk_widget().pack(pady=10)


# ==========================
# MAIN
# ==========================
def main():
    root = tk.Tk()
    app = MonitoramentoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
