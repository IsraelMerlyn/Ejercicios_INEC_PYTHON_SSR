"""
LogiTrack -- Capa de Vista (SOLO interfaz, sin logica de negocio).
======================================================================

Regla de oro: esta clase nunca decide NADA por su cuenta. Cada accion del
usuario (clic, texto ingresado) se delega a self.controller. La vista
solo sabe dibujar widgets y refrescar lo que el controller le indique.
"""

import tkinter as tk
from tkinter import messagebox


class NotaView:
    """Interfaz de la bitacora de incidencias. self.controller se asigna
    despues de crear el NotaController (ver controller.py)."""

    def __init__(self, master: tk.Tk):
        self.master = master
        self.controller = None  # lo asigna NotaController al construirse
        self._construir_ui()

    def _construir_ui(self):
        """Arma los widgets: Entry, boton 'Agregar', Listbox, boton 'Resolver'.

        # TODO:
        # 1. self.entrada = tk.Entry(self.master, width=40); pack.
        # 2. self.btn_agregar = tk.Button(self.master, text='Agregar',
        #    command=self._click_agregar); pack.
        # 3. self.lista = tk.Listbox(self.master, width=50, height=10); pack.
        # 4. self.btn_resolver = tk.Button(self.master, text='Marcar
        #    resuelta', command=self._click_resolver); pack.
        """
        raise NotImplementedError

    def _click_agregar(self):
        """Callback del boton Agregar: delega al controller, no decide nada.

        # TODO: lee self.entrada.get(), llama a
        # self.controller.agregar_nota(texto), y limpia self.entrada
        # (delete(0, tk.END)).
        """
        raise NotImplementedError

    def _click_resolver(self):
        """Callback del boton Resolver: delega al controller.

        # TODO: obten self.lista.curselection(); si hay seleccion,
        # llama a self.controller.resolver_nota(seleccion[0]).
        """
        raise NotImplementedError

    def actualizar_lista(self, notas):
        """El controller llama a esto para refrescar la vista con datos nuevos.

        # TODO: limpia self.lista (delete(0, tk.END)) y por cada nota
        # en 'notas', inserta un texto tipo "[RESUELTA] texto" o
        # "[ABIERTA] texto" segun nota['resuelta'].
        """
        raise NotImplementedError

    def mostrar_error(self, mensaje: str):
        """El controller llama a esto para mostrar errores de validacion.

        # TODO: usa messagebox.showerror('LogiTrack', mensaje).
        """
        raise NotImplementedError
