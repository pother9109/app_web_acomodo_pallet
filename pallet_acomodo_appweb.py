
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from math import pi
import zipfile
import os
import base64

st.set_page_config(page_title="Acomodo de Pallets – SINSA", layout="wide")


# Logo de SINSA en el sidebar
with st.sidebar:
    logo_path = "images.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
            st.markdown(f"<img src='data:image/png;base64,{encoded}' width='150'>", unsafe_allow_html=True)
    st.markdown("## Configuración del Pallet")

# Icono de pallet como encabezado en la app
pallet_icon_path = "paleta.png"
if os.path.exists(pallet_icon_path):
    with open(pallet_icon_path, "rb") as icon_file:
        encoded_icon = base64.b64encode(icon_file.read()).decode()
        st.markdown(
            f"""
            <div style='display: flex; align-items: center;'>
                <img src="data:image/png;base64,{encoded_icon}" width="60">
                <h1 style='color:#56B948; padding-left: 15px;'>Acomodo de múltiples SKUs en pallets</h1>
            </div>
            <hr style="border-top: 4px solid #F7941D;">
            """,
            unsafe_allow_html=True
        )
else:
    st.title("Acomodo de múltiples SKUs en pallets")


st.sidebar.markdown("<h2 style='color:#F7941D;'>Configuración del Pallet</h2>", unsafe_allow_html=True)
pallet_length = st.sidebar.number_input("Largo del pallet (cm)", value=120.0, format="%.2f")
pallet_width = st.sidebar.number_input("Ancho del pallet (cm)", value=100.0, format="%.2f")
pallet_max_height = st.sidebar.number_input("Altura máxima (cm)", value=130.0, format="%.2f")
pallet_base_height = st.sidebar.number_input("Altura del polín (cm)", value=14.5, format="%.2f")
pallet_effective_height = pallet_max_height - pallet_base_height
pallet_max_weight = st.sidebar.number_input("Peso máximo (kg)", value=1250.0, format="%.2f")

st.sidebar.markdown("<h3 style='color:#F7941D;'>Sube tu archivo Excel</h3>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("Archivo de productos (varios SKUs)", type=["xlsx"])

st.markdown("""
    <style>
    .stButton>button {
        background-color: #F7941D;
        color: white;
        font-weight: bold;
    }
    .stDownloadButton>button {
        background-color: #56B948;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

def generar_acomodo(largo, ancho, alto, peso, is_cilindro=False):
    def calcular_posiciones(l, a, over_l, over_a):
        espacio_util_l = pallet_length + 2 * over_l
        espacio_util_a = pallet_width + 2 * over_a
        cols = int(espacio_util_l // l)
        rows = int(espacio_util_a // a)
        return cols, rows, cols * rows

    cols_0, rows_0, total_0 = calcular_posiciones(largo, ancho, 0, 0)
    over_l = 0.2 * largo if largo >= 20 else 0
    over_a = 0.2 * ancho if ancho >= 40 else 0
    cols_1, rows_1, total_1 = calcular_posiciones(largo, ancho, over_l, over_a)

    usar_overhang = total_1 > total_0

    cols = cols_1 if usar_overhang else cols_0
    rows = rows_1 if usar_overhang else rows_0

    max_layers = int(pallet_effective_height // alto)
    posiciones = []
    peso_total = 0

    offset_x = (max(pallet_length, cols * largo) - (cols * largo)) / 2
    offset_y = (max(pallet_width, rows * ancho) - (rows * ancho)) / 2

    for layer in range(max_layers):
        for row in range(rows):
            for col in range(cols):
                if peso_total + peso > pallet_max_weight:
                    continue
                x = col * largo + offset_x
                y = row * ancho + offset_y
                z = layer * alto
                if z + alto <= pallet_effective_height:
                    posiciones.append({
                        "x": x, "y": y, "z": z,
                        "largo": largo, "ancho": ancho, "alto": alto,
                        "is_cilindro": is_cilindro
                    })
                    peso_total += peso
    return posiciones


def dibujar_3d(posiciones, titulo):
    # Dibujar pallet base en color café claro
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111, projection='3d')

    pallet_thickness = 5
    base = [
        [0, 0, 0], [pallet_length, 0, 0], [pallet_length, pallet_width, 0], [0, pallet_width, 0],
        [0, 0, pallet_thickness], [pallet_length, 0, pallet_thickness],
        [pallet_length, pallet_width, pallet_thickness], [0, pallet_width, pallet_thickness]
    ]
    faces_base = [
        [base[0], base[1], base[2], base[3]],
        [base[4], base[5], base[6], base[7]],
        [base[0], base[1], base[5], base[4]],
        [base[2], base[3], base[7], base[6]],
        [base[1], base[2], base[6], base[5]],
        [base[4], base[7], base[3], base[0]]
    ]
    ax.add_collection3d(Poly3DCollection(faces_base, facecolors='#8B4513', edgecolors='k', linewidths=0.5, alpha=1.0))

    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111, projection='3d')
    for obj in posiciones:
        x, y, z = obj["x"], obj["y"], obj["z"]
        if obj.get("is_cilindro", False):
            r = obj["largo"] / 2
            h = obj["alto"]
            theta = np.linspace(0, 2 * np.pi, 30)
            z_vals = np.linspace(z, z + h, 2)
            theta_grid, z_grid = np.meshgrid(theta, z_vals)
            x_cyl = x + r + r * np.cos(theta_grid)
            y_cyl = y + r + r * np.sin(theta_grid)
            ax.plot_surface(x_cyl, y_cyl, z_grid, color='tomato', edgecolor='k', alpha=0.8)
        else:
            dx, dy, dz = obj["largo"], obj["ancho"], obj["alto"]
            box = [
                [x, y, z], [x+dx, y, z], [x+dx, y+dy, z], [x, y+dy, z],
                [x, y, z+dz], [x+dx, y, z+dz], [x+dx, y+dy, z+dz], [x, y+dy, z+dz]
            ]
            faces = [
                [box[0], box[1], box[2], box[3]],
                [box[4], box[5], box[6], box[7]],
                [box[0], box[1], box[5], box[4]],
                [box[2], box[3], box[7], box[6]],
                [box[1], box[2], box[6], box[5]],
                [box[4], box[7], box[3], box[0]]
            ]
            ax.add_collection3d(Poly3DCollection(faces, facecolors='lightblue', edgecolors='k', linewidths=0.5, alpha=0.85))
    ax.set_xlim([0, pallet_length])
    ax.set_ylim([0, pallet_width])
    ax.set_zlim([0, pallet_max_height])
    ax.set_xlabel("Largo (cm)")
    ax.set_ylabel("Ancho (cm)")
    ax.set_zlabel("Alto (cm)")
    ax.set_title(titulo)
    return fig

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("📋 Tabla de entrada:")
    st.dataframe(df)

    zip_buffer = BytesIO()
    resultados = []
    graficos = {}

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:
        for index, row in df.iterrows():
            tipo = row["Tipo"].strip().lower()
            largo = row["Largo"]
            ancho = row["Ancho"]
            alto = row["Alto"]
            peso = row["Peso"]
            nombre = str(row["SKU"]) if "SKU" in row else f"SKU_{index+1}"
            # Validación de desbordamiento no permitido
            if largo > pallet_length + 15 or ancho > pallet_width + 15:
                st.error(f"❌ El SKU '{nombre}' tiene dimensiones que exceden el desbordamiento permitido (15 cm). No se simulará.")
                continue


            if tipo == "caja":
                pos1 = generar_acomodo(largo, ancho, alto, peso)
                pos2 = generar_acomodo(ancho, largo, alto, peso)
                posiciones = pos1 if len(pos1) >= len(pos2) else pos2
                cajas_por_cama = max(len(set([p["x"] for p in posiciones])) * len(set([p["y"] for p in posiciones])), 1)
            else:
                posiciones = generar_acomodo(ancho, ancho, alto, peso, is_cilindro=True)
                cajas_por_cama = max(len(set([p["x"] for p in posiciones])) * len(set([p["y"] for p in posiciones])), 1)


            largo_min = min([p["x"] for p in posiciones])
            largo_max = max([p["x"] + p["largo"] for p in posiciones])
            largo_final = max(largo_max - largo_min, pallet_length)
            ancho_min = min([p["y"] for p in posiciones])
            ancho_max = max([p["y"] + p["ancho"] for p in posiciones])
            ancho_final = max(ancho_max - ancho_min, pallet_width)
            alto_final = max([p["z"] + p["alto"] for p in posiciones], default=0) + pallet_base_height
            total_cajas = len(posiciones)
            camas_completas = total_cajas // cajas_por_cama if cajas_por_cama else 0
            cajas_incompletas = total_cajas % cajas_por_cama
            peso_total = total_cajas * peso
            vol_unit = largo * ancho * alto if tipo == "caja" else pi * (ancho/2)**2 * alto
            vol_total = vol_unit * total_cajas
            vol_max = pallet_length * pallet_width * pallet_max_height

            fig = dibujar_3d(posiciones, f"{nombre} – {tipo.upper()}")
            graficos[nombre] = fig

            
            fig.text(0.02, 0.95, f"{nombre} – {tipo.upper()}", fontsize=12, weight='bold')
            fig.text(0.02, 0.91, f"Medidas finales: Largo {largo_final:.2f} cm | Ancho {ancho_final:.2f} cm | Alto {alto_final:.2f} cm", fontsize=10)
            fig.text(0.02, 0.87, f"Camas completas: {camas_completas} | Cajas en última cama: {cajas_incompletas}", fontsize=10)
            fig.text(0.02, 0.83, f"Peso total: {peso_total:.1f} kg ({(peso_total/pallet_max_weight)*100:.1f}%)", fontsize=10)
            fig.text(0.02, 0.79, f"Volumen: {vol_total:,.0f} cm³ ({(vol_total/vol_max)*100:.1f}%)", fontsize=10)
            
            
            pdf_buffer = BytesIO()
            with PdfPages(pdf_buffer) as pdf:
                # Página 1: Visualización 3D del acomodo
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # Página 2: Caja 3D con medidas
                
                
                unidades = int(row.get("Unidades", 0))
                fig_box = plt.figure(figsize=(8.5, 11))  # Tamaño carta en pulgadas
                ax_box = fig_box.add_subplot(111, projection='3d')
                dx, dy, dz = largo, ancho, alto
                x, y, z = 0, 0, 0
                box = [
                    [x, y, z], [x+dx, y, z], [x+dx, y+dy, z], [x, y+dy, z],
                    [x, y, z+dz], [x+dx, y, z+dz], [x+dx, y+dy, z+dz], [x, y+dy, z+dz]
                ]
                faces = [
                    [box[0], box[1], box[2], box[3]],
                    [box[4], box[5], box[6], box[7]],
                    [box[0], box[1], box[5], box[4]],
                    [box[2], box[3], box[7], box[6]],
                    [box[1], box[2], box[6], box[5]],
                    [box[4], box[7], box[3], box[0]]
                ]
                ax_box.add_collection3d(Poly3DCollection(
                    faces, facecolors='peru', edgecolors='k', linewidths=1, alpha=1.0, hatch='///'))

                # Acotaciones con fondo verde y texto blanco
                def etiqueta_con_fondo(x, y, z, texto, ha='center', rotation=0):
                    ax_box.text(x, y, z, texto, ha=ha, fontsize=10, rotation=rotation,
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='green', edgecolor='none'),
                                color='white')

                ax_box.plot([0, dx], [-dy*0.2, -dy*0.2], [0, 0], color='black', linestyle='dotted')
                etiqueta_con_fondo(dx/2, -dy*0.25, 0, f"Largo: {dx:.1f} cm")

                ax_box.plot([dx + dx*0.1]*2, [0, dy], [0, 0], color='black', linestyle='dotted')
                etiqueta_con_fondo(dx + dx*0.15, dy/2, 0, f"Ancho: {dy:.1f} cm", rotation=90)

                ax_box.plot([0, 0], [-dy*0.2, -dy*0.2], [0, dz], color='black', linestyle='dotted')
                etiqueta_con_fondo(0, -dy*0.25, dz/2, f"Alto: {dz:.1f} cm")

                ax_box.set_xlim([0, max(dx, dy) * 1.5])
                ax_box.set_ylim([min(-dy * 0.5, 0), dy * 1.5])
                ax_box.set_zlim([0, dz * 1.5])
                ax_box.set_axis_off()
                fig_box.suptitle(f"{nombre} – Caja 3D con textura y medidas (Unidades: {unidades})", fontsize=12, weight='bold')
                pdf.savefig(fig_box, bbox_inches="tight")
                plt.close(fig_box)



            zipf.writestr(f"{nombre}.pdf", pdf_buffer.getvalue())



            resultados.append({
                "SKU": nombre,
                "Tipo": tipo.title(),
                "Cajas por cama": cajas_por_cama,
                "Camas completas": camas_completas,
                "Cajas en última cama (incompleta)": cajas_incompletas,
                "Total cajas por pallet": total_cajas,
                "Peso total (kg)": peso_total,
                "% peso ocupado": f"{(peso_total/pallet_max_weight)*100:.1f}%",
                "Volumen ocupado (cm3)": int(vol_total),
                "% volumen ocupado": f"{(vol_total/vol_max)*100:.1f}%",
                "Largo final del acomodo (cm)": round(largo_final, 2),
                "Ancho final del acomodo (cm)": round(ancho_final, 2),
                "Alto final del acomodo (cm)": round(alto_final, 2)
            })

        df_out = pd.DataFrame(resultados)
        excel_buffer = BytesIO()
        df_out.to_excel(excel_buffer, index=False)
        zipf.writestr("resumen_consolidado.xlsx", excel_buffer.getvalue())

    st.success("✅ Simulación completada para todos los SKUs.")
    st.download_button("📦 Descargar resultados (ZIP)", zip_buffer.getvalue(), file_name="acomodo_skus.zip")

    st.subheader("📈 Resultados por SKU:")
    st.dataframe(df_out)

    
    
    st.subheader("🎯 Visualizador de acomodo 3D")

    skus = df_out["SKU"].tolist()

    if "sku_index" not in st.session_state:
        st.session_state.sku_index = 0

    # Selectbox sincronizado con el índice
    selected_sku = st.selectbox("Selecciona un SKU para ver su acomodo 3D", skus, index=st.session_state.sku_index)
    st.session_state.sku_index = skus.index(selected_sku)

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("⏮️ Anterior"):
            st.session_state.sku_index = (st.session_state.sku_index - 1) % len(skus)
    with col2:
        if st.button("⏭️ Siguiente"):
            st.session_state.sku_index = (st.session_state.sku_index + 1) % len(skus)

    selected_sku = skus[st.session_state.sku_index]
    st.markdown(f"**SKU actual seleccionado:** `{selected_sku}`")

    st.pyplot(graficos[selected_sku])


