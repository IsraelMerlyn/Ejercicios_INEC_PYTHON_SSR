"""
LogiTrack -- Capa de Controlador (orquesta Modelo <-> Vista).
=================================================================

Regla de oro: el controller no dibuja widgets NI guarda estado de
negocio propio; solo traduce eventos de la vista en llamadas al modelo,
y llamadas al modelo en actualizaciones de la vista.
"""


class NotaController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.controller = self  # la vista necesita esta referencia
        # TODO: al arrancar, refresca la vista con los datos actuales del
        # modelo (llama a self.view.actualizar_lista(self.model.listar())).
        raise NotImplementedError

    def agregar_nota(self, texto: str):
        """Recibe la peticion de la vista, valida via el modelo, refresca.

        # TODO:
        # try: self.model.agregar(texto); luego
        # self.view.actualizar_lista(self.model.listar())
        # except ValueError as e: self.view.mostrar_error(str(e))
        """
        raise NotImplementedError

    def resolver_nota(self, indice: int):
        """Recibe la peticion de la vista, actualiza el modelo, refresca.

        # TODO: self.model.marcar_resuelta(indice), luego
        # self.view.actualizar_lista(self.model.listar()).
        """
        raise NotImplementedError
