Política y Registro de Uso de IA

Documento vivo — registrar cada uso significativo de IA en el proyecto a medida que ocurra.

1. Política del equipo

[DECISIÓN DEL EQUIPO] Definir las reglas de uso de IA para este proyecto. Sugerencia de puntos a cubrir:

| Aspecto                                                     | Política definida                                                                                                                                                                                                                                                                                  |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **¿Para qué tareas SÍ se permite usar IA?**                 | Se permite utilizar IA para redactar borradores de documentación, mejorar la redacción, explicar errores, resolver dudas conceptuales, generar código repetitivo o *boilerplate*, sugerir estructuras de código y revisar sintaxis.                                                                |
| **¿Para qué tareas NO se permite usar IA sin supervisión?** | No se permite utilizar IA sin supervisión para tomar decisiones de diseño, definir la arquitectura del sistema, establecer la lógica de negocio central, resolver por completo el problema principal del proyecto o generar funcionalidades que el equipo no comprenda.                            |
| **¿Es obligatorio revisar el código generado?**             | **Sí.** Todo código generado o modificado con ayuda de IA debe ser revisado, probado y comprendido por el integrante responsable antes de realizar un commit. Ningún integrante debe subir código que no pueda explicar.                                                                           |
| **¿Cómo se declara el uso de IA?**                          | Cuando la IA haya tenido una participación relevante en una funcionalidad, se debe indicar en la descripción del Pull Request. Se puede utilizar una nota como: **"Uso de IA: Sí. Se utilizó IA para generar/revisar código y explicar errores. El código fue revisado y probado por el equipo."** |

2. Registro de uso

Cada integrante agrega una fila cuando use IA de forma significativa (más allá de autocompletado simple).

Fecha	Integrante	Herramienta	Para qué se usó	Qué se revisó/ajustó manualmente
				
3. Buenas prácticas acordadas

No pegar código generado por IA sin leerlo y entenderlo línea por línea.
No usar IA para escribir las pruebas y el código que prueban al mismo tiempo, sin revisión cruzada.
Citar la herramienta usada en la descripción del Pull Request cuando el uso fue relevante.

Este documento no debe considerarse definitivo mientras existan etiquetas [DECISIÓN DEL EQUIPO] sin resolver.
