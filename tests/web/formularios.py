"""Formularios de la interfaz web. Solo dan forma a los datos: las reglas
de negocio y las validaciones de seguridad están en los servicios."""

from decimal import Decimal

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


class EnvioForm(forms.Form):
    """Datos de envío del checkout (HU-04 criterio 3). El servicio los vuelve
    a validar; aquí solo dan la forma y la validación del navegador."""

    nombre = forms.CharField(label="Nombre de quien recibe", max_length=150,
                             widget=forms.TextInput(attrs={"autocomplete": "name"}))
    direccion = forms.CharField(label="Dirección", max_length=200,
                                widget=forms.TextInput(attrs={"autocomplete": "street-address"}))
    ciudad = forms.CharField(label="Ciudad", max_length=100,
                             widget=forms.TextInput(attrs={"autocomplete": "address-level2"}))
    telefono = forms.CharField(
        label="Teléfono", max_length=20, help_text="Entre 7 y 15 dígitos; puede empezar con +.",
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel",
                                      "pattern": r"\+?[0-9][0-9 ]{6,19}"}),
    )


class ProductoForm(forms.Form):
    """Crear o editar un producto (HU-03). El servicio vuelve a validar."""

    nombre = forms.CharField(label="Nombre", max_length=200)
    descripcion = forms.CharField(label="Descripción", max_length=2000, required=False,
                                  widget=forms.Textarea(attrs={"rows": 4}))
    precio = forms.DecimalField(label="Precio (COP)", max_digits=12, decimal_places=2,
                                min_value=Decimal("0.01"))
    stock = forms.IntegerField(label="Unidades disponibles", min_value=0, max_value=1_000_000)
    activo = forms.BooleanField(label="Visible en el catálogo", required=False, initial=True)
