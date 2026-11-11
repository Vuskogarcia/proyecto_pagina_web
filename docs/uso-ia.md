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
2026-11-02	Kevin García	Claude (Cowork)	Implementación de las recomendaciones de la auditoría de seguridad (ADL-01 a ADL-07, H13, H14), HU-01 (sesión y roles), carrito editable, tipo de PQR e interfaz web con plantillas Django; pruebas de seguridad escritas primero (en rojo) y verificadas en PostgreSQL. Ver docs/seguridad/ (semana-13.md y ai-decision-log-seguridad.md §5).	[PENDIENTE] Revisión línea por línea del equipo antes del commit; llenar «Decisión humana» en el AI Decision Log.
2026-11-11	Kevin García	Claude Code (Opus 5.5)	Módulo 7, semanas 13 y 14 (rama feature/modulo7-rnf-y-rc): Historias 01 (413), 03 (ReDoS), 04 y 10 (Argon2id, medido), 05 (cierre de DT-13 y rotación), 06 (id de seguimiento en los 500), 07 (veredicto H1–H14), 08 y 09 (k6 contra PostgreSQL con evidencia cruda), 11 (triage del RC), 12 (CHANGELOG) y el registro único docs/seguridad-y-rnf.md. Todos los números salen de ejecuciones reales en el equipo de Kevin (docs/rendimiento/resultados/ y docs/seguridad/evidencia/modulo7-ejecucion-postgresql.txt).	[PENDIENTE] Revisión del equipo antes de fusionar: decisiones tomadas por la IA a pedido de Kevin que el equipo debe confirmar o cambiar: revocar en vez de purgar (DT-13), Argon2id t=3/64 MiB/p=4, 400 para asunto > 200 y ?orden= desconocido (cambia la API), fecha de corte 2026-11-13. Historia 02 y H9 quedaron sin contenido porque no hay enunciado. gitleaks no se corrió localmente (lo corre el CI).
				
3. Buenas prácticas acordadas

No pegar código generado por IA sin leerlo y entenderlo línea por línea.
No usar IA para escribir las pruebas y el código que prueban al mismo tiempo, sin revisión cruzada.
Citar la herramienta usada en la descripción del Pull Request cuando el uso fue relevante.

Este documento no debe considerarse definitivo mientras existan etiquetas [DECISIÓN DEL EQUIPO] sin resolver.
