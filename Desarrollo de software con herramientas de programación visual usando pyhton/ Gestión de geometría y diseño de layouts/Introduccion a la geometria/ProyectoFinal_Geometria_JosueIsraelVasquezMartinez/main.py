import tkinter as tk
from tkinter import ttk


class BookstorePOS(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SaaS BookStore POS - Arquitectura de Layout")
        self.geometry("950x650")
        self.minsize(900, 600)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        # --- CONFIGURACIÓN DE LA RAÍZ CON GRID UNIFICADO ---
        # Fila 0: Header (Altura fija)
        self.rowconfigure(0, weight=0)
        # Fila 1: Workspace y Sidebar (Se expande verticalmente)
        self.rowconfigure(1, weight=1)
        # Fila 2: Status Bar (Altura fija)
        self.rowconfigure(2, weight=0)

        # Columna 0: Sidebar (Ancho fijo)
        self.columnconfigure(0, weight=0, minsize=180)
        # Columna 1: Workspace (Se expande horizontalmente)
        self.columnconfigure(1, weight=1)

        self._create_layout_containers()

    def _create_layout_containers(self) -> None:
        """Inicializa y posiciona los contenedores maestros de la UI."""

        # 1. HEADER (Usa grid ocupando ambas columnas)
        self.header_frame = tk.Frame(self, bg="#2C3E50", height=60)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header_frame.pack_propagate(False)  # Conserva su altura

        # 2. SIDEBAR (Usa grid en la columna 0, fila 1. Altura completa vertical)
        self.sidebar_frame = tk.Frame(self, bg="#34495E", width=180)
        self.sidebar_frame.grid(row=1, column=0, sticky="ns")
        self.sidebar_frame.pack_propagate(False)

        # 3. WORKSPACE (Usa grid en la columna 1, fila 1. Se expande en todas direcciones)
        self.workspace_frame = tk.Frame(self, bg="#ECF0F1")
        self.workspace_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

        # Configuramos la cuadrícula interna del Workspace (50% a cada panel hijo)
        self.workspace_frame.columnconfigure(0, weight=1)  # Catálogo
        self.workspace_frame.columnconfigure(1, weight=1)  # Carrito de Compras
        self.workspace_frame.rowconfigure(0, weight=1)

        # 4. STATUS BAR (Usa grid en la fila 2, ocupando ambas columnas)
        self.status_frame = tk.Frame(self, bg="#BDC3C7", height=40)
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.status_frame.pack_propagate(False)

        # 5. FLOATING ALERT (Usa place. Es seguro porque place ignora la negociación de grid)
        self.floating_alert = tk.Frame(self, bg="#E74C3C", width=220, height=50)
        self.floating_alert.place(relx=0.98, rely=0.92, anchor="se")

        # --- AGREGAR CONTENIDO Y COMPORTAMIENTO INTERNO ---
        # En el Header
        tk.Label(
            self.header_frame,
            text="SISTEMA POS LIBRERÍA - VISTA NORTE",
            fg="white",
            bg="#2C3E50",
            font=("Arial", 12, "bold")
        ).pack(pady=15)

        # En el Sidebar (Aquí usamos PACK de forma segura, porque el contenedor es el sidebar)
        tk.Label(self.sidebar_frame, text="CATEGORÍAS", fg="white", bg="#34495E", font=("Arial", 10, "bold")).pack(
            pady=15)

        # Botones de categorías simulados
        self.btn_ficcion = ttk.Button(self.sidebar_frame, text="Ficción")
        self.btn_ficcion.pack(fill=tk.X, padx=10, pady=5)

        self.btn_tecnicos = ttk.Button(self.sidebar_frame, text="Técnicos")
        self.btn_tecnicos.pack(fill=tk.X, padx=10, pady=5)

        self.btn_historicos = ttk.Button(self.sidebar_frame, text="Históricos")
        self.btn_historicos.pack(fill=tk.X, padx=10, pady=5)

        # Texto dentro de la alerta flotante
        tk.Label(
            self.floating_alert,
            text="¡10% Descuento Aplicado!",
            fg="white",
            bg="#E74C3C",
            font=("Arial", 10, "bold")
        ).pack(expand=True)


if __name__ == "__main__":
    app = BookstorePOS()
    app.mainloop()