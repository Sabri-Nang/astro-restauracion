# Interfaz para Julia — revisión de etapa 4

## Recorrido principal

1. Subir la foto propia. El formato se presenta como PNG o TIFF; la profundidad de color se explica en una ayuda, sin confundirla con dimensiones o peso. Los originales de 16 bits requieren exportar una copia compatible; no se convierten silenciosamente.
2. Elegir cuánto puede cambiar la IA la foto. Se conserva el control de intensidad; los pasos, semilla y tamaño de trabajo usan 30, 42 y 256 para mantener un recorrido simple y reproducible. El laboratorio técnico conserva su propósito separado.
3. Comparar foto ajustada y reconstrucción mediante el deslizador. Una vista contigua muestra las zonas para revisar en amarillo; el control de resaltado permite volver a la salida sin marcas, sin inferencia adicional.
4. Leer el informe y guardar el resultado. Las afinidades CLIP se presentan como preferencias por frases, sin números de calidad ni probabilidad de autenticidad. Los valores exactos y parámetros quedan en el ZIP.

Se retiraron los ejemplos, el botón de ensayo guardado y el acordeón de registro completo de la interfaz de usuario final. La evidencia y las funciones de investigación permanecen disponibles en el repositorio. Cambiar la foto limpia los resultados para evitar asociarlos a otra entrada. El reintento del informe no vuelve a ejecutar difusión.

## Honestidad y resaltado

El amarillo significa cambio de píxeles que merece revisión, no invención detectada. Se calcula la media RGB absoluta redondeada y se promedia en un entorno local de 5 × 5 píxeles para agrupar cambios cercanos, con umbral fijo de 12 sobre 255, color (255, 176, 0) y opacidad 0,6 sobre la salida. No se normaliza por imagen ni se usa CLIP para localizar supuestas invenciones. El aviso aclara que también puede marcar ruido modificado o detalles perdidos y que las zonas sin marca no están verificadas.

El ZIP conserva la salida exacta sin marcas, la copia resaltada, el mapa absoluto, original, informe, parámetros y hashes. Añade una copia para compartir con una banda visible de identificación de IA; no se usa para métricas. El aviso también se guarda en los metadatos PNG, informe y LEEME.

## Base visual y revisión pendiente

Tema Soft de Gradio, acento teal, Arial/sans-serif, máximo 1120 px y adaptación a pantallas angostas. El foco de teclado se conserva. La leyenda usa texto además del color. Los estilos de `assets/interfaz/tema.css` se comparten entre local y Colab mediante `launch_app()`.

Las pruebas comprueban el cálculo del resaltado, la conservación de píxeles, el registro descargable y la estructura de componentes. El host de navegador no estuvo disponible al intentar revisar esta versión: quedan pendientes la captura real, contraste claro/oscuro, móvil, teclado y una prueba de comprensión con una persona. No se da por realizada una prueba de usabilidad con Julia.
