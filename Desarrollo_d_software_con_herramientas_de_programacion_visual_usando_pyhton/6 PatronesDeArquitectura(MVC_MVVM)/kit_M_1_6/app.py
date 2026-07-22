"""
LogiTrack -- Bitacora de Incidencias bajo MVC (Proyecto Integrador M1.6)
===========================================================================

Contexto (caso "LogiTrack"):
LogiTrack necesita una app de escritorio para que sus operadores registren
y den seguimiento a notas/incidencias de la flota (ej. "Camion 12: fuga de
aceite"). El requisito del negocio es que la logica de negocio (Model) y la
interfaz (View) esten TOTALMENTE desacopladas, comunicandose solo a traves
del Controller, para poder migrar la interfaz en el futuro (consola web,
otra libreria GUI) sin tocar la logica.

Este archivo es el PUNTO DE ENTRADA. NO resuelve el ejercicio: implementa
model.py, view.py y controller.py (cada uno con sus propios TODO) y luego
conecta las tres piezas aqui.

Que debes lograr:
  - model.py: NotaModel -- persiste notas en datos/notes_data.json,
    valida, lista, marca como resuelta. NO importa tkinter.
  - view.py: NotaView -- SOLO dibuja widgets y captura eventos del
    usuario; delega toda decision al controller (self.view.controller).
  - controller.py: NotaController -- orquesta: recibe eventos de la
    vista, llama al modelo, le dice a la vista que actualizar.
  - app.py (este archivo): crea el modelo, la vista y el controller, y
    arranca el mainloop.

Flujo esperado (unidireccional): usuario -> vista -> controller -> modelo
-> vista. Ningun dato debe saltar un eslabon (la vista NUNCA llama
directamente al modelo).
"""

import tkinter as tk

from model import NotaModel
from view import NotaView
from controller import NotaController


def main():
    # TODO:
    # 1. Crea la ventana raiz: root = tk.Tk(); root.title("LogiTrack -- Bitacora de Incidencias")
    # 2. Instancia el modelo: modelo = NotaModel()
    # 3. Instancia la vista: vista = NotaView(root)
    # 4. Instancia el controller conectando modelo y vista:
    #    NotaController(modelo, vista)
    # 5. root.mainloop()
    raise NotImplementedError


if __name__ == "__main__":
    main()
