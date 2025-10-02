from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

# --- Modelos para Trabajadores y Empresas ---

class EmpresaTercera(models.Model):
    """Modelo para registrar empresas de terceros."""
    nombre = models.CharField(max_length=255, unique=True, help_text="Nombre de la empresa externa")

    def __str__(self):
        return self.nombre

class Trabajador(models.Model):
    """Modelo para registrar a los trabajadores."""
    class TipoTrabajador(models.TextChoices):
        PLANILLA = 'PLANILLA', 'Planilla'
        TERCERO = 'TERCERO', 'Tercero'

    nombres = models.CharField(max_length=200)
    apellidos = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Código único del trabajador")
    tipo = models.CharField(max_length=10, choices=TipoTrabajador.choices, default=TipoTrabajador.PLANILLA)
    empresa_tercera = models.ForeignKey(EmpresaTercera, on_delete=models.SET_NULL, null=True, blank=True, help_text="Empresa si es de tipo 'Tercero'")

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

# --- Modelos para Productos y Catálogo ---

class LineaProducto(models.Model):
    """Categorías para los productos, ej: Inyectables, Polvos."""
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    """Modelo para los productos."""
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=50, unique=True, help_text="Código único del producto")
    linea = models.ForeignKey(LineaProducto, related_name='productos', on_delete=models.CASCADE)
    presentacion = models.CharField(max_length=100, help_text="Ej: 20mg, 50ml, Caja x 100")

    def __str__(self):
        return f"{self.nombre} ({self.presentacion})"

# --- Modelos para Pedidos y Carrito ---

class Orden(models.Model):
    """Representa un pedido, que inicia como un carrito de compras."""
    class EstadoOrden(models.TextChoices):
        CARRITO = 'CARRITO', 'Carrito'
        PROCESADA = 'PROCESADA', 'Procesada'
        EN_PRODUCCION = 'EN_PRODUCCION', 'En Producción'
        COMPLETADA = 'COMPLETADA', 'Completada'

    codigo_orden = models.CharField(max_length=20, unique=True, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Usuario que realiza el pedido")
    estado = models.CharField(max_length=20, choices=EstadoOrden.choices, default=EstadoOrden.CARRITO)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    lote_asignado = models.CharField(max_length=50, blank=True, null=True, help_text="Código de lote para la producción")

    def save(self, *args, **kwargs):
        if not self.codigo_orden:
            # Genera un código único para la orden
            self.codigo_orden = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden {self.codigo_orden} - {self.estado}"

class ItemOrden(models.Model):
    """Representa un producto dentro de una orden."""
    orden = models.ForeignKey(Orden, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, related_name='items_orden', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en orden {self.orden.codigo_orden}"

# --- Modelos para el Flujo de Producción ---

class Etapa(models.Model):
    """Etapa principal del proceso de producción. Ej: Fabricación, Envasado."""
    nombre = models.CharField(max_length=100, unique=True)
    orden_secuencia = models.PositiveIntegerField(default=0, help_text="Orden de la etapa en el flujo")

    class Meta:
        ordering = ['orden_secuencia']

    def __str__(self):
        return self.nombre

class Proceso(models.Model):
    """Proceso dentro de una etapa. Ej: Tableteado, Impresión de Caja."""
    etapa = models.ForeignKey(Etapa, related_name='procesos', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    orden_secuencia = models.PositiveIntegerField(default=0, help_text="Orden del proceso en la etapa")

    class Meta:
        ordering = ['etapa__orden_secuencia', 'orden_secuencia']

    def __str__(self):
        return f"{self.etapa.nombre} -> {self.nombre}"

class Subproceso(models.Model):
    """Subproceso detallado dentro de un proceso. Ej: Calibración, Limpieza de área."""
    proceso = models.ForeignKey(Proceso, related_name='subprocesos', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=255)
    orden_secuencia = models.PositiveIntegerField(default=0, help_text="Orden del subproceso en el proceso")

    class Meta:
        ordering = ['proceso__etapa__orden_secuencia', 'proceso__orden_secuencia', 'orden_secuencia']

    def __str__(self):
        return f"{self.proceso} -> {self.nombre}"


# --- Modelos para Seguimiento de Tiempo y Asistencia ---

class SeguimientoProduccion(models.Model):
    """Modelo central para seguir el progreso de un producto de una orden en el flujo."""
    class EstadoSeguimiento(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_PROGRESO = 'EN_PROGRESO', 'En Progreso'
        PAUSADO = 'PAUSADO', 'Pausado'
        FINALIZADO = 'FINALIZADO', 'Finalizado'

    item_orden = models.ForeignKey(ItemOrden, on_delete=models.CASCADE, related_name="seguimientos")
    subproceso_actual = models.ForeignKey(Subproceso, on_delete=models.PROTECT)
    estado = models.CharField(max_length=20, choices=EstadoSeguimiento.choices, default=EstadoSeguimiento.PENDIENTE)
    trabajadores_asignados = models.ManyToManyField(Trabajador, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_total_segundos = models.BigIntegerField(default=0, help_text="Duración acumulada del trabajo en segundos")

    def __str__(self):
        return f"Seguimiento de {self.item_orden.producto.nombre} en {self.subproceso_actual.nombre}"

class RegistroAsistencia(models.Model):
    """Registra la asistencia diaria de un trabajador a un subproceso."""
    seguimiento = models.ForeignKey(SeguimientoProduccion, on_delete=models.CASCADE)
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    asistio = models.BooleanField(default=True)

    class Meta:
        unique_together = ('seguimiento', 'trabajador', 'fecha')

    def __str__(self):
        estado = "Asistió" if self.asistio else "Faltó"
        return f"{self.trabajador} - {self.fecha} - {estado}"

class RegistroActividad(models.Model):
    """Registra eventos de tiempo (inicio, pausa, reanudación) para el cronómetro."""
    class TipoEvento(models.TextChoices):
        INICIO = 'INICIO', 'Inicio'
        PAUSA = 'PAUSA', 'Pausa'
        REANUDAR = 'REANUDAR', 'Reanudar'
        FIN = 'FIN', 'Fin'

    seguimiento = models.ForeignKey(SeguimientoProduccion, on_delete=models.CASCADE, related_name="actividades")
    tipo_evento = models.CharField(max_length=20, choices=TipoEvento.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Evento {self.tipo_evento} en {self.seguimiento} a las {self.timestamp}"
