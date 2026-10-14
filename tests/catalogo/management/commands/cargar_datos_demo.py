"""Carga datos de ejemplo en las tablas de Django.

Son los mismos datos de database/02_seed.sql (clientes, productos, agentes,
pedidos y tickets), pero creados a través de los servicios de la aplicación,
así que respetan las mismas reglas de negocio que la API.

Uso (desde la carpeta tests/):
    python manage.py cargar_datos_demo           # carga si la base está vacía
    python manage.py cargar_datos_demo --reset   # borra los datos y los vuelve a cargar
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from carrito import servicios as pedidos
from carrito.models import Pedido
from catalogo.models import Producto
from soporte import servicios as soporte
from soporte.models import TicketSoporte

CLAVE_DEMO = "demo12345"

CLIENTES = [
    ("ana", "Ana", "Torres", "ana.torres@example.com"),
    ("luis", "Luis", "Gómez", "luis.gomez@example.com"),
    ("maria", "María", "Pérez", "maria.perez@example.com"),
]

AGENTES = [
    ("carlos", "Carlos", "Ruiz", "carlos.ruiz@example.com"),
    ("diana", "Diana", "Salazar", "diana.salazar@example.com"),
]

PRODUCTOS = [
    ("Teclado mecánico", "Teclado mecánico switches rojos", "150000", 25),
    ("Mouse inalámbrico", "Mouse ergonómico 2.4GHz", "60000", 40),
    ('Monitor 24"', "Monitor Full HD IPS", "650000", 10),
    ("Audífonos gamer", "Audífonos con micrófono", "120000", 15),
    ("Webcam HD", "Cámara 1080p con micrófono", "180000", 0),  # agotado: HU-02 criterio 4
]


class Command(BaseCommand):
    help = "Carga datos de ejemplo (clientes, agentes, productos, pedidos y tickets)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra pedidos, tickets, productos y usuarios de ejemplo antes de cargar.",
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        usuarios_demo = [u for u, *_ in CLIENTES + AGENTES]

        if opciones["reset"]:
            TicketSoporte.objects.all().delete()
            Pedido.objects.all().delete()
            Producto.objects.all().delete()
            Usuario.objects.filter(username__in=usuarios_demo).delete()
            self.stdout.write("Datos anteriores borrados.")
        elif Producto.objects.exists() or Usuario.objects.filter(username__in=usuarios_demo).exists():
            self.stdout.write(
                self.style.WARNING(
                    "Ya hay datos cargados. Usa --reset si quieres borrarlos y cargarlos de nuevo."
                )
            )
            return

        # Usuarios: clientes normales y agentes (is_staff = pueden entrar a /admin/).
        def crear_usuario(datos, es_agente):
            username, nombre, apellido, correo = datos
            return Usuario.objects.create_user(
                username=username,
                password=CLAVE_DEMO,
                first_name=nombre,
                last_name=apellido,
                email=correo,
                is_staff=es_agente,
            )

        ana, luis, maria = (crear_usuario(c, False) for c in CLIENTES)
        carlos, diana = (crear_usuario(a, True) for a in AGENTES)

        teclado, mouse, monitor, audifonos, _ = (
            Producto.objects.create(nombre=n, descripcion=d, precio=Decimal(p), stock=s)
            for n, d, p, s in PRODUCTOS
        )

        # Pedidos: pasan por el checkout real, así que también descuentan el stock.
        pedido_ana = pedidos.realizar_checkout(ana.pk, [{"id_producto": teclado.pk, "cantidad": 1}])
        pedido_luis = pedidos.realizar_checkout(
            luis.pk,
            [
                {"id_producto": monitor.pk, "cantidad": 1},
                {"id_producto": audifonos.pk, "cantidad": 2},
            ],
        )
        pedidos.realizar_checkout(maria.pk, [{"id_producto": mouse.pk, "cantidad": 3}])

        # Tickets: uno abierto en la cola, uno en proceso y uno cerrado.
        soporte.crear_ticket(
            ana.pk, "El producto no ha llegado", pedido_id=pedido_ana.pk, asunto="Pedido sin entregar"
        )
        en_proceso = soporte.crear_ticket(
            luis.pk, "Necesito cambiar la dirección de envío", pedido_id=pedido_luis.pk,
            asunto="Cambio de dirección",
        )
        soporte.tomar_ticket(en_proceso.pk, diana.pk)
        cerrado = soporte.crear_ticket(maria.pk, "¿Cuánto dura la garantía?", asunto="Consulta sobre garantía")
        soporte.tomar_ticket(cerrado.pk, carlos.pk)
        TicketSoporte.objects.filter(pk=cerrado.pk).update(estado=TicketSoporte.CERRADO)

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados:"))
        self.stdout.write(f"  Clientes: ana, luis, maria · Agentes: carlos, diana (clave: {CLAVE_DEMO})")
        self.stdout.write(f"  Productos: {Producto.objects.count()} · Pedidos: {Pedido.objects.count()} "
                          f"· Tickets: {TicketSoporte.objects.count()}")
