"""
LogiTrack -- Capa de Modelo (datos + logica de negocio).
============================================================

Regla de oro del patron MVC: este archivo NO debe importar tkinter ni
ningun otro toolkit visual. Solo conoce datos y reglas de negocio.
"""

import json
import os

RUTA_DATOS = os.path.join(os.path.dirname(__file__), "datos", "notes_data.json")
LIMITE_NOTAS_ABIERTAS = 8


class NotaModel:
    """Persiste y valida notas/incidencias de la flota de LogiTrack."""

    def __init__(self, ruta_datos: str = RUTA_DATOS):
        self.ruta_datos = ruta_datos
        self.notas = []
        self.cargar()

    def cargar(self):
        """Carga self.notas desde el archivo JSON (si existe).

        # TODO: si os.path.exists(self.ruta_datos), abre y json.load()
        # el contenido en self.notas. Si no existe, deja self.notas = [].
        """
        raise NotImplementedError

    def guardar(self):
        """Persiste self.notas al archivo JSON.

        # TODO: escribe self.notas en self.ruta_datos con json.dump
        # (indent=2, ensure_ascii=False). Crea el directorio 'datos/'
        # si no existe (os.makedirs).
        """
        raise NotImplementedError

    def agregar(self, texto: str):
        """Agrega una nota nueva. Lanza ValueError si es invalida.

        # TODO:
        # 1. Si texto.strip() esta vacio: raise ValueError("El texto de
        #    la nota no puede estar vacio").
        # 2. Cuenta cuantas notas tienen 'resuelta' == False; si ya hay
        #    LIMITE_NOTAS_ABIERTAS o mas, raise ValueError("Limite de
        #    notas abiertas alcanzado (8). Resuelve alguna antes de
        #    agregar otra.").
        # 3. Si pasa las validaciones, agrega un dict
        #    {"texto": texto.strip(), "resuelta": False} a self.notas,
        #    llama a self.guardar() y devuelve True.
        """
        raise NotImplementedError

    def listar(self):
        """Devuelve una COPIA de self.notas (para que nadie mute el original).

        # TODO: devuelve self.notas.copy() (o list(self.notas)).
        """
        raise NotImplementedError

    def marcar_resuelta(self, indice: int):
        """Marca la nota en 'indice' como resuelta y persiste el cambio.

        # TODO: si 0 <= indice < len(self.notas), pon
        # self.notas[indice]['resuelta'] = True y llama a self.guardar().
        # Si el indice es invalido, no hagas nada (no lances excepcion).
        """
        raise NotImplementedError
