# Instalar y usar en Mac (instructivo corto)

Probado en un Mac con chip Apple (2026-11-22). Necesita internet y unos 3 GB libres.

**1. Bajar el código.** En GitHub: **Code → Download ZIP**. Si no se descomprime solo, doble clic en el ZIP en Descargas.

**2. Abrir la Terminal.** ⌘ + Espacio, escribir "Terminal" y Enter.

**3. Instalar** (una sola vez, unos 10 min; termina con "Listo."):

```bash
cd ~/Downloads/dti-alps-atlas-main && bash app/instalar.sh
```

**4. Abrir la app** (también las próximas veces):

```bash
cd ~/Downloads/dti-alps-atlas-main && bash app/abrir_app.command
```

**5. Procesar.** En la app: **Subir archivos** → seleccionar juntos (⌘ + clic) el `.nii.gz`, el `.bval` y el `.bvec` →
**Procesar** (30 a 40 min).

Para cerrar la app: **Ctrl + C** en la Terminal.

**Desinstalar:** todo queda dentro de la carpeta del repositorio, salvo las cachés de Streamlit y matplotlib (bórrelas
solo si no usa esos programas para otra cosa):

```bash
rm -rf ~/Downloads/dti-alps-atlas-main ~/.streamlit ~/.matplotlib
```
