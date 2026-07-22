# Proyecto Integrador -- Modulo 1.6: Bitacora de Incidencias bajo MVC (LogiTrack)

## Objetivo

LogiTrack necesita una app de escritorio donde sus operadores registren
incidencias de la flota ("Camion 12: fuga de aceite"). El requisito no
negociable del negocio es que la app siga el patron **MVC** de forma
estricta: si manana deciden cambiar tkinter por otra libreria, o mover la
interfaz a consola/web, la logica de negocio (Model) no debe tocarse.

## Que debes construir

Completa cada `# TODO:` en los 4 archivos:

1. **`model.py`** (`NotaModel`): carga/guarda `datos/notes_data.json`,
   valida (texto no vacio, maximo 8 notas abiertas simultaneas), lista y
   marca notas como resueltas. **Nunca** importa `tkinter`.
2. **`view.py`** (`NotaView`): dibuja `Entry`, `Listbox` y botones.
   **Nunca** decide nada por su cuenta -- cada clic delega al
   `controller`.
3. **`controller.py`** (`NotaController`): recibe eventos de la vista,
   llama al modelo, actualiza la vista.
4. **`app.py`**: conecta las tres piezas y arranca el `mainloop`.

Flujo unidireccional obligatorio: `usuario -> vista -> controller ->
modelo -> vista`. Si tu vista llama directamente a `model`, rompiste el
contrato de MVC.

## Estructura de carpetas

```
proyecto_integrador/
├── app.py               # Punto de entrada -- completa el TODO
├── model.py              # Modelo -- completa los TODO (sin tkinter)
├── view.py                # Vista -- completa los TODO
├── controller.py          # Controlador -- completa los TODO
├── datos/
│   └── notes_data.json     # Notas de ejemplo
├── requirements.txt        # Solo stdlib (tkinter + json)
└── README.md                # Este archivo
```

## Como correrlo

```bash
python app.py
```

## Que debes entregar

- Los 4 archivos completos (sin `NotImplementedError` pendientes).
- La app debe correr sin errores con `python app.py`.
- `model.py` no debe importar `tkinter` (verificalo con
  `grep -i tkinter model.py` -- no debe haber coincidencias).
- Repasa el brief completo de la leccion "Implementacion practica de MVC
  en Python" dentro de la plataforma -- ahi estan la rubrica de
  evaluacion y los criterios de calidad esperados.
