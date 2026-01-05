import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from typing import List, Tuple, Optional
import csv
import io

# Tentar importar openpyxl para suporte XLSX
try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

# Operadoras disponíveis
OPERADORAS = ['Claro', 'Tim', 'Arquia', 'Quectel Tim', 'Quectel Vivo', 'Vivo']

# Cores modernas do tema
COR_PRIMARIA = '#6366f1'  # Indigo moderno
COR_SECUNDARIA = '#8b5cf6'  # Roxo
COR_ACCENT = '#06b6d4'  # Cyan
COR_SUCESSO = '#10b981'  # Verde
COR_ERRO = '#ef4444'  # Vermelho
COR_FUNDO = '#f8fafc'  # Cinza claro
COR_CARD = '#ffffff'  # Branco
COR_TEXTO = '#1e293b'  # Cinza escuro
COR_TEXTO_SECUNDARIO = '#64748b'  # Cinza médio

class ModernButton(tk.Canvas):
    """Botão moderno com efeitos visuais"""
    
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
        
        # Desenhar botão
        self.button_id = self.create_rounded_rect(2, 2, width-2, height-2, 
                                                   radius=8, fill=bg_color, outline='')
        self.text_id = self.create_text(width//2, height//2, text=text, 
                                       fill=text_color, font=font)
        
        # Bind eventos
        self.bind('<Button-1>', self.on_click)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Motion>', self.on_enter)
        
        # Tags
        self.tag_bind(self.button_id, '<Button-1>', self.on_click)
        self.tag_bind(self.text_id, '<Button-1>', self.on_click)
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        """Cria um retângulo arredondado"""
        # Método simplificado usando create_rectangle com borderradius
        # Para tkinter, usamos create_rectangle diretamente
        return self.create_rectangle(x1, y1, x2, y2, **kwargs)
    
    def on_enter(self, event):
        """Efeito hover"""
        self.itemconfig(self.button_id, fill=self.hover_color)
        self.configure(cursor='hand2')
    
    def on_leave(self, event):
        """Remove efeito hover"""
        self.itemconfig(self.button_id, fill=self.bg_color)
        self.configure(cursor='')
    
    def on_click(self, event):
        """Animação de clique"""
        original_color = self.bg_color
        self.itemconfig(self.button_id, fill=COR_ACCENT)
        self.update()
        self.after(100, lambda: self.itemconfig(self.button_id, fill=original_color))
        self.after(150, self.command)


class CardFrame(tk.Frame):
    """Frame estilo card com sombra visual"""
    
    def __init__(self, parent, **kwargs):
        bg = kwargs.pop('bg', COR_CARD)
        super().__init__(parent, bg=bg, **kwargs)
        
        # Container com borda sutil
        self.config(relief=tk.FLAT, bd=0)
        self.inner_frame = tk.Frame(self, bg=bg, relief=tk.FLAT)
        self.inner_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)


class Database:
    """Classe para gerenciar o banco de dados"""
    
    def __init__(self, db_name='chips.db'):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_database(self):
        """Inicializa as tabelas do banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabela de chips
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
        
        # Tabela de remessas
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
    
    def adicionar_chip(self, iccid: str, operadora: str, remessa_id: Optional[int] = None, observacoes: str = ''):
        """Adiciona um chip ao banco de dados"""
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
    
    def adicionar_chips_lote(self, chips: List[Tuple[str, str]], remessa_id: Optional[int] = None):
        """Adiciona múltiplos chips em lote"""
        conn = self.get_connection()
        cursor = conn.cursor()
        sucesso = 0
        falhas = []
        
        for iccid, operadora in chips:
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
    
    def gerar_numero_remessa(self) -> str:
        """Gera um número de remessa único no formato REM-YYYYMMDD-NNNN"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        data_atual = datetime.now().strftime('%Y%m%d')
        prefixo = f"REM-{data_atual}"
        
        # Buscar última remessa do dia
        cursor.execute('''
            SELECT numero_remessa FROM remessas 
            WHERE numero_remessa LIKE ?
            ORDER BY numero_remessa DESC
            LIMIT 1
        ''', (f"{prefixo}-%",))
        
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            # Extrair o último número
            ultimo_num = resultado[0].split('-')[-1]
            try:
                proximo_num = int(ultimo_num) + 1
            except ValueError:
                proximo_num = 1
        else:
            proximo_num = 1
        
        # Formatar com 4 dígitos (0001, 0002, etc)
        numero_remessa = f"{prefixo}-{proximo_num:04d}"
        return numero_remessa
    
    def criar_remessa(self, numero_remessa: Optional[str] = None, operadora: str = '', quantidade: int = 0, observacoes: str = ''):
        """Cria uma nova remessa. Se numero_remessa for None, gera automaticamente"""
        if numero_remessa is None or numero_remessa == '' or (isinstance(numero_remessa, str) and numero_remessa.strip() == ''):
            numero_remessa = self.gerar_numero_remessa()
        
        max_tentativas = 100
        tentativa = 0
        
        while tentativa < max_tentativas:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO remessas (numero_remessa, data_remessa, operadora, quantidade, observacoes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (numero_remessa, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), operadora, quantidade, observacoes))
                remessa_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return remessa_id, numero_remessa
            except sqlite3.IntegrityError:
                conn.close()
                # Se colidir, gera novo número
                numero_remessa = self.gerar_numero_remessa()
                tentativa += 1
        
        return None, None
    
    def retirar_chip(self, iccid: str, retirado_por: str):
        """Registra a retirada de um chip"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE chips 
            SET status = 'Retirado', 
                data_saida = ?,
                retirado_por = ?
            WHERE iccid = ? AND status = 'Disponível'
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), retirado_por, iccid))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False
    
    def buscar_chip(self, iccid: str):
        """Busca informações de um chip"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, iccid, operadora, status, data_entrada, data_saida, retirado_por, observacoes
            FROM chips
            WHERE iccid = ?
        ''', (iccid,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    
    def listar_chips(self, filtro_operadora: Optional[str] = None, filtro_status: Optional[str] = None):
        """Lista todos os chips com filtros opcionais"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT id, iccid, operadora, status, data_entrada, data_saida, retirado_por FROM chips WHERE 1=1'
        params = []
        
        if filtro_operadora:
            query += ' AND operadora = ?'
            params.append(filtro_operadora)
        
        if filtro_status:
            query += ' AND status = ?'
            params.append(filtro_status)
        
        query += ' ORDER BY data_entrada DESC'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    
    def listar_remessas(self):
        """Lista todas as remessas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, numero_remessa, data_remessa, operadora, quantidade, observacoes FROM remessas ORDER BY data_remessa DESC')
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    
    def buscar_chips_remessa(self, remessa_id: int):
        """Busca todos os chips de uma remessa"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, iccid, operadora, status, data_entrada, data_saida, retirado_por
            FROM chips
            WHERE remessa_id = ?
            ORDER BY data_entrada
        ''', (remessa_id,))
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    
    def buscar_remessa_por_id(self, remessa_id: int):
        """Busca informações de uma remessa pelo ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, numero_remessa, data_remessa, operadora, quantidade, observacoes FROM remessas WHERE id = ?', (remessa_id,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    
    def excluir_remessa(self, remessa_id: int, excluir_chips: bool = False):
        """Exclui uma remessa e opcionalmente os chips relacionados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if excluir_chips:
                # Excluir chips primeiro
                cursor.execute('DELETE FROM chips WHERE remessa_id = ?', (remessa_id,))
            
            # Excluir remessa
            cursor.execute('DELETE FROM remessas WHERE id = ?', (remessa_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            return False
    
    def estatisticas(self):
        """Retorna estatísticas do sistema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM chips')
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chips WHERE status = 'Disponível'")
        disponiveis = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chips WHERE status = 'Retirado'")
        retirados = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM remessas')
        total_remessas = cursor.fetchone()[0]
        
        conn.close()
        return {
            'total': total,
            'disponiveis': disponiveis,
            'retirados': retirados,
            'total_remessas': total_remessas
        }


class MonitoramentoApp:
    """Aplicação principal de monitoramento de chips"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("📱 Sistema de Monitoramento de Chips")
        self.root.geometry("1300x750")
        self.root.configure(bg=COR_FUNDO)
        
        # Configurar estilo
        self.setup_styles()
        
        self.db = Database()
        
        # Header
        self.create_header()
        
        # Criar notebook (abas) com estilo moderno
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=COR_FUNDO, borderwidth=0)
        style.configure('TNotebook.Tab', padding=[20, 10], background=COR_CARD, 
                       foreground=COR_TEXTO, font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', COR_PRIMARIA)], 
                 foreground=[('selected', 'white')])
        
        notebook_container = tk.Frame(root, bg=COR_FUNDO)
        notebook_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.notebook = ttk.Notebook(notebook_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Abas
        self.criar_aba_cadastro_individual()
        self.criar_aba_cadastro_lote()
        self.criar_aba_retirada()
        self.criar_aba_consulta()
        self.criar_aba_remessas()
        self.criar_aba_estatisticas()
    
    def setup_styles(self):
        """Configura estilos modernos"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Entry style
        style.configure('Modern.TEntry', fieldbackground='white', borderwidth=2, 
                       relief=tk.FLAT, padding=8, font=('Segoe UI', 10))
        style.map('Modern.TEntry', bordercolor=[('focus', COR_PRIMARIA)])
        
        # Combobox style
        style.configure('Modern.TCombobox', fieldbackground='white', borderwidth=2, 
                       relief=tk.FLAT, padding=8, font=('Segoe UI', 10))
        style.map('Modern.TCombobox', bordercolor=[('focus', COR_PRIMARIA)])
        
        # Treeview style
        style.configure('Modern.Treeview', background='white', foreground=COR_TEXTO,
                       fieldbackground='white', rowheight=30, font=('Segoe UI', 9))
        style.configure('Modern.Treeview.Heading', background=COR_PRIMARIA, 
                       foreground='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT)
        style.map('Modern.Treeview', background=[('selected', COR_PRIMARIA)])
    
    def create_header(self):
        """Cria cabeçalho moderno"""
        header = tk.Frame(self.root, bg=COR_PRIMARIA, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_frame = tk.Frame(header, bg=COR_PRIMARIA)
        title_frame.pack(side=tk.LEFT, padx=30, pady=15)
        
        title_label = tk.Label(title_frame, text="📱 Monitoramento de Chips", 
                              font=('Segoe UI', 20, 'bold'), bg=COR_PRIMARIA, 
                              fg='white')
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(title_frame, text="Sistema de Gestão de Chips SIM", 
                                 font=('Segoe UI', 10), bg=COR_PRIMARIA, 
                                 fg='#c7d2fe')
        subtitle_label.pack(side=tk.LEFT, padx=(15, 0))
    
    def criar_aba_cadastro_individual(self):
        """Cria a aba de cadastro individual"""
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="➕ Cadastro Individual")
        
        # Container principal
        main_container = tk.Frame(frame, bg=COR_FUNDO)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Card principal
        card = CardFrame(main_container, bg=COR_CARD)
        card.pack(fill=tk.BOTH, expand=True)
        
        inner = card.inner_frame
        
        # Título
        title_frame = tk.Frame(inner, bg=COR_CARD)
        title_frame.pack(pady=(30, 20))
        
        tk.Label(title_frame, text="📝 Cadastro Individual de Chip", 
                font=('Segoe UI', 18, 'bold'), bg=COR_CARD, fg=COR_TEXTO).pack()
        tk.Label(title_frame, text="Cadastre chips individualmente no sistema", 
                font=('Segoe UI', 10), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO).pack(pady=(5, 0))
        
        # Formulário centralizado
        form_frame = tk.Frame(inner, bg=COR_CARD)
        form_frame.pack(pady=30, padx=50)
        
        # ICCID
        tk.Label(form_frame, text="ICCID", font=('Segoe UI', 11, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=0, column=0, sticky=tk.W, pady=(0, 8), padx=(0, 20))
        self.iccid_entry = ttk.Entry(form_frame, style='Modern.TEntry', width=45, font=('Segoe UI', 11))
        self.iccid_entry.grid(row=0, column=1, pady=(0, 20), ipady=8)
        
        # Operadora
        tk.Label(form_frame, text="Operadora", font=('Segoe UI', 11, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=1, column=0, sticky=tk.W, pady=(0, 8), padx=(0, 20))
        self.operadora_combo = ttk.Combobox(form_frame, values=OPERADORAS, 
                                           style='Modern.TCombobox', width=42, 
                                           font=('Segoe UI', 11), state='readonly')
        self.operadora_combo.grid(row=1, column=1, pady=(0, 20), ipady=8)
        
        # Observações
        tk.Label(form_frame, text="Observações", font=('Segoe UI', 11, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=2, column=0, sticky=tk.NW, pady=(0, 8), padx=(0, 20))
        self.obs_text = scrolledtext.ScrolledText(form_frame, width=42, height=6, 
                                                  font=('Segoe UI', 10), relief=tk.FLAT, 
                                                  borderwidth=2, highlightthickness=1,
                                                  highlightbackground='#e2e8f0',
                                                  highlightcolor=COR_PRIMARIA,
                                                  bg='white', fg=COR_TEXTO)
        self.obs_text.grid(row=2, column=1, pady=(0, 30), ipady=5)
        
        # Botão de cadastro
        btn_frame = tk.Frame(form_frame, bg=COR_CARD)
        btn_frame.grid(row=3, column=1, sticky=tk.W, pady=(0, 20))
        
        btn_cadastrar = ModernButton(btn_frame, "✓ Cadastrar Chip", 
                                    self.cadastrar_chip_individual,
                                    width=180, height=45, bg_color=COR_SUCESSO,
                                    hover_color='#059669', font=('Segoe UI', 11, 'bold'))
        btn_cadastrar.pack(side=tk.LEFT)
        
        # Mensagem de status
        self.status_label = tk.Label(form_frame, text="", font=('Segoe UI', 10), 
                                     bg=COR_CARD, fg=COR_SUCESSO)
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10)
    
    def criar_aba_cadastro_lote(self):
        """Cria a aba de cadastro em lote"""
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📦 Cadastro em Lote")
        
        # Container principal
        main_container = tk.Frame(frame, bg=COR_FUNDO)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Card de remessa
        remessa_card = CardFrame(main_container, bg=COR_CARD)
        remessa_card.pack(fill=tk.X, pady=(0, 20))
        
        remessa_inner = remessa_card.inner_frame
        
        tk.Label(remessa_inner, text="📋 Informações da Remessa", 
                font=('Segoe UI', 14, 'bold'), bg=COR_CARD, fg=COR_TEXTO).pack(pady=(20, 15), anchor=tk.W, padx=20)
        
        remessa_form = tk.Frame(remessa_inner, bg=COR_CARD)
        remessa_form.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        tk.Label(remessa_form, text="Número da Remessa", font=('Segoe UI', 10, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=0, column=0, sticky=tk.W, pady=8, padx=(0, 15))
        
        self.num_remessa_entry = ttk.Entry(remessa_form, style='Modern.TEntry', width=30, font=('Segoe UI', 10), state='readonly')
        self.num_remessa_entry.grid(row=0, column=1, pady=8, sticky=tk.W, ipady=6)
        
        # Gerar número inicial
        self.atualizar_numero_remessa()
        
        tk.Label(remessa_form, text="Operadora", font=('Segoe UI', 10, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=1, column=0, sticky=tk.W, pady=8, padx=(0, 15))
        self.remessa_operadora_combo = ttk.Combobox(remessa_form, values=OPERADORAS, 
                                                    style='Modern.TCombobox', width=32, 
                                                    font=('Segoe UI', 10), state='readonly')
        self.remessa_operadora_combo.grid(row=1, column=1, pady=8, sticky=tk.W, ipady=6)
        
        tk.Label(remessa_form, text="Observações", font=('Segoe UI', 10, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=2, column=0, sticky=tk.NW, pady=8, padx=(0, 15))
        self.remessa_obs_text = scrolledtext.ScrolledText(remessa_form, width=32, height=3, 
                                                          font=('Segoe UI', 9), relief=tk.FLAT,
                                                          borderwidth=2, highlightthickness=1,
                                                          highlightbackground='#e2e8f0',
                                                          highlightcolor=COR_PRIMARIA,
                                                          bg='white', fg=COR_TEXTO)
        self.remessa_obs_text.grid(row=2, column=1, pady=8, sticky=tk.W, ipady=5)
        
        # Card de chips
        chips_card = CardFrame(main_container, bg=COR_CARD)
        chips_card.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        chips_inner = chips_card.inner_frame
        
        tk.Label(chips_inner, text="📝 Lista de Chips (ICCID, Operadora)", 
                font=('Segoe UI', 14, 'bold'), bg=COR_CARD, fg=COR_TEXTO).pack(pady=(20, 10), anchor=tk.W, padx=20)
        texto_formato = "Formato: ICCID,Operadora (um por linha) ou apenas ICCID (usará operadora da remessa)"
        texto_formato += "\nImporte CSV/XLSX: Coluna A = ICCID, Coluna B = Operadora (opcional)"
        if not XLSX_AVAILABLE:
            texto_formato += " | Instale openpyxl para suporte XLSX: pip install openpyxl"
        tk.Label(chips_inner, text=texto_formato, 
                font=('Segoe UI', 9), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO, 
                justify=tk.LEFT).pack(anchor=tk.W, padx=20, pady=(0, 10))
        
        chips_text_frame = tk.Frame(chips_inner, bg=COR_CARD)
        chips_text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        self.chips_text = scrolledtext.ScrolledText(chips_text_frame, width=60, height=18, 
                                                    font=('Consolas', 10), relief=tk.FLAT,
                                                    borderwidth=2, highlightthickness=1,
                                                    highlightbackground='#e2e8f0',
                                                    highlightcolor=COR_PRIMARIA,
                                                    bg='#f8fafc', fg=COR_TEXTO)
        self.chips_text.pack(fill=tk.BOTH, expand=True)
        
        # Botões
        btn_frame = tk.Frame(chips_inner, bg=COR_CARD)
        btn_frame.pack(pady=(0, 20), padx=20)
        
        btn_text = "📁 Importar CSV/XLSX" if XLSX_AVAILABLE else "📁 Importar CSV"
        btn_importar = ModernButton(btn_frame, btn_text, self.importar_arquivo,
                                    width=170, height=40, bg_color=COR_ACCENT, hover_color='#0891b2',
                                    font=('Segoe UI', 10, 'bold'))
        btn_importar.pack(side=tk.LEFT, padx=5)
        
        btn_cadastrar = ModernButton(btn_frame, "✓ Cadastrar Lote", self.cadastrar_lote,
                                    width=160, height=40, bg_color=COR_SUCESSO, hover_color='#059669',
                                    font=('Segoe UI', 10, 'bold'))
        btn_cadastrar.pack(side=tk.LEFT, padx=5)
        
        btn_limpar = ModernButton(btn_frame, "🗑️ Limpar", self.limpar_lote,
                                  width=120, height=40, bg_color=COR_TEXTO_SECUNDARIO, 
                                  hover_color='#475569', font=('Segoe UI', 10, 'bold'))
        btn_limpar.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.lote_status_label = tk.Label(chips_inner, text="", font=('Segoe UI', 10), 
                                          bg=COR_CARD, fg=COR_SUCESSO)
        self.lote_status_label.pack(pady=(0, 15))
    
    def criar_aba_retirada(self):
        """Cria a aba de retirada de chips"""
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📤 Retirada de Chip")
        
        # Container principal
        main_container = tk.Frame(frame, bg=COR_FUNDO)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=40)
        
        # Card principal
        card = CardFrame(main_container, bg=COR_CARD)
        card.pack(fill=tk.BOTH, expand=True)
        
        inner = card.inner_frame
        
        # Título
        title_frame = tk.Frame(inner, bg=COR_CARD)
        title_frame.pack(pady=(40, 30))
        
        tk.Label(title_frame, text="📤 Retirada de Chip", 
                font=('Segoe UI', 18, 'bold'), bg=COR_CARD, fg=COR_TEXTO).pack()
        tk.Label(title_frame, text="Registre a saída de chips do estoque", 
                font=('Segoe UI', 10), bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO).pack(pady=(5, 0))
        
        # Formulário centralizado
        form_frame = tk.Frame(inner, bg=COR_CARD)
        form_frame.pack(pady=30, padx=80)
        
        tk.Label(form_frame, text="ICCID", font=('Segoe UI', 12, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=0, column=0, sticky=tk.W, pady=(0, 10), padx=(0, 25))
        self.retirada_iccid_entry = ttk.Entry(form_frame, style='Modern.TEntry', width=45, font=('Segoe UI', 11))
        self.retirada_iccid_entry.grid(row=0, column=1, pady=(0, 25), ipady=10)
        self.retirada_iccid_entry.bind('<KeyRelease>', self.buscar_chip_retirada)
        
        tk.Label(form_frame, text="Retirado por", font=('Segoe UI', 12, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).grid(row=1, column=0, sticky=tk.W, pady=(0, 10), padx=(0, 25))
        self.retirado_por_entry = ttk.Entry(form_frame, style='Modern.TEntry', width=45, font=('Segoe UI', 11))
        self.retirado_por_entry.grid(row=1, column=1, pady=(0, 30), ipady=10)
        
        # Informações do chip
        info_card = CardFrame(form_frame, bg='#f1f5f9')
        info_card.grid(row=2, column=0, columnspan=2, pady=(0, 30), sticky=tk.EW, padx=20)
        info_inner = info_card.inner_frame
        
        tk.Label(info_inner, text="ℹ️ Informações do Chip", 
                font=('Segoe UI', 11, 'bold'), bg='#f1f5f9', fg=COR_TEXTO).pack(pady=(15, 10), anchor=tk.W, padx=20)
        
        self.chip_info_label = tk.Label(info_inner, text="Digite o ICCID para buscar informações", 
                                        font=('Segoe UI', 10), bg='#f1f5f9', 
                                        fg=COR_TEXTO_SECUNDARIO, justify=tk.LEFT)
        self.chip_info_label.pack(pady=(0, 15), padx=20, anchor=tk.W)
        
        # Botão
        btn_frame = tk.Frame(form_frame, bg=COR_CARD)
        btn_frame.grid(row=3, column=1, sticky=tk.E, pady=(0, 20))
        
        btn_retirar = ModernButton(btn_frame, "✓ Confirmar Retirada", self.retirar_chip,
                                   width=200, height=50, bg_color=COR_ERRO, hover_color='#dc2626',
                                   font=('Segoe UI', 11, 'bold'))
        btn_retirar.pack()
        
        # Status
        self.retirada_status_label = tk.Label(form_frame, text="", font=('Segoe UI', 10), 
                                              bg=COR_CARD, fg=COR_SUCESSO)
        self.retirada_status_label.grid(row=4, column=0, columnspan=2, pady=10)
    
    def criar_aba_consulta(self):
        """Cria a aba de consulta"""
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="🔍 Consulta de Chips")
        
        # Container principal
        main_container = tk.Frame(frame, bg=COR_FUNDO)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Card de filtros
        filtro_card = CardFrame(main_container, bg=COR_CARD)
        filtro_card.pack(fill=tk.X, pady=(0, 20))
        
        filtro_inner = filtro_card.inner_frame
        
        tk.Label(filtro_inner, text="🔍 Filtros de Busca", 
                font=('Segoe UI', 14, 'bold'), bg=COR_CARD, fg=COR_TEXTO).pack(pady=(20, 15), anchor=tk.W, padx=20)
        
        filtro_frame = tk.Frame(filtro_inner, bg=COR_CARD)
        filtro_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        tk.Label(filtro_frame, text="Operadora:", font=('Segoe UI', 10, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).pack(side=tk.LEFT, padx=(0, 10))
        self.filtro_operadora = ttk.Combobox(filtro_frame, values=[''] + OPERADORAS, 
                                            style='Modern.TCombobox', width=22, 
                                            font=('Segoe UI', 10), state='readonly')
        self.filtro_operadora.set('')
        self.filtro_operadora.pack(side=tk.LEFT, padx=(0, 20), ipady=6)
        
        tk.Label(filtro_frame, text="Status:", font=('Segoe UI', 10, 'bold'), 
                bg=COR_CARD, fg=COR_TEXTO).pack(side=tk.LEFT, padx=(0, 10))
        self.filtro_status = ttk.Combobox(filtro_frame, values=['', 'Disponível', 'Retirado'], 
                                         style='Modern.TCombobox', width=18, 
                                         font=('Segoe UI', 10), state='readonly')
        self.filtro_status.set('')
        self.filtro_status.pack(side=tk.LEFT, padx=(0, 20), ipady=6)
        
        btn_aplicar = ModernButton(filtro_frame, "🔍 Aplicar", self.atualizar_consulta,
                                   width=120, height=35, bg_color=COR_PRIMARIA, hover_color=COR_SECUNDARIA,
                                   font=('Segoe UI', 10, 'bold'))
        btn_aplicar.pack(side=tk.LEFT, padx=5)
        
        btn_exportar = ModernButton(filtro_frame, "📥 Exportar CSV", self.exportar_csv,
                                    width=140, height=35, bg_color=COR_ACCENT, hover_color='#0891b2',
                                    font=('Segoe UI', 10, 'bold'))
        btn_exportar.pack(side=tk.LEFT, padx=5)
        
        # Card de resultados
        resultado_card = CardFrame(main_container, bg=COR_CARD)
        resultado_card.pack(fill=tk.BOTH, expand=True)
        
        resultado_inner = resultado_card.inner_frame
        
        # Treeview
        tree_frame = tk.Frame(resultado_inner, bg=COR_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        columns = ('ICCID', 'Operadora', 'Status', 'Data Entrada', 'Data Saída', 'Retirado Por')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=22, style='Modern.Treeview')
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=180, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.atualizar_consulta()
    
    def criar_aba_remessas(self):
        """Cria a aba de remessas"""
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📋 Remessas")
        
        # Container principal
        main_container = tk.Frame(frame, bg=COR_FUNDO)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Card
        card = CardFrame(main_container, bg=COR_CARD)
        card.pack(fill=tk.BOTH, expand=True)
        
        inner = card.inner_frame
        
        title_frame = tk.Frame(inner, bg=COR_CARD)
        title_frame.pack(pady=(20, 15), padx=20, fill=tk.X)
        
        tk.Label(title_frame, text="📋 Histórico de Remessas", 
                font=('Segoe UI', 16, 'bold'), bg=COR_CARD, fg=COR_TEXTO).pack(side=tk.LEFT)
        
        btn_frame = tk.Frame(title_frame, bg=COR_CARD)
        btn_frame.pack(side=tk.RIGHT)
        
        btn_visualizar = ModernButton(btn_frame, "👁️ Visualizar", self.visualizar_remessa,
                                     width=130, height=35, bg_color=COR_ACCENT, hover_color='#0891b2',
                                     font=('Segoe UI', 10, 'bold'))
        btn_visualizar.pack(side=tk.LEFT, padx=5)
        
        btn_excluir = ModernButton(btn_frame, "🗑️ Excluir", self.excluir_remessa_selecionada,
                                   width=130, height=35, bg_color=COR_ERRO, hover_color='#dc2626',
                                   font=('Segoe UI', 10, 'bold'))
        btn_excluir.pack(side=tk.LEFT, padx=5)
        
        btn_atualizar = ModernButton(btn_frame, "🔄 Atualizar", self.atualizar_remessas,
                                     width=130, height=35, bg_color=COR_PRIMARIA, hover_color=COR_SECUNDARIA,
                                     font=('Segoe UI', 10, 'bold'))
        btn_atualizar.pack(side=tk.LEFT, padx=5)
        
        # Treeview
        tree_frame = tk.Frame(inner, bg=COR_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        columns = ('ID', 'Número Remessa', 'Data', 'Operadora', 'Quantidade', 'Observações')
        self.remessas_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=24, style='Modern.Treeview')
        
        for col in columns:
            self.remessas_tree.heading(col, text=col)
            self.remessas_tree.column(col, width=150, anchor=tk.CENTER)
        
        self.remessas_tree.column('Observações', width=250)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.remessas_tree.yview)
        self.remessas_tree.configure(yscrollcommand=scrollbar.set)
        
        self.remessas_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind duplo clique para visualizar
        self.remessas_tree.bind('<Double-1>', lambda e: self.visualizar_remessa())
        
        self.atualizar_remessas()
    
    def criar_aba_estatisticas(self):
        """Cria a aba de estatísticas"""
        frame = tk.Frame(self.notebook, bg=COR_FUNDO)
        self.notebook.add(frame, text="📊 Estatísticas")
        
        # Container principal
        main_container = tk.Frame(frame, bg=COR_FUNDO)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=40)
        
        # Título
        title_frame = tk.Frame(main_container, bg=COR_FUNDO)
        title_frame.pack(pady=(0, 40))
        
        tk.Label(title_frame, text="📊 Estatísticas do Sistema", 
                font=('Segoe UI', 22, 'bold'), bg=COR_FUNDO, fg=COR_TEXTO).pack()
        tk.Label(title_frame, text="Visão geral do sistema de monitoramento", 
                font=('Segoe UI', 11), bg=COR_FUNDO, fg=COR_TEXTO_SECUNDARIO).pack(pady=(8, 0))
        
        # Cards de estatísticas
        stats_container = tk.Frame(main_container, bg=COR_FUNDO)
        stats_container.pack()
        
        self.stats_labels = {}
        
        stats_config = [
            ('📱', 'Total de Chips', 'total', COR_PRIMARIA),
            ('✅', 'Chips Disponíveis', 'disponiveis', COR_SUCESSO),
            ('📤', 'Chips Retirados', 'retirados', COR_ERRO),
            ('📦', 'Total de Remessas', 'total_remessas', COR_ACCENT)
        ]
        
        for i, (icon, label, key, color) in enumerate(stats_config):
            card = CardFrame(stats_container, bg=COR_CARD)
            card.pack(side=tk.LEFT, padx=15, fill=tk.BOTH, expand=True)
            inner = card.inner_frame
            
            # Ícone e valor
            icon_label = tk.Label(inner, text=icon, font=('Segoe UI', 40), bg=COR_CARD, fg=color)
            icon_label.pack(pady=(25, 10))
            
            value_label = tk.Label(inner, text="0", font=('Segoe UI', 32, 'bold'), 
                                  bg=COR_CARD, fg=COR_TEXTO)
            value_label.pack(pady=(0, 5))
            self.stats_labels[key] = value_label
            
            tk.Label(inner, text=label, font=('Segoe UI', 11, 'bold'), 
                    bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO).pack(pady=(0, 25))
            
            # Barra decorativa
            bar = tk.Frame(inner, bg=color, height=4)
            bar.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Botão atualizar
        btn_frame = tk.Frame(main_container, bg=COR_FUNDO)
        btn_frame.pack(pady=40)
        
        btn_atualizar = ModernButton(btn_frame, "🔄 Atualizar Estatísticas", 
                                     self.atualizar_estatisticas,
                                     width=220, height=45, bg_color=COR_PRIMARIA, 
                                     hover_color=COR_SECUNDARIA,
                                     font=('Segoe UI', 11, 'bold'))
        btn_atualizar.pack()
        
        self.atualizar_estatisticas()
    
    # Métodos de funcionalidade
    
    def cadastrar_chip_individual(self):
        """Cadastra um chip individual"""
        iccid = self.iccid_entry.get().strip()
        operadora = self.operadora_combo.get()
        observacoes = self.obs_text.get('1.0', tk.END).strip()
        
        if not iccid:
            messagebox.showerror("Erro", "ICCID é obrigatório!")
            return
        
        if not operadora:
            messagebox.showerror("Erro", "Operadora é obrigatória!")
            return
        
        if self.db.adicionar_chip(iccid, operadora, None, observacoes):
            self.status_label.config(text=f"✓ Chip {iccid} cadastrado com sucesso!", foreground=COR_SUCESSO)
            self.iccid_entry.delete(0, tk.END)
            self.operadora_combo.set('')
            self.obs_text.delete('1.0', tk.END)
            # Limpar mensagem após 3 segundos
            self.root.after(3000, lambda: self.status_label.config(text=""))
        else:
            messagebox.showerror("Erro", f"ICCID {iccid} já está cadastrado!")
            self.status_label.config(text="")
    
    def importar_arquivo(self):
        """Importa chips de um arquivo CSV ou XLSX"""
        from tkinter import filedialog
        
        filetypes = [("CSV files", "*.csv"), ("Excel files", "*.xlsx")]
        if not XLSX_AVAILABLE:
            filetypes = [("CSV files", "*.csv")]
        filetypes.append(("All files", "*.*"))
        
        arquivo = filedialog.askopenfilename(
            title="Selecionar arquivo CSV ou XLSX",
            filetypes=filetypes
        )
        
        if not arquivo:
            return
        
        try:
            linhas = []
            
            # Verificar extensão do arquivo
            if arquivo.lower().endswith('.xlsx'):
                if not XLSX_AVAILABLE:
                    messagebox.showerror("Erro", 
                        "Biblioteca openpyxl não está instalada!\n\n"
                        "Para importar arquivos XLSX, instale com:\n"
                        "pip install openpyxl")
                    return
                
                # Importar XLSX
                wb = openpyxl.load_workbook(arquivo)
                ws = wb.active
                
                for row in ws.iter_rows(min_row=1, values_only=True):
                    if row and row[0]:
                        iccid = str(row[0]).strip()
                        # Pular cabeçalho
                        if iccid.lower() in ['iccid', 'iccid ']:
                            continue
                        # Verificar se tem operadora na coluna B
                        if len(row) >= 2 and row[1]:
                            operadora = str(row[1]).strip()
                            if operadora.lower() not in ['operadora', 'operadora '] and operadora:
                                linhas.append(f"{iccid},{operadora}")
                            elif iccid:  # Apenas ICCID, sem operadora
                                linhas.append(f"{iccid},")
                        elif iccid:  # Apenas ICCID, sem coluna B
                            linhas.append(f"{iccid},")
            
            else:
                # Importar CSV
                with open(arquivo, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and len(row) > 0 and row[0].strip():
                            iccid = row[0].strip()
                            # Pular cabeçalho
                            if iccid.lower() in ['iccid', 'iccid ']:
                                continue
                            # Verificar se tem operadora na coluna B
                            if len(row) >= 2 and row[1].strip():
                                operadora = row[1].strip()
                                if operadora.lower() not in ['operadora', 'operadora '] and operadora:
                                    linhas.append(f"{iccid},{operadora}")
                                else:
                                    linhas.append(f"{iccid},")
                            else:  # Apenas ICCID
                                linhas.append(f"{iccid},")
            
            if linhas:
                self.chips_text.insert('1.0', '\n'.join(linhas))
                messagebox.showinfo("Sucesso", f"✓ {len(linhas)} linhas importadas com sucesso!")
            else:
                messagebox.showwarning("Aviso", "Nenhum dado válido encontrado no arquivo!")
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao importar arquivo: {str(e)}")
    
    def atualizar_numero_remessa(self):
        """Atualiza o número de remessa gerado automaticamente"""
        numero = self.db.gerar_numero_remessa()
        self.num_remessa_entry.config(state='normal')
        self.num_remessa_entry.delete(0, tk.END)
        self.num_remessa_entry.insert(0, numero)
        self.num_remessa_entry.config(state='readonly')
    
    def cadastrar_lote(self):
        """Cadastra chips em lote"""
        operadora_remessa = self.remessa_operadora_combo.get()
        obs_remessa = self.remessa_obs_text.get('1.0', tk.END).strip()
        chips_text = self.chips_text.get('1.0', tk.END).strip()
        
        if not chips_text:
            messagebox.showerror("Erro", "Lista de chips está vazia!")
            return
        
        # Processar chips
        linhas = [linha.strip() for linha in chips_text.split('\n') if linha.strip()]
        chips = []
        operadora_padrao = operadora_remessa if operadora_remessa in OPERADORAS else None
        
        for linha in linhas:
            partes = [p.strip() for p in linha.split(',')]
            if len(partes) >= 1 and partes[0]:  # Pelo menos tem ICCID
                iccid = partes[0]
                
                # Se tem operadora na linha, usar ela
                if len(partes) >= 2 and partes[1] and partes[1] in OPERADORAS:
                    operadora = partes[1]
                    chips.append((iccid, operadora))
                # Se não tem operadora na linha, usar a operadora da remessa
                elif operadora_padrao:
                    chips.append((iccid, operadora_padrao))
                # Se não tem operadora nem na linha nem na remessa, ignorar
                else:
                    continue
        
        if not chips:
            if not operadora_padrao:
                messagebox.showerror("Erro", 
                    "Nenhum chip válido encontrado!\n\n"
                    "Se os chips não tiverem operadora, selecione uma operadora na remessa.")
            else:
                messagebox.showerror("Erro", "Nenhum chip válido encontrado!")
            return
        
        # Criar remessa com número gerado automaticamente
        remessa_id, numero_remessa = self.db.criar_remessa(None, operadora_remessa or '', len(chips), obs_remessa)
        
        if remessa_id is None:
            messagebox.showerror("Erro", "Erro ao criar remessa! Tente novamente.")
            return
        
        # Adicionar chips
        sucesso, falhas = self.db.adicionar_chips_lote(chips, remessa_id)
        
        mensagem = f"✓ Remessa {numero_remessa} criada com sucesso!\n"
        mensagem += f"✓ {sucesso} chips cadastrados"
        if falhas:
            mensagem += f"\n⚠ {len(falhas)} chips já existentes"
        
        self.lote_status_label.config(text=mensagem, foreground=COR_SUCESSO)
        self.limpar_lote()
        # Gerar novo número para próxima remessa
        self.atualizar_numero_remessa()
    
    def limpar_lote(self):
        """Limpa os campos do cadastro em lote"""
        self.remessa_operadora_combo.set('')
        self.remessa_obs_text.delete('1.0', tk.END)
        self.chips_text.delete('1.0', tk.END)
        # Não limpa número de remessa - ele é gerado automaticamente
    
    def buscar_chip_retirada(self, event=None):
        """Busca informações do chip ao digitar ICCID"""
        iccid = self.retirada_iccid_entry.get().strip()
        if not iccid:
            self.chip_info_label.config(text="Digite o ICCID para buscar informações", 
                                       foreground=COR_TEXTO_SECUNDARIO)
            return
        
        resultado = self.db.buscar_chip(iccid)
        if resultado:
            _, iccid_db, operadora, status, data_entrada, data_saida, retirado_por, obs = resultado
            info = f"ICCID: {iccid_db}\nOperadora: {operadora}\nStatus: {status}\nData Entrada: {data_entrada}"
            if data_saida:
                info += f"\nData Saída: {data_saida}\nRetirado por: {retirado_por}"
            self.chip_info_label.config(text=info, foreground=COR_TEXTO)
        else:
            self.chip_info_label.config(text=f"❌ Chip {iccid} não encontrado!", foreground=COR_ERRO)
    
    def retirar_chip(self):
        """Registra a retirada de um chip"""
        iccid = self.retirada_iccid_entry.get().strip()
        retirado_por = self.retirado_por_entry.get().strip()
        
        if not iccid:
            messagebox.showerror("Erro", "ICCID é obrigatório!")
            return
        
        if not retirado_por:
            messagebox.showerror("Erro", "Nome de quem retirou é obrigatório!")
            return
        
        if self.db.retirar_chip(iccid, retirado_por):
            self.retirada_status_label.config(text=f"✓ Chip {iccid} retirado com sucesso por {retirado_por}!", foreground=COR_SUCESSO)
            self.retirada_iccid_entry.delete(0, tk.END)
            self.retirado_por_entry.delete(0, tk.END)
            self.chip_info_label.config(text="Digite o ICCID para buscar informações", 
                                       foreground=COR_TEXTO_SECUNDARIO)
            self.root.after(5000, lambda: self.retirada_status_label.config(text=""))
        else:
            self.retirada_status_label.config(text=f"❌ Chip {iccid} não encontrado ou já foi retirado!", foreground=COR_ERRO)
            self.root.after(5000, lambda: self.retirada_status_label.config(text=""))
    
    def atualizar_consulta(self):
        """Atualiza a lista de chips"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        filtro_op = self.filtro_operadora.get() if self.filtro_operadora.get() else None
        filtro_st = self.filtro_status.get() if self.filtro_status.get() else None
        
        chips = self.db.listar_chips(filtro_op, filtro_st)
        
        for chip in chips:
            _, iccid, operadora, status, data_entrada, data_saida, retirado_por = chip
            self.tree.insert('', tk.END, values=(
                iccid,
                operadora,
                status,
                data_entrada,
                data_saida or '',
                retirado_por or ''
            ))
    
    def exportar_csv(self):
        """Exporta a consulta para CSV"""
        from tkinter import filedialog
        arquivo = filedialog.asksaveasfilename(
            title="Salvar como CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not arquivo:
            return
        
        try:
            filtro_op = self.filtro_operadora.get() if self.filtro_operadora.get() else None
            filtro_st = self.filtro_status.get() if self.filtro_status.get() else None
            chips = self.db.listar_chips(filtro_op, filtro_st)
            
            with open(arquivo, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ICCID', 'Operadora', 'Status', 'Data Entrada', 'Data Saída', 'Retirado Por'])
                for chip in chips:
                    _, iccid, operadora, status, data_entrada, data_saida, retirado_por = chip
                    writer.writerow([iccid, operadora, status, data_entrada, data_saida or '', retirado_por or ''])
            
            messagebox.showinfo("Sucesso", f"✓ Dados exportados para {arquivo}!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    def atualizar_remessas(self):
        """Atualiza a lista de remessas"""
        for item in self.remessas_tree.get_children():
            self.remessas_tree.delete(item)
        
        remessas = self.db.listar_remessas()
        
        for remessa in remessas:
            id_rem, num_rem, data_rem, operadora, quantidade, obs = remessa
            self.remessas_tree.insert('', tk.END, values=(
                id_rem,
                num_rem,
                data_rem,
                operadora or '',
                quantidade,
                obs or ''
            ), tags=(id_rem,))
    
    def visualizar_remessa(self):
        """Visualiza os chips de uma remessa selecionada"""
        selecionado = self.remessas_tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma remessa para visualizar!")
            return
        
        item = selecionado[0]
        values = self.remessas_tree.item(item, 'values')
        if not values:
            return
        
        remessa_id = int(values[0])
        
        # Buscar informações da remessa
        remessa_info = self.db.buscar_remessa_por_id(remessa_id)
        if not remessa_info:
            messagebox.showerror("Erro", "Remessa não encontrada!")
            return
        
        _, num_rem, data_rem, operadora, quantidade, obs = remessa_info
        
        # Buscar chips da remessa
        chips = self.db.buscar_chips_remessa(remessa_id)
        
        # Criar janela de visualização
        janela = tk.Toplevel(self.root)
        janela.title(f"Visualizar Remessa: {num_rem}")
        janela.geometry("900x650")
        janela.configure(bg=COR_FUNDO)
        janela.transient(self.root)
        janela.grab_set()
        
        # Header
        header = tk.Frame(janela, bg=COR_PRIMARIA, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        info_frame = tk.Frame(header, bg=COR_PRIMARIA)
        info_frame.pack(padx=20, pady=15)
        
        tk.Label(info_frame, text=f"📦 Remessa: {num_rem}", 
                font=('Segoe UI', 16, 'bold'), bg=COR_PRIMARIA, fg='white').pack(anchor=tk.W)
        tk.Label(info_frame, text=f"Data: {data_rem} | Operadora: {operadora or 'N/A'} | Quantidade: {quantidade}", 
                font=('Segoe UI', 10), bg=COR_PRIMARIA, fg='#c7d2fe').pack(anchor=tk.W, pady=(5, 0))
        if obs:
            tk.Label(info_frame, text=f"Observações: {obs}", 
                    font=('Segoe UI', 9), bg=COR_PRIMARIA, fg='#c7d2fe').pack(anchor=tk.W, pady=(2, 0))
        
        # Container principal
        main_frame = tk.Frame(janela, bg=COR_FUNDO)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Card
        card = CardFrame(main_frame, bg=COR_CARD)
        card.pack(fill=tk.BOTH, expand=True)
        
        inner = card.inner_frame
        
        tk.Label(inner, text=f"📱 Chips da Remessa ({len(chips)} chips)", 
                font=('Segoe UI', 14, 'bold'), bg=COR_CARD, fg=COR_TEXTO).pack(pady=(20, 15), padx=20, anchor=tk.W)
        
        # Treeview
        tree_frame = tk.Frame(inner, bg=COR_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        columns = ('ICCID', 'Operadora', 'Status', 'Data Entrada', 'Data Saída', 'Retirado Por')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=20, style='Modern.Treeview')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=140, anchor=tk.CENTER)
        
        tree.column('ICCID', width=180)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Popular treeview
        for chip in chips:
            _, iccid, operadora_chip, status, data_entrada, data_saida, retirado_por = chip
            tree.insert('', tk.END, values=(
                iccid,
                operadora_chip,
                status,
                data_entrada,
                data_saida or '',
                retirado_por or ''
            ))
        
        # Botão fechar
        btn_frame = tk.Frame(inner, bg=COR_CARD)
        btn_frame.pack(pady=(0, 20))
        
        btn_fechar = ModernButton(btn_frame, "✕ Fechar", janela.destroy,
                                  width=150, height=40, bg_color=COR_TEXTO_SECUNDARIO, 
                                  hover_color='#475569', font=('Segoe UI', 10, 'bold'))
        btn_fechar.pack()
    
    def excluir_remessa_selecionada(self):
        """Exclui a remessa selecionada"""
        selecionado = self.remessas_tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma remessa para excluir!")
            return
        
        item = selecionado[0]
        values = self.remessas_tree.item(item, 'values')
        if not values:
            return
        
        remessa_id = int(values[0])
        num_rem = values[1]
        
        # Confirmar exclusão
        resposta = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja realmente excluir a remessa {num_rem}?",
            icon='warning'
        )
        
        if not resposta:
            return
        
        # Perguntar se deseja excluir chips também
        excluir_chips = messagebox.askyesno(
            "Excluir Chips",
            "Deseja excluir também os chips relacionados a esta remessa?\n\n"
            "SIM = Exclui remessa e todos os chips\n"
            "NÃO = Exclui apenas a remessa (chips permanecem no sistema)"
        )
        
        # Executar exclusão
        sucesso = self.db.excluir_remessa(remessa_id, excluir_chips)
        
        if sucesso:
            if excluir_chips:
                messagebox.showinfo("Sucesso", f"Remessa {num_rem} e seus chips foram excluídos com sucesso!")
            else:
                messagebox.showinfo("Sucesso", f"Remessa {num_rem} foi excluída. Os chips permanecem no sistema.")
            self.atualizar_remessas()
        else:
            messagebox.showerror("Erro", "Erro ao excluir remessa!")
    
    def atualizar_estatisticas(self):
        """Atualiza as estatísticas com animação"""
        stats = self.db.estatisticas()
        
        def animate_value(label, target, current=0, step=1):
            if current < target:
                label.config(text=str(current))
                self.root.after(20, lambda: animate_value(label, target, current + step, step))
            else:
                label.config(text=str(target))
        
        for key, label in self.stats_labels.items():
            target_value = stats.get(key, 0)
            current_value = int(label.cget('text') or 0)
            if target_value > current_value:
                step = max(1, (target_value - current_value) // 20)
                animate_value(label, target_value, current_value, step)
            else:
                label.config(text=str(target_value))


def main():
    root = tk.Tk()
    app = MonitoramentoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
