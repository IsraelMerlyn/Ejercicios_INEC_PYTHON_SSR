import tkinter as tk
from tkinter import ttk
from typing import Final

# CONSTANTES DE DISEÑO (Simulando un tema profesional de brigada)
COLOR_HEADER: Final[str] = "#1F2937"  # Gris muy oscuro
COLOR_SIDEBAR: Final[str] = "#374151"  # Gris medio
COLOR_CONTENT: Final[str] = "#F3F4F6"  # Gris claro (área de trabajo)
COLOR_FOOTER: Final[str] = "#111827"  # Negro/Gris profundo


class TerritorialDashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Brigadas Territoriales Guadalajara - Centro de Mando")
        self.geometry("1024x768")
        self.minsize(900, 600)

        self._init_layout()

    def _init_layout(self) -> None:
        # Contenedor raíz unificado para evitar colocar elementos sueltos en el root
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. HEADER (Línea superior de control, fill=X para ocupar todo el ancho)
        header_frame = tk.Frame(main_container, bg=COLOR_HEADER, height=60)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        header_frame.pack_propagate(False)  # Forzar a que respete la altura fija definida

        # Título del Header
        lbl_title = tk.Label(
            header_frame,
            text="GOBIERNO DE GUADALAJARA - OPERACIONES TERRITORIALES",
            fg="white",
            bg=COLOR_HEADER,
            font=("Helvetica", 12, "bold")
        )
        # Relleno interno (padding) para centrar visualmente dentro del header
        lbl_title.pack(side=tk.LEFT, padx=15, pady=15)

        # 2. FOOTER (Usa side=BOTTOM)
        footer_frame = tk.Frame(main_container, bg=COLOR_FOOTER, height=30)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)

        lbl_status = tk.Label(
            footer_frame,
            text="Estado: Conectado a Servidor Central Jalisco | Brigadas Activas: 14",
            fg="#10B981",
            bg=COLOR_FOOTER,
            font=("Helvetica", 9)
        )
        lbl_status.pack(side=tk.LEFT, padx=10, pady=5)

        # 3. BODY (Espacio intermedio que contiene Sidebar y Área de Trabajo)
        # Debe usar fill=BOTH y expand=True para consumir todo el espacio vertical disponible entre Header y Footer
        body_frame = tk.Frame(main_container, bg="#FFFFFF")
        body_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 4. SIDEBAR (Izquierda, acoplada al Body, ancho fijo de 200px)
        sidebar_frame = tk.Frame(body_frame, bg=COLOR_SIDEBAR, width=200)
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        sidebar_frame.pack_propagate(False)

        # Botones de navegación en la Barra Lateral
        tk.Label(sidebar_frame, text="BRIGADAS", fg="white", bg=COLOR_SIDEBAR, font=("Helvetica", 10, "bold")).pack(
            pady=15)

        for i in range(1, 4):
            btn = ttk.Button(sidebar_frame, text=f"Zona {i} - Guadalajara")
            # padding externo para simular márgenes limpios
            btn.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # 5. CONTENT AREA (Derecha, consume el espacio restante del Body)
        # NOTA: Al empaquetarlo con side=RIGHT, fill=BOTH y expand=True, empuja y reclama la cavidad restante
        content_frame = tk.Frame(body_frame, bg=COLOR_CONTENT)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Sub-anidamiento dentro del Área de Contenido
        # A: Zona superior de simulación de mapa (se expande por completo)
        self.map_placeholder = tk.Frame(content_frame, bg="#D1D5DB")
        self.map_placeholder.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        lbl_map_info = tk.Label(self.map_placeholder, text="VISTA DE MAPA VECTORIAL (OPENSTREETMAP INTERFACES)",
                                fg="#4B5563", bg="#D1D5DB", font=("Helvetica", 11, "italic"))
        lbl_map_info.pack(expand=True)

        # TODO (Tu Desafío de Réplica): Implementar aquí abajo el panel de estadísticas 'stats_panel_frame'
        # Debe tener una altura fija de 150px, fondo oscuro o contrastante y acoplarse al BOTTOM del content_frame.


if __name__ == "__main__":
    app = TerritorialDashboard()
    app.mainloop()