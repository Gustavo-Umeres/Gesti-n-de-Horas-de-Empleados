# core/admin.py

from django.contrib import admin
from .models import (
    EmpresaTercera, Trabajador, LineaProducto, Producto, Orden, ItemOrden,
    Etapa, Proceso, Subproceso, SeguimientoProduccion, RegistroAsistencia, RegistroActividad
)

@admin.register(EmpresaTercera)
class EmpresaTerceraAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'codigo', 'tipo', 'empresa_tercera')
    list_filter = ('tipo', 'empresa_tercera')
    search_fields = ('nombres', 'apellidos', 'codigo')
    list_select_related = ('empresa_tercera',)

@admin.register(LineaProducto)
class LineaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'linea', 'presentacion')
    list_filter = ('linea',)
    search_fields = ('nombre', 'codigo')
    list_select_related = ('linea',)

class ItemOrdenInline(admin.TabularInline):
    model = ItemOrden
    extra = 1
    autocomplete_fields = ['producto']

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('codigo_orden', 'usuario', 'estado', 'fecha_creacion', 'lote_asignado')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('codigo_orden', 'usuario__username', 'lote_asignado')
    readonly_fields = ('codigo_orden', 'fecha_creacion')
    inlines = [ItemOrdenInline]
    date_hierarchy = 'fecha_creacion'

# --- NUEVO ---
# Se necesita registrar ItemOrdenAdmin para que autocomplete_fields funcione en SeguimientoProduccionAdmin
@admin.register(ItemOrden)
class ItemOrdenAdmin(admin.ModelAdmin):
    list_display = ('orden', 'producto', 'cantidad')
    search_fields = ('producto__nombre', 'orden__codigo_orden') # Campos para la búsqueda
    list_select_related = ('orden', 'producto')


@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden_secuencia')
    ordering = ('orden_secuencia',)

@admin.register(Proceso)
class ProcesoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'etapa', 'orden_secuencia')
    list_filter = ('etapa',)
    ordering = ('etapa__orden_secuencia', 'orden_secuencia')

@admin.register(Subproceso)
class SubprocesoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proceso', 'orden_secuencia')
    list_filter = ('proceso__etapa',)
    # --- MODIFICADO ---
    # Se añade search_fields para que autocomplete_fields funcione
    search_fields = ('nombre', 'proceso__nombre') 
    ordering = ('proceso__etapa__orden_secuencia', 'proceso__orden_secuencia', 'orden_secuencia')

@admin.register(SeguimientoProduccion)
class SeguimientoProduccionAdmin(admin.ModelAdmin):
    list_display = ('item_orden', 'subproceso_actual', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado', 'subproceso_actual')
    search_fields = ('item_orden__producto__nombre', 'subproceso_actual__nombre')
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'duracion_total_segundos')
    filter_horizontal = ('trabajadores_asignados',)
    autocomplete_fields = ['item_orden', 'subproceso_actual']

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('seguimiento', 'trabajador', 'fecha', 'asistio')
    list_filter = ('asistio', 'fecha')
    date_hierarchy = 'fecha'

@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    list_display = ('seguimiento', 'tipo_evento', 'timestamp', 'usuario')
    list_filter = ('tipo_evento',)
    readonly_fields = ('timestamp',)