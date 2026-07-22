import tkinter as tk
from tkinter import ttk
from typing import Final

# PALETA DE COLORES PROFESIONAL (Tema Oscuro/Cyber)
COLOR_BG: Final[str] = "#0F172A"  # Fondo pizarra oscuro
COLOR_CARD: Final[str] = "#1E293B"  # Fondo de tarjetas
COLOR_ACCENT: Final[str] = "#3B82F6"  # Azul de destaque
COLOR_TEXT: Final[str] = "#F8FAFC"  # Blanco/Gris claro
COLOR_GREEN: Final[str] = "#10B981"  # Estado correcto


class ServerMonitorDashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DataCenter OS - Grid Monitor")
        self.geometry("1024x700")
        self.minsize(900, 600)
        self.configure(bg=COLOR_BG)

        # Configurar estilos de TTK para adaptarlos al tema oscuro
        self._setup_styles()

        # --- CONFIGURACIÓN DE RESPONSIVIDAD DE LA RAÍZ ---
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Frame contenedor maestro para aplicar márgenes generales limpios
        self.main_container = tk.Frame(self, bg=COLOR_BG)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        # Configurar la matriz 4x3 del contenedor principal
        self._configure_grid_matrix()
        self._build_components()

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Helvetica", 10), background=COLOR_CARD, foreground=COLOR_TEXT)
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), background=COLOR_BG, foreground=COLOR_TEXT)

    def _configure_grid_matrix(self) -> None:
        # 4 Columnas idénticas (uniformidad)
        for col in range(4):
            self.main_container.columnconfigure(col, weight=1, uniform="main_cols")

        # 3 Filas con comportamiento dinámico diferenciado
        self.main_container.rowconfigure(0, weight=0)  # Header: No se estira verticalmente
        self.main_container.rowconfigure(1, weight=1)  # KPIs: Expansión moderada
        self.main_container.rowconfigure(2, weight=2)  # Logs y Controles: Ocupan la mayor parte del espacio vertical

    def _build_components(self) -> None:
        # Fila 0: Header (Ocupa las 4 columnas)
        self.header_frame = tk.Frame(self.main_container, bg=COLOR_BG)
        self.header_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 15))

        lbl_system = ttk.Label(self.header_frame, text="SISTEMA DE MONITOREO CORE - DATACENTER GUADALAJARA",
                               style="Header.TLabel")
        lbl_system.pack(side=tk.LEFT)

        lbl_status = tk.Label(self.header_frame, text="GLOBAL STATUS: ONLINE", fg=COLOR_GREEN, bg=COLOR_BG,
                              font=("Helvetica", 10, "bold"))
        lbl_status.pack(side=tk.RIGHT)

        # Fila 1: Inicialización de los 4 KPIs
        self.kpi_frames: list[tk.Frame] = []
        kpi_names = ["CPU UTILIZATION", "MEMORY USAGE", "DISK I/O", "NETWORK TRAFFIC"]

        for idx, name in enumerate(kpi_names):
            # Crear cada tarjeta
            kpi_card = tk.Frame(self.main_container, bg=COLOR_CARD, bd=1, relief="solid")
            # Colocación matemática directa usando el índice del bucle
            kpi_card.grid(row=1, column=idx, sticky="nsew", padx=5, pady=5)

            # Asegurar responsividad interna de la tarjeta
            kpi_card.columnconfigure(0, weight=1)
            kpi_card.rowconfigure(1, weight=1)

            # Etiqueta interna de la tarjeta
            lbl_name = tk.Label(kpi_card, text=name, fg=COLOR_TEXT, bg=COLOR_CARD, font=("Helvetica", 9, "bold"))
            lbl_name.grid(row=0, column=0, sticky="w", padx=10, pady=5)

            self.kpi_frames.append(kpi_card)

        # TODO (Tu Desafío de Réplica - Fila 2):
        # 1. Crear el Panel de Logs ('self.logs_frame') en la Fila 2, Columna 0 con columnspan=3.
        # 2. Crear el Panel de Controles ('self.controls_frame') en la Fila 2, Columna 3 con columnspan=1.


if __name__ == "__main__":
    app = ServerMonitorDashboard()
    app.mainloop()