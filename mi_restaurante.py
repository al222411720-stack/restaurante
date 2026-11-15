"""
SISTEMA DE GESTION - MI RESTAURANTE
----------------------------------
Aplicacion de escritorio desarrollada con Python, Tkinter y MySQL (XAMPP).

Funciones:
- Registrar ventas y generar recibos.
- Guardar ventas y detalles en una base de datos MySQL.
- Consultar el historial de ventas.
- Administrar el catalogo de productos y sus precios.
- Mostrar reportes graficos: ventas por dia, ventas por mes,
  productos mas vendidos e ingresos por categoria.
- Consultar los ingresos totales.

Instalacion:
    pip install matplotlib mysql-connector-python

Antes de ejecutar:
    Abre XAMPP y pulsa Start en MySQL.

Ejecucion:
    python mi_restaurante_mysql.py

La base de datos "restaurante" y sus tablas se crean automaticamente.
"""

import mysql.connector
from datetime import datetime, date, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Matplotlib se utiliza para dibujar las graficas dentro de Tkinter.
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_DISPONIBLE = True
except ImportError:
    MATPLOTLIB_DISPONIBLE = False


# ---------------------------------------------------------------------
# CONFIGURACION GENERAL
# ---------------------------------------------------------------------

NOMBRE_RESTAURANTE = "Restaurante Rubi Esmeralda Solòrzano Carreño"
IMPUESTO = 0.07  # Se conserva el 7 % de impuesto del programa original.
SIMBOLO_MONEDA = "$"

# Datos de conexion a MySQL (valores por defecto de XAMPP).
NOMBRE_BASE_DATOS = "restaurante"
CONFIG_MYSQL = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "port": 3306,
}

# Productos iniciales tomados del programa original.
PRODUCTOS_INICIALES = [
    ("Pollo", "Comida", 1.32),
    ("Cordero", "Comida", 1.65),
    ("Salmon", "Comida", 2.31),
    ("Merluza", "Comida", 3.22),
    ("Kebab", "Comida", 1.22),
    ("Pizza 1", "Comida", 1.99),
    ("Pizza 2", "Comida", 2.05),
    ("Pizza 3", "Comida", 2.65),
    ("Agua", "Bebida", 0.25),
    ("Soda", "Bebida", 0.99),
    ("Jugo", "Bebida", 1.21),
    ("Cola", "Bebida", 1.54),
    ("Vino 1", "Bebida", 1.08),
    ("Vino 2", "Bebida", 1.10),
    ("Cerveza 1", "Bebida", 2.00),
    ("Cerveza 2", "Bebida", 1.58),
    ("Helado", "Postre", 1.54),
    ("Fruta", "Postre", 1.68),
    ("Brownies", "Postre", 1.32),
    ("Flan", "Postre", 1.97),
    ("Mousse", "Postre", 2.55),
    ("Pastel 1", "Postre", 2.14),
    ("Pastel 2", "Postre", 1.94),
    ("Pastel 3", "Postre", 1.74),
]


def dinero(valor):
    """Convierte un importe numerico a una cadena con dos decimales."""
    return f"{SIMBOLO_MONEDA} {float(valor):,.2f}"


# ---------------------------------------------------------------------
# BASE DE DATOS MYSQL
# ---------------------------------------------------------------------

class BaseDatos:
    """Administra la conexion y las operaciones de la base de datos."""

    def __init__(self):
        self.crear_base_datos()
        self.crear_tablas()
        self.cargar_productos_iniciales()

    def conectar(self):
        """Abre una conexion nueva con la base de datos restaurante."""
        return mysql.connector.connect(database=NOMBRE_BASE_DATOS, **CONFIG_MYSQL)

    def consultar(self, sql, parametros=(), uno=False):
        """Ejecuta un SELECT y devuelve filas como diccionarios."""
        con = self.conectar()
        try:
            cursor = con.cursor(dictionary=True)
            cursor.execute(sql, parametros)
            return cursor.fetchone() if uno else cursor.fetchall()
        finally:
            con.close()

    def ejecutar(self, sql, parametros=()):
        """Ejecuta un INSERT/UPDATE y guarda los cambios."""
        con = self.conectar()
        try:
            cursor = con.cursor()
            cursor.execute(sql, parametros)
            con.commit()
            return cursor.lastrowid
        finally:
            con.close()

    def crear_base_datos(self):
        """Crea la base de datos restaurante si todavia no existe."""
        con = mysql.connector.connect(**CONFIG_MYSQL)
        try:
            cursor = con.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {NOMBRE_BASE_DATOS} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
            con.commit()
        finally:
            con.close()

    def crear_tablas(self):
        """Crea las tablas necesarias si todavia no existen."""
        con = self.conectar()
        try:
            cursor = con.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    categoria VARCHAR(50) NOT NULL,
                    precio DECIMAL(10,2) NOT NULL CHECK (precio >= 0),
                    activo TINYINT NOT NULL DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ventas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    fecha DATETIME NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL,
                    impuesto DECIMAL(10,2) NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    INDEX idx_ventas_fecha (fecha)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalle_ventas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    venta_id INT NOT NULL,
                    producto_id INT,
                    producto_nombre VARCHAR(100) NOT NULL,
                    categoria VARCHAR(50) NOT NULL,
                    cantidad INT NOT NULL,
                    precio_unitario DECIMAL(10,2) NOT NULL,
                    importe DECIMAL(10,2) NOT NULL,
                    INDEX idx_detalle_venta (venta_id),
                    FOREIGN KEY (venta_id) REFERENCES ventas(id)
                )
            """)
            con.commit()
        finally:
            con.close()

    def cargar_productos_iniciales(self):
        """Registra el catalogo original solo cuando la tabla esta vacia."""
        fila = self.consultar("SELECT COUNT(*) AS cantidad FROM productos", uno=True)
        if fila["cantidad"] == 0:
            con = self.conectar()
            try:
                cursor = con.cursor()
                cursor.executemany(
                    "INSERT INTO productos(nombre, categoria, precio) VALUES (%s, %s, %s)",
                    PRODUCTOS_INICIALES
                )
                con.commit()
            finally:
                con.close()

    def obtener_productos(self, incluir_inactivos=False):
        """Devuelve los productos ordenados por categoria y nombre."""
        if incluir_inactivos:
            return self.consultar("SELECT * FROM productos ORDER BY categoria, nombre")
        return self.consultar(
            "SELECT * FROM productos WHERE activo=1 ORDER BY categoria, nombre"
        )

    def guardar_producto(self, producto_id, nombre, categoria, precio):
        """Inserta un producto nuevo o actualiza uno existente."""
        if producto_id:
            self.ejecutar("""
                UPDATE productos
                SET nombre=%s, categoria=%s, precio=%s
                WHERE id=%s
            """, (nombre, categoria, precio, producto_id))
        else:
            self.ejecutar("""
                INSERT INTO productos(nombre, categoria, precio)
                VALUES (%s, %s, %s)
            """, (nombre, categoria, precio))

    def desactivar_producto(self, producto_id):
        """Oculta un producto del catalogo sin borrar ventas anteriores."""
        self.ejecutar("UPDATE productos SET activo=0 WHERE id=%s", (producto_id,))

    def registrar_venta(self, carrito):
        """Guarda la venta y sus productos en una sola transaccion."""
        subtotal = sum(item["cantidad"] * item["precio"] for item in carrito.values())
        impuesto = round(subtotal * IMPUESTO, 2)
        total = round(subtotal + impuesto, 2)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        con = self.conectar()
        try:
            cursor = con.cursor()
            cursor.execute("""
                INSERT INTO ventas(fecha, subtotal, impuesto, total)
                VALUES (%s, %s, %s, %s)
            """, (fecha, subtotal, impuesto, total))
            venta_id = cursor.lastrowid

            for producto_id, item in carrito.items():
                importe = item["cantidad"] * item["precio"]
                cursor.execute("""
                    INSERT INTO detalle_ventas(
                        venta_id, producto_id, producto_nombre, categoria,
                        cantidad, precio_unitario, importe
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    venta_id, producto_id, item["nombre"], item["categoria"],
                    item["cantidad"], item["precio"], importe
                ))
            con.commit()
        except mysql.connector.Error:
            con.rollback()
            raise
        finally:
            con.close()

        return venta_id, fecha, subtotal, impuesto, total

    def obtener_ventas(self, limite=500):
        """Consulta las ventas mas recientes."""
        return self.consultar("""
            SELECT id, fecha, subtotal, impuesto, total
            FROM ventas
            ORDER BY id DESC
            LIMIT %s
        """, (limite,))

    def obtener_detalle_venta(self, venta_id):
        """Consulta los productos que pertenecen a una venta."""
        return self.consultar("""
            SELECT producto_nombre, categoria, cantidad,
                   precio_unitario, importe
            FROM detalle_ventas
            WHERE venta_id=%s
            ORDER BY id
        """, (venta_id,))

    def ingresos_totales(self):
        """Suma los importes de todas las ventas registradas."""
        fila = self.consultar(
            "SELECT COALESCE(SUM(total), 0) AS total FROM ventas", uno=True
        )
        return float(fila["total"])

    def datos_ventas_por_dia(self):
        return self.consultar("""
            SELECT DATE_FORMAT(fecha, '%Y-%m-%d') AS periodo, SUM(total) AS importe
            FROM ventas
            GROUP BY periodo
            ORDER BY periodo
        """)

    def datos_ventas_por_mes(self):
        return self.consultar("""
            SELECT DATE_FORMAT(fecha, '%Y-%m') AS periodo, SUM(total) AS importe
            FROM ventas
            GROUP BY periodo
            ORDER BY periodo
        """)

    def datos_productos_mas_vendidos(self):
        return self.consultar("""
            SELECT producto_nombre AS nombre, SUM(cantidad) AS cantidad
            FROM detalle_ventas
            GROUP BY producto_nombre
            ORDER BY cantidad DESC
            LIMIT 10
        """)

    def datos_ingresos_categoria(self):
        return self.consultar("""
            SELECT categoria, SUM(importe) AS importe
            FROM detalle_ventas
            GROUP BY categoria
            ORDER BY importe DESC
        """)


# ---------------------------------------------------------------------
# APLICACION E INTERFAZ GRAFICA
# ---------------------------------------------------------------------

class RestauranteApp:
    """Ventana principal y funciones de la aplicacion."""

    def __init__(self, ventana):
        self.ventana = ventana
        self.db = BaseDatos()
        self.carrito = {}
        self.venta_actual_id = None
        self.producto_seleccionado_id = None

        self.configurar_ventana()
        self.crear_estilos()
        self.crear_interfaz()
        self.actualizar_productos()
        self.actualizar_historial()
        self.actualizar_reportes()

    def configurar_ventana(self):
        self.ventana.title(f"{NOMBRE_RESTAURANTE} - Sistema de gestion")
        self.ventana.geometry("1280x780")
        self.ventana.minsize(1050, 680)
        self.ventana.configure(bg="#6F4E37")

    def crear_estilos(self):
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("TNotebook", background="#6F4E37", borderwidth=0)
        estilo.configure("TNotebook.Tab", padding=(16, 9), font=("Arial", 10, "bold"),
                         background="#D9BF9B", foreground="#4A2C17")
        estilo.map("TNotebook.Tab",
                   background=[("selected", "#FAF1E0")],
                   foreground=[("selected", "#4A2C17")])
        estilo.configure("Treeview", rowheight=27, font=("Arial", 10),
                         background="#FFFBF2", fieldbackground="#FFFBF2",
                         foreground="#4A2C17")
        estilo.map("Treeview",
                   background=[("selected", "#A67B5B")],
                   foreground=[("selected", "#FFFBF2")])
        estilo.configure("Treeview.Heading", font=("Arial", 10, "bold"),
                         background="#8B5A2B", foreground="#FFF8EC")
        estilo.configure("TButton", padding=7, font=("Arial", 10, "bold"),
                         background="#8B5A2B", foreground="#FFF8EC")
        estilo.map("TButton",
                   background=[("active", "#A67B5B")],
                   foreground=[("active", "#FFF8EC")])
        estilo.configure("Titulo.TLabel", font=("Arial", 22, "bold"),
                         foreground="#4A2C17", background="#F5E6D3")
        estilo.configure("Subtitulo.TLabel", font=("Arial", 12, "bold"),
                         foreground="#4A2C17", background="#F5E6D3")

    def crear_interfaz(self):
        encabezado = tk.Frame(self.ventana, bg="#F5E6D3")
        encabezado.pack(fill="x", padx=18, pady=(12, 5))

        tk.Label(
            encabezado, text=NOMBRE_RESTAURANTE,
            font=("Arial", 25, "bold"), fg="#4A2C17", bg="#F5E6D3"
        ).pack(side="left")

        tk.Label(
            encabezado, text="Sistema de ventas y administracion",
            font=("Arial", 10), fg="#8B5A2B", bg="#F5E6D3"
        ).pack(side="right", pady=12)

        self.pestanas = ttk.Notebook(self.ventana)
        self.pestanas.pack(fill="both", expand=True, padx=15, pady=10)

        self.tab_venta = tk.Frame(self.pestanas, bg="#FAF1E0")
        self.tab_productos = tk.Frame(self.pestanas, bg="#FAF1E0")
        self.tab_historial = tk.Frame(self.pestanas, bg="#FAF1E0")
        self.tab_reportes = tk.Frame(self.pestanas, bg="#FAF1E0")

        self.pestanas.add(self.tab_venta, text="  Ventas  ")
        self.pestanas.add(self.tab_productos, text="  Productos  ")
        self.pestanas.add(self.tab_historial, text="  Historial  ")
        self.pestanas.add(self.tab_reportes, text="  Reportes graficos  ")

        self.crear_pestana_ventas()
        self.crear_pestana_productos()
        self.crear_pestana_historial()
        self.crear_pestana_reportes()

    # ---------------------------- VENTAS ----------------------------

    def crear_pestana_ventas(self):
        marco = self.tab_venta
        tk.Label(marco, text="Registro de venta", font=("Arial", 17, "bold"),
                 bg="#FAF1E0", fg="#4A2C17").pack(anchor="w", padx=15, pady=12)

        controles = tk.Frame(marco, bg="#E8D3B0")
        controles.pack(fill="x", padx=15)

        tk.Label(controles, text="Producto:", bg="#E8D3B0", fg="#4A2C17").grid(row=0, column=0, padx=5)
        self.combo_producto = ttk.Combobox(controles, state="readonly", width=38)
        self.combo_producto.grid(row=0, column=1, padx=5, pady=8)

        tk.Label(controles, text="Cantidad:", bg="#E8D3B0", fg="#4A2C17").grid(row=0, column=2, padx=5)
        self.spin_cantidad = tk.Spinbox(controles, from_=1, to=999, width=7)
        self.spin_cantidad.grid(row=0, column=3, padx=5)

        ttk.Button(controles, text="Agregar al pedido",
                   command=self.agregar_al_carrito).grid(row=0, column=4, padx=10)

        zona = tk.Frame(marco, bg="#FAF1E0")
        zona.pack(fill="both", expand=True, padx=15, pady=8)

        marco_tabla = tk.LabelFrame(zona, text="Productos de la cuenta",
                                    bg="#FAF1E0", fg="#4A2C17", padx=8, pady=8)
        marco_tabla.pack(side="left", fill="both", expand=True, padx=(0, 8))

        columnas = ("producto", "categoria", "cantidad", "precio", "importe")
        self.tabla_carrito = ttk.Treeview(
            marco_tabla, columns=columnas, show="headings", height=14
        )
        encabezados = {
            "producto": "Producto", "categoria": "Categoria",
            "cantidad": "Cantidad", "precio": "Precio unitario", "importe": "Importe"
        }
        anchos = {"producto": 190, "categoria": 100, "cantidad": 75,
                  "precio": 110, "importe": 110}
        for col in columnas:
            self.tabla_carrito.heading(col, text=encabezados[col])
            self.tabla_carrito.column(col, width=anchos[col], anchor="center")
        self.tabla_carrito.pack(fill="both", expand=True)

        panel_derecho = tk.Frame(zona, bg="#EBD9BC", padx=15, pady=12)
        panel_derecho.pack(side="right", fill="y")

        tk.Label(panel_derecho, text="Resumen de cuenta",
                 font=("Arial", 14, "bold"), bg="#EBD9BC",
                 fg="#4A2C17").pack(pady=(4, 18))

        self.lbl_subtotal = tk.Label(panel_derecho, text="Subtotal: $ 0.00",
                                     font=("Arial", 11), bg="#EBD9BC", fg="#4A2C17")
        self.lbl_subtotal.pack(anchor="w", pady=6)
        self.lbl_impuesto = tk.Label(panel_derecho, text="Impuesto (7 %): $ 0.00",
                                     font=("Arial", 11), bg="#EBD9BC", fg="#4A2C17")
        self.lbl_impuesto.pack(anchor="w", pady=6)
        self.lbl_total = tk.Label(panel_derecho, text="TOTAL: $ 0.00",
                                  font=("Arial", 15, "bold"), bg="#EBD9BC",
                                  fg="#8A4B25")
        self.lbl_total.pack(anchor="w", pady=12)

        ttk.Button(panel_derecho, text="Quitar producto",
                   command=self.quitar_del_carrito).pack(fill="x", pady=5)
        ttk.Button(panel_derecho, text="Vaciar cuenta",
                   command=self.vaciar_carrito).pack(fill="x", pady=5)
        ttk.Button(panel_derecho, text="FINALIZAR Y GUARDAR VENTA",
                   command=self.finalizar_venta).pack(fill="x", pady=(18, 5))

        self.texto_recibo = tk.Text(marco, height=8, font=("Courier New", 9),
                                    wrap="none", bg="#FFFBF2", fg="#4A2C17")
        self.texto_recibo.pack(fill="x", padx=15, pady=(3, 12))
        self.texto_recibo.insert("1.0", "El recibo de la venta aparecera aqui.")

    def actualizar_productos_combo(self):
        self.productos_combo = self.db.obtener_productos()
        self.mapa_combo = {}
        opciones = []
        for p in self.productos_combo:
            etiqueta = f'{p["nombre"]} | {p["categoria"]} | {dinero(p["precio"])}'
            opciones.append(etiqueta)
            self.mapa_combo[etiqueta] = p
        self.combo_producto["values"] = opciones
        if opciones:
            self.combo_producto.current(0)
        else:
            self.combo_producto.set("")

    def agregar_al_carrito(self):
        seleccion = self.combo_producto.get()
        if not seleccion or seleccion not in self.mapa_combo:
            messagebox.showwarning("Producto", "Selecciona un producto.")
            return
        try:
            cantidad = int(self.spin_cantidad.get())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Cantidad", "Escribe una cantidad entera mayor que cero.")
            return

        producto = self.mapa_combo[seleccion]
        pid = producto["id"]
        if pid not in self.carrito:
            self.carrito[pid] = {
                "nombre": producto["nombre"],
                "categoria": producto["categoria"],
                "precio": float(producto["precio"]),
                "cantidad": 0
            }
        self.carrito[pid]["cantidad"] += cantidad
        self.refrescar_carrito()

    def refrescar_carrito(self):
        for fila in self.tabla_carrito.get_children():
            self.tabla_carrito.delete(fila)

        subtotal = 0
        for pid, item in self.carrito.items():
            importe = item["cantidad"] * item["precio"]
            subtotal += importe
            self.tabla_carrito.insert("", "end", iid=str(pid), values=(
                item["nombre"], item["categoria"], item["cantidad"],
                dinero(item["precio"]), dinero(importe)
            ))

        impuesto = round(subtotal * IMPUESTO, 2)
        total = round(subtotal + impuesto, 2)
        self.lbl_subtotal.config(text=f"Subtotal: {dinero(subtotal)}")
        self.lbl_impuesto.config(text=f"Impuesto ({IMPUESTO:.0%}): {dinero(impuesto)}")
        self.lbl_total.config(text=f"TOTAL: {dinero(total)}")

    def quitar_del_carrito(self):
        seleccion = self.tabla_carrito.selection()
        if not seleccion:
            messagebox.showinfo("Pedido", "Selecciona un producto de la cuenta.")
            return
        pid = int(seleccion[0])
        self.carrito.pop(pid, None)
        self.refrescar_carrito()

    def vaciar_carrito(self):
        if self.carrito and not messagebox.askyesno(
            "Confirmar", "¿Deseas vaciar todos los productos de la cuenta?"
        ):
            return
        self.carrito.clear()
        self.refrescar_carrito()

    def finalizar_venta(self):
        if not self.carrito:
            messagebox.showwarning("Venta", "Agrega al menos un producto.")
            return
        if not messagebox.askyesno("Confirmar venta", "¿Deseas guardar esta venta?"):
            return

        try:
            venta_id, fecha, subtotal, impuesto, total = self.db.registrar_venta(self.carrito)
        except mysql.connector.Error as error:
            messagebox.showerror("Base de datos", f"No se pudo guardar la venta:\n{error}")
            return

        lineas = [
            f"{NOMBRE_RESTAURANTE}",
            f"Recibo de venta No. {venta_id}",
            f"Fecha: {fecha}",
            "-" * 48,
            f"{'Producto':20} {'Cant.':>5} {'Importe':>12}",
            "-" * 48
        ]
        for item in self.carrito.values():
            importe = item["cantidad"] * item["precio"]
            lineas.append(
                f"{item['nombre'][:20]:20} {item['cantidad']:>5} {dinero(importe):>12}"
            )
        lineas.extend([
            "-" * 48,
            f"Subtotal: {dinero(subtotal)}",
            f"Impuesto ({IMPUESTO:.0%}): {dinero(impuesto)}",
            f"TOTAL: {dinero(total)}",
            "",
            "Gracias por su visita."
        ])
        recibo = "\n".join(lineas)
        self.texto_recibo.delete("1.0", "end")
        self.texto_recibo.insert("1.0", recibo)

        self.venta_actual_id = venta_id
        self.carrito.clear()
        self.refrescar_carrito()
        self.actualizar_historial()
        self.actualizar_reportes()
        messagebox.showinfo(
            "Venta guardada",
            f"La venta #{venta_id} se guardo correctamente.\nTotal: {dinero(total)}"
        )

    # -------------------------- PRODUCTOS ---------------------------

    def crear_pestana_productos(self):
        marco = self.tab_productos
        tk.Label(marco, text="Administracion de productos",
                 font=("Arial", 17, "bold"), bg="#FAF1E0",
                 fg="#4A2C17").pack(anchor="w", padx=15, pady=12)

        formulario = tk.LabelFrame(marco, text="Datos del producto",
                                   bg="#FAF1E0", fg="#4A2C17", padx=12, pady=12)
        formulario.pack(fill="x", padx=15, pady=5)

        tk.Label(formulario, text="Nombre:", bg="#FAF1E0", fg="#4A2C17").grid(row=0, column=0, padx=5)
        self.entry_nombre = ttk.Entry(formulario, width=25)
        self.entry_nombre.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(formulario, text="Categoria:", bg="#FAF1E0", fg="#4A2C17").grid(row=0, column=2, padx=5)
        self.combo_categoria = ttk.Combobox(
            formulario, values=["Comida", "Bebida", "Postre"], state="readonly", width=17
        )
        self.combo_categoria.grid(row=0, column=3, padx=5)
        self.combo_categoria.current(0)

        tk.Label(formulario, text="Precio:", bg="#FAF1E0", fg="#4A2C17").grid(row=0, column=4, padx=5)
        self.entry_precio = ttk.Entry(formulario, width=12)
        self.entry_precio.grid(row=0, column=5, padx=5)

        ttk.Button(formulario, text="Guardar producto",
                   command=self.guardar_producto).grid(row=0, column=6, padx=8)
        ttk.Button(formulario, text="Limpiar",
                   command=self.limpiar_formulario_producto).grid(row=0, column=7, padx=4)

        columnas = ("id", "nombre", "categoria", "precio", "estado")
        self.tabla_productos = ttk.Treeview(
            marco, columns=columnas, show="headings", height=17
        )
        for col, titulo, ancho in [
            ("id", "ID", 60), ("nombre", "Nombre", 260),
            ("categoria", "Categoria", 160), ("precio", "Precio", 130),
            ("estado", "Estado", 100)
        ]:
            self.tabla_productos.heading(col, text=titulo)
            self.tabla_productos.column(col, width=ancho, anchor="center")
        self.tabla_productos.pack(fill="both", expand=True, padx=15, pady=10)
        self.tabla_productos.bind("<<TreeviewSelect>>", self.seleccionar_producto)

        acciones = tk.Frame(marco, bg="#FAF1E0")
        acciones.pack(fill="x", padx=15, pady=(0, 12))
        ttk.Button(acciones, text="Actualizar lista",
                   command=self.actualizar_productos).pack(side="left", padx=4)
        ttk.Button(acciones, text="Desactivar producto seleccionado",
                   command=self.eliminar_producto).pack(side="left", padx=4)

    def actualizar_productos(self):
        if not hasattr(self, "tabla_productos"):
            return
        for fila in self.tabla_productos.get_children():
            self.tabla_productos.delete(fila)
        for p in self.db.obtener_productos(incluir_inactivos=True):
            estado = "Activo" if p["activo"] else "Inactivo"
            self.tabla_productos.insert("", "end", iid=str(p["id"]), values=(
                p["id"], p["nombre"], p["categoria"], dinero(p["precio"]), estado
            ))
        if hasattr(self, "combo_producto"):
            self.actualizar_productos_combo()

    def seleccionar_producto(self, _evento=None):
        seleccion = self.tabla_productos.selection()
        if not seleccion:
            return
        pid = int(seleccion[0])
        producto = next(
            (p for p in self.db.obtener_productos(incluir_inactivos=True) if p["id"] == pid),
            None
        )
        if producto is None:
            return
        self.producto_seleccionado_id = pid
        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, producto["nombre"])
        self.combo_categoria.set(producto["categoria"])
        self.entry_precio.delete(0, "end")
        self.entry_precio.insert(0, str(producto["precio"]))

    def limpiar_formulario_producto(self):
        self.producto_seleccionado_id = None
        self.entry_nombre.delete(0, "end")
        self.entry_precio.delete(0, "end")
        self.combo_categoria.current(0)
        self.tabla_productos.selection_remove(self.tabla_productos.selection())

    def guardar_producto(self):
        nombre = self.entry_nombre.get().strip()
        categoria = self.combo_categoria.get().strip()
        try:
            precio = float(self.entry_precio.get().replace(",", "."))
            if precio < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Precio", "Escribe un precio numerico igual o mayor que cero.")
            return
        if not nombre:
            messagebox.showwarning("Producto", "Escribe el nombre del producto.")
            return
        if categoria not in ("Comida", "Bebida", "Postre"):
            messagebox.showwarning("Categoria", "Selecciona una categoria valida.")
            return

        try:
            self.db.guardar_producto(self.producto_seleccionado_id, nombre, categoria, precio)
        except mysql.connector.IntegrityError:
            messagebox.showerror("Producto", "Ya existe un producto con ese nombre.")
            return
        except mysql.connector.Error as error:
            messagebox.showerror("Base de datos", str(error))
            return

        self.limpiar_formulario_producto()
        self.actualizar_productos()
        messagebox.showinfo("Productos", "El producto se guardo correctamente.")

    def eliminar_producto(self):
        seleccion = self.tabla_productos.selection()
        if not seleccion:
            messagebox.showwarning("Productos", "Selecciona un producto.")
            return
        pid = int(seleccion[0])
        if not messagebox.askyesno(
            "Confirmar", "El producto se desactivara y ya no aparecera en nuevas ventas."
        ):
            return
        self.db.desactivar_producto(pid)
        self.limpiar_formulario_producto()
        self.actualizar_productos()
        messagebox.showinfo("Productos", "Producto desactivado.")

    # --------------------------- HISTORIAL --------------------------

    def crear_pestana_historial(self):
        marco = self.tab_historial
        tk.Label(marco, text="Historial de ventas",
                 font=("Arial", 17, "bold"), bg="#FAF1E0",
                 fg="#4A2C17").pack(anchor="w", padx=15, pady=12)

        columnas = ("id", "fecha", "subtotal", "impuesto", "total")
        self.tabla_historial = ttk.Treeview(
            marco, columns=columnas, show="headings", height=15
        )
        for col, titulo, ancho in [
            ("id", "Folio", 80), ("fecha", "Fecha y hora", 220),
            ("subtotal", "Subtotal", 150), ("impuesto", "Impuesto", 150),
            ("total", "Total", 150)
        ]:
            self.tabla_historial.heading(col, text=titulo)
            self.tabla_historial.column(col, width=ancho, anchor="center")
        self.tabla_historial.pack(fill="both", expand=True, padx=15, pady=8)
        self.tabla_historial.bind("<<TreeviewSelect>>", self.mostrar_detalle_historial)

        ttk.Button(marco, text="Actualizar historial",
                   command=self.actualizar_historial).pack(anchor="w", padx=15, pady=5)

        self.detalle_historial = tk.Text(marco, height=9, font=("Courier New", 9),
                                         bg="#FFFBF2", fg="#4A2C17")
        self.detalle_historial.pack(fill="x", padx=15, pady=8)

    def actualizar_historial(self):
        if not hasattr(self, "tabla_historial"):
            return
        for fila in self.tabla_historial.get_children():
            self.tabla_historial.delete(fila)
        for venta in self.db.obtener_ventas():
            self.tabla_historial.insert("", "end", iid=str(venta["id"]), values=(
                venta["id"], str(venta["fecha"]), dinero(venta["subtotal"]),
                dinero(venta["impuesto"]), dinero(venta["total"])
            ))

    def mostrar_detalle_historial(self, _evento=None):
        seleccion = self.tabla_historial.selection()
        if not seleccion:
            return
        venta_id = int(seleccion[0])
        detalles = self.db.obtener_detalle_venta(venta_id)
        self.detalle_historial.delete("1.0", "end")
        self.detalle_historial.insert("end", f"DETALLE DE LA VENTA #{venta_id}\n")
        self.detalle_historial.insert("end", "-" * 65 + "\n")
        for item in detalles:
            self.detalle_historial.insert(
                "end",
                f'{item["producto_nombre"]} | {item["categoria"]} | '
                f'{item["cantidad"]} x {dinero(item["precio_unitario"])} = '
                f'{dinero(item["importe"])}\n'
            )

    # ---------------------------- REPORTES --------------------------

    def crear_pestana_reportes(self):
        marco = self.tab_reportes
        tk.Label(marco, text="Reportes y estadisticas",
                 font=("Arial", 17, "bold"), bg="#FAF1E0",
                 fg="#4A2C17").pack(anchor="w", padx=15, pady=12)

        resumen = tk.Frame(marco, bg="#EBD9BC", padx=15, pady=12)
        resumen.pack(fill="x", padx=15, pady=5)

        self.lbl_ingresos_totales = tk.Label(
            resumen, text="Ingresos totales: $ 0.00",
            font=("Arial", 17, "bold"), fg="#4A2C17", bg="#EBD9BC"
        )
        self.lbl_ingresos_totales.pack(side="left", padx=10)

        self.lbl_num_ventas = tk.Label(
            resumen, text="Ventas registradas: 0",
            font=("Arial", 12, "bold"), bg="#EBD9BC", fg="#4A2C17"
        )
        self.lbl_num_ventas.pack(side="right", padx=10)

        barra = tk.Frame(marco, bg="#FAF1E0")
        barra.pack(fill="x", padx=15, pady=8)
        tk.Label(barra, text="Tipo de reporte:", bg="#FAF1E0", fg="#4A2C17").pack(side="left")
        self.combo_reporte = ttk.Combobox(
            barra, state="readonly", width=32,
            values=[
                "Ventas por dia",
                "Productos mas vendidos",
                "Ingresos por categoria",
                "Ventas por mes"
            ]
        )
        self.combo_reporte.pack(side="left", padx=8)
        self.combo_reporte.current(0)
        ttk.Button(barra, text="Mostrar grafica",
                   command=self.dibujar_grafica).pack(side="left", padx=5)
        ttk.Button(barra, text="Actualizar reportes",
                   command=self.actualizar_reportes).pack(side="left", padx=5)

        self.marco_grafica = tk.Frame(marco, bg="#FFFBF2")
        self.marco_grafica.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        if not MATPLOTLIB_DISPONIBLE:
            tk.Label(
                self.marco_grafica,
                text="Para mostrar las graficas instala Matplotlib:\n"
                     "python -m pip install matplotlib",
                font=("Arial", 13), bg="#FFFBF2", fg="#8A4B25"
            ).pack(expand=True)
        else:
            self.figura = Figure(figsize=(9, 4.5), dpi=100)
            self.ejes = self.figura.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.figura, master=self.marco_grafica)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self.dibujar_grafica()

    def actualizar_reportes(self):
        total = self.db.ingresos_totales()
        ventas = self.db.obtener_ventas(limite=100000)
        if hasattr(self, "lbl_ingresos_totales"):
            self.lbl_ingresos_totales.config(
                text=f"Ingresos totales: {dinero(total)}"
            )
            self.lbl_num_ventas.config(text=f"Ventas registradas: {len(ventas)}")
        if MATPLOTLIB_DISPONIBLE and hasattr(self, "canvas"):
            self.dibujar_grafica()

    def dibujar_grafica(self):
        if not MATPLOTLIB_DISPONIBLE or not hasattr(self, "ejes"):
            return

        tipo = self.combo_reporte.get()
        self.ejes.clear()
        self.figura.patch.set_facecolor("#FFFBF2")
        self.ejes.set_facecolor("#FAF1E0")

        if tipo == "Ventas por dia":
            datos = self.db.datos_ventas_por_dia()
            etiquetas = [fila["periodo"] for fila in datos]
            valores = [float(fila["importe"]) for fila in datos]
            self.ejes.bar(etiquetas, valores, color="#8B5A2B")
            self.ejes.set_title("Ingresos por dia", color="#4A2C17")
            self.ejes.set_ylabel("Importe")
            self.ejes.set_xlabel("Fecha")
            self.ejes.tick_params(axis="x", rotation=40)

        elif tipo == "Productos mas vendidos":
            datos = self.db.datos_productos_mas_vendidos()
            etiquetas = [fila["nombre"] for fila in datos]
            valores = [float(fila["cantidad"]) for fila in datos]
            self.ejes.barh(etiquetas[::-1], valores[::-1], color="#A67B5B")
            self.ejes.set_title("Los 10 productos mas vendidos", color="#4A2C17")
            self.ejes.set_xlabel("Unidades vendidas")

        elif tipo == "Ingresos por categoria":
            datos = self.db.datos_ingresos_categoria()
            etiquetas = [fila["categoria"] for fila in datos]
            valores = [float(fila["importe"]) for fila in datos]
            if valores:
                self.ejes.pie(
                    valores, labels=etiquetas, autopct="%1.1f%%",
                    startangle=90,
                    colors=["#6F4E37", "#A67B5B", "#D9BF9B", "#C19A6B"]
                )
                self.ejes.set_title("Distribucion de ingresos por categoria", color="#4A2C17")
                self.ejes.axis("equal")
            else:
                self.ejes.text(0.5, 0.5, "Todavia no hay ventas registradas",
                               ha="center", va="center", transform=self.ejes.transAxes)

        elif tipo == "Ventas por mes":
            datos = self.db.datos_ventas_por_mes()
            etiquetas = [fila["periodo"] for fila in datos]
            valores = [float(fila["importe"]) for fila in datos]
            self.ejes.bar(etiquetas, valores, color="#8B5A2B")
            self.ejes.set_title("Ingresos por mes", color="#4A2C17")
            self.ejes.set_ylabel("Importe")
            self.ejes.set_xlabel("Mes")
            self.ejes.tick_params(axis="x", rotation=35)

        if tipo != "Ingresos por categoria" and not (
            self.db.datos_ventas_por_dia() if tipo == "Ventas por dia"
            else self.db.datos_productos_mas_vendidos() if tipo == "Productos mas vendidos"
            else self.db.datos_ventas_por_mes()
        ):
            self.ejes.text(0.5, 0.5, "Todavia no hay ventas registradas",
                           ha="center", va="center", transform=self.ejes.transAxes)

        self.figura.tight_layout()
        self.canvas.draw()


# ---------------------------------------------------------------------
# INICIO DEL PROGRAMA
# ---------------------------------------------------------------------

if __name__ == "__main__":
    ventana_principal = tk.Tk()
    try:
        aplicacion = RestauranteApp(ventana_principal)
    except mysql.connector.Error as error:
        messagebox.showerror(
            "MySQL",
            "No se pudo conectar a MySQL.\n"
            "Abre XAMPP y pulsa Start en MySQL.\n\n"
            f"Detalle: {error}"
        )
        ventana_principal.destroy()
    else:
        ventana_principal.mainloop()