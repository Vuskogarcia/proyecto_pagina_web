"""Crea el grupo "agentes" (rol de agente de soporte, HU-01)."""

from django.db import migrations


def crear_grupo(apps, schema_editor):
    apps.get_model("auth", "Group").objects.get_or_create(name="agentes")


def borrar_grupo(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name="agentes").delete()


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(crear_grupo, borrar_grupo)]
