import tkinter as tk
from tkinter import ttk
from typing import Final

# CONSTANTES DE DISEÑO (Clean Code - Estilo Staff Engineer)
BG_MAIN: Final[str] = "#0a0f12"  # Fondo Cyberpunk Oscuro
BG_PANEL: Final[str] = "#141f24"  # Fondo de Paneles
ACCENT_GREEN: Final[str] = "#00ff66"  # Color de acento
ACCENT_RED: Final[str] = "#ff3333"  # Color de alertas


class CyberDashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CENTRO DE MANDO - RECONSTRUCCIÓN DE PIXELES")
        self.geometry("1024x768")
        self.minsize(900, 600)
        self.configure(bg=BG_MAIN)

        # Simular grilla de fondo para visualización de posicionamiento
        self._draw_background_grid()
        self._init_layout_panels()

    def _draw_background_grid(self) -> None:
        """Crea líneas o marcas sutiles de fondo para validar alineación."""
        canvas = tk.Canvas(self, bg=BG_MAIN, highlightthickness=0)
        canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # Dibujar líneas de referencia cada 100px para depuración del maquetador
        for i in range(100, 2000, 100):
            # Líneas verticales
            canvas.create_line(i, 0, i, 2000, fill="#1a262c", width=1)
            # Líneas horizontales
            canvas.create_line(0, i, 2000, i, fill="#1a262c", width=1)

    def _init_layout_panels(self) -> None:
        """Instancia los paneles principales utilizando posicionamiento absoluto."""

        # 1. PANEL DE MONITOREO (Izquierda)
        self.left_panel = tk.Frame(self, bg=BG_PANEL, bd=2, relief="groove")
        self.left_panel.place(x=20, y=20, relwidth=0.25, relheight=0.90)

        # Agregar indicador visual de título al panel
        lbl_mon = tk.Label(self.left_panel, text="SISTEMAS MONITOREADOS", fg=ACCENT_GREEN, bg=BG_PANEL,
                           font=("Courier", 10, "bold"))
        lbl_mon.place(x=10, y=10)

        # 2. CONSOLA CENTRAL (Perfectamente centrada)
        self.center_console = tk.Frame(self, bg=BG_PANEL, bd=2, relief="sunken")
        self.center_console.place(relx=0.5, rely=0.5, relwidth=0.42, relheight=0.70, anchor="center")

        lbl_con = tk.Label(self.center_console, text="CONSOLA CRÍTICA NÚCLEO", fg=ACCENT_RED, bg=BG_PANEL,
                           font=("Courier", 12, "bold"))
        lbl_con.place(relx=0.5, rely=0.05, anchor="center")

        # TODO (Paso 2): Implementar el Panel de la Derecha aquí.

        # TODO (Paso 2): Implementar la Barra de Estado inferior aquí.


if __name__ == "__main__":
    app = CyberDashboard()
    app.mainloop()