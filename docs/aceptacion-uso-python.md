# Aceptación del uso de Python en el proyecto

## Contexto

El agente de inteligencia artificial que usa el docente del curso para revisar los proyectos está configurado para Java. Este proyecto no está escrito en Java: usa **Python** con **Django** (ver [README](../README.md)).

## Decisión

El docente **aceptó que el proyecto se desarrolle en Python**, aunque su agente de IA esté configurado para Java.

| Campo | Detalle |
| --- | --- |
| Quién aceptó | Docente del curso |
| Medio | Verbal, en clase |
| Fecha | _(completar: AAAA-MM-DD)_ |
| Lenguaje aceptado | Python 3.11+ con Django |
| Lenguaje configurado en el agente del docente | Java |
| Integrantes del equipo | Kevin Vuskovit Garcia Gonzalez, Esteban Pinilla Vela |

## Qué implica

- El proyecto sigue en Python y Django. No hay que migrar el código a Java.
- Si el agente de IA del docente evalúa el código con criterios de Java (por ejemplo, la estructura de paquetes, la compilación con Maven o Gradle, o pruebas JUnit), esos criterios no aplican a este repositorio. Su equivalente en este proyecto es:

  | Criterio en Java | Equivalente en este proyecto |
  | --- | --- |
  | Maven / Gradle (`pom.xml`, `build.gradle`) | `tests/requirements.txt` con `pip` |
  | JUnit | `python manage.py test` (pruebas de Django) |
  | Spring Boot | Django |
  | JPA / Hibernate | ORM de Django y migraciones |

## Constancia

La aceptación fue verbal, así que este documento queda como registro escrito. Si más adelante el docente la confirma por escrito (correo o plataforma del curso), se agrega aquí el enlace o una captura.
