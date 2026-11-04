"""Formularios de la interfaz web. Solo dan forma a los datos: las reglas
de negocio y las validaciones de seguridad están en los servicios."""

from django import forms

from soporte.models import TicketSoporte


class EntrarForm(forms.Form):
    usuario = forms.CharField(label="Usuario o email", max_length=150,
                              widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}))
    clave = forms.CharField(label="Contraseña", max_length=128,
                            widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class RegistroForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=150, required=False,
                             widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(label="Email", max_length=150,
                             widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    clave = forms.CharField(label="Contraseña", max_length=128,
                            help_text="Mínimo 10 caracteres; no uses solo números ni claves comunes.",
                            widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": 10}))
    clave2 = forms.CharField(label="Repite la contraseña", max_length=128,
                             widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": 10}))

    def clean(self):
        datos = super().clean()
        if datos.get("clave") and datos.get("clave") != datos.get("clave2"):
            self.add_error("clave2", "Las contraseñas no coinciden.")
        return datos


class PqrForm(forms.Form):
    tipo = forms.ChoiceField(label="Tipo de solicitud", choices=TicketSoporte.TIPOS,
                             widget=forms.RadioSelect)
    pedido = forms.TypedChoiceField(label="Pedido relacionado", coerce=int, required=False,
                                    empty_value=None)
    asunto = forms.CharField(label="Asunto", max_length=200)
    descripcion = forms.CharField(label="Describe tu solicitud", max_length=5000,
                                  widget=forms.Textarea(attrs={"rows": 7}))

    def __init__(self, *args, pedidos=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pedido"].choices = [("", "Sin pedido (consulta general)")] + [
            (p.pk, f"{p.codigo} · {p.creado_en:%d/%m/%Y} · ${p.total():,.0f}".replace(",", "."))
            for p in pedidos
        ]
