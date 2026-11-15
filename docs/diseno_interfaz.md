# Base de diseño para Julia — etapa 4

La revisión se retoma por pedido de la autora al finalizar la etapa 3. Esta primera versión organiza el uso; todavía requiere revisión visual y prueba con una persona.

## Recorrido y jerarquía

1. Preparar: subir un archivo o elegir el ejemplo público. Los ajustes avanzados se agrupan en un acordeón para no competir con la acción principal.
2. Comparar: entrada preparada, reconstrucción identificada como IA y deslizador de las mismas regiones. El mapa se abre cuando se necesita.
3. Entender y guardar: informe, límites, reintento independiente y ZIP. El registro técnico se consulta opcionalmente.

«Ver ensayo guardado» permite explorar resultados reales sin esperar una inferencia; la vista lo identifica explícitamente. «Procesar y comparar» ejecuta los modelos. Cambiar el archivo limpia los resultados anteriores para evitar asociarlos a la entrada equivocada.

## Convenciones compartidas

- Tipografía del sistema Arial/sans-serif, sin descargar fuentes externas; título adaptable entre 2 y 3 rem y texto con interlineado 1,55.
- Tema Soft de Gradio, acento teal y neutros slate; color de acento local `#0f766e`.
- Espaciado base 16 px, radio 12 px, contenedor máximo 1120 px; margen interior 24 px y 12 px en pantallas de hasta 640 px.
- Acción primaria para inferencia; secundaria para evidencia guardada. Se conserva el foco de teclado y se refuerza su contorno.
- Advertencia persistente junto al encabezado; ningún color sustituye etiquetas o mensajes textuales.
- No usar «limpieza exitosa», estrellas de calidad ni porcentajes de reducción sin evidencia. La similitud CLIP conserva cuatro decimales y un límite interpretativo explícito.

Los estilos están en `assets/interfaz/tema.css`; `launch_app()` aplica el mismo tema localmente y en el nuevo notebook. Esta base pequeña constituye convenciones reutilizables del prototipo, no un sistema de diseño completo ya validado.

## Revisión pendiente para la demo

Comprobar contraste en modo claro y oscuro, navegación con teclado, ancho móvil, lectura de nombres largos y errores, tiempo de espera en Colab y comprensión del informe. Registrar lo observado antes de marcarlo como validado. No se ha realizado una prueba de usabilidad con Julia.
