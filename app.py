# ---------------------------------------------------------
# GENERADOR DE INFORME EJECUTIVO CON PLANTILLA CORPORATIVA
# ---------------------------------------------------------
class CorporateTemplateCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # 1. ENCABEZADO CORPORATIVO (IMAGEN DE PLANTILLA)
        header_img_path = "logo_header.png"
        if not os.path.exists(header_img_path):
            header_img_path = "extracted_media/image1.jpeg"
            
        if os.path.exists(header_img_path):
            try:
                self.drawImage(header_img_path, 36, 735, width=540, height=45, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        else:
            # Fallback en colores institucionales si no hay imagen
            self.setFillColor(colors.HexColor("#0077C8"))
            self.rect(0, 772, 612, 20, fill=True, stroke=False)
            self.setFillColor(colors.HexColor("#7AB800"))
            self.rect(0, 768, 612, 4, fill=True, stroke=False)

        # 2. PIE DE PÁGINA CORPORATIVO (SELLOS Y MARCA)
        footer_img_path = "logo_footer.png"
        if not os.path.exists(footer_img_path):
            footer_img_path = "extracted_media/image2.png"
            
        if os.path.exists(footer_img_path):
            try:
                self.drawImage(footer_img_path, 36, 30, width=540, height=35, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        # Números de página y fecha
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))
        self.drawString(36, 18, f"La Terminal S.A. | Informe de Gestión Trimestral - Emitido el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        self.drawRightString(576, 18, f"Página {self._pageNumber} de {page_count}")
        
        self.setStrokeColor(colors.HexColor("#CCCCCC"))
        self.setLineWidth(0.5)
        self.line(36, 725, 576, 725)
        self.line(36, 68, 576, 68)
        
        self.restoreState()

def generar_pdf_informe_trimestral(entorno_nombre, anio_sel, trim_sel, df_base_input):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=75,
        bottomMargin=80
    )

    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor("#0077C8"), alignment=0, spaceAfter=4)
    style_subtitle = ParagraphStyle('DocSub', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.HexColor("#555555"), alignment=0, spaceAfter=12)
    style_sec_head = ParagraphStyle('SecHead', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor("#0077C8"), spaceBefore=10, spaceAfter=6)
    style_body = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor("#222222"))
    style_table_cell = ParagraphStyle('TableCell', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor("#222222"))
    style_table_header = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white, alignment=1)

    elements = []

    # Título principal del documento
    elements.append(Paragraph(f"INFORME EJECUTIVO DE GESTIÓN - {entorno_nombre.upper()}", style_title))
    elements.append(Paragraph(f"Corte Evaluado: <b>{trim_sel} - Vigencia {anio_sel}</b>", style_subtitle))

    # Selección de meses según trimestre
    map_trim_meses = {
        "Trimestre 1 (Q1)": [1, 2, 3],
        "Trimestre 2 (Q2)": [4, 5, 6],
        "Trimestre 3 (Q3)": [7, 8, 9],
        "Trimestre 4 (Q4)": [10, 11, 12]
    }
    meses_trim = map_trim_meses.get(trim_sel, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

    df_inf = df_base_input.copy()
    
    col_cierre = "Cierre" if "Cierre" in df_inf.columns else ("FECHA DE TERMINACIÓN" if "FECHA DE TERMINACIÓN" in df_inf.columns else df_inf.columns[8])
    col_estado = "Estado" if "Estado" in df_inf.columns else ("ESTADO" if "ESTADO" in df_inf.columns else df_inf.columns[11])
    col_resp = "Responsable" if "Responsable" in df_inf.columns else ("AREA RESPONSABLE" if "AREA RESPONSABLE" in df_inf.columns else df_inf.columns[6])
    col_riesgo = "Nivel del Riesgo" if "Nivel del Riesgo" in df_inf.columns else None
    col_hallaz = "Transcribir el del Hallazgo o Situación Evidenciada" if "Transcribir el del Hallazgo o Situación Evidenciada" in df_inf.columns else ("DESCRIPCIÓN HALLAZGO" if "DESCRIPCIÓN HALLAZGO" in df_inf.columns else df_inf.columns[2])
    col_id = "ID" if "ID" in df_inf.columns else ("No. HALLAZGO" if "No. HALLAZGO" in df_inf.columns else df_inf.columns[0])

    df_inf['Fecha_DT'] = df_inf[col_cierre].apply(parsear_fecha_estricta)
    
    mask_trim = (df_inf['Fecha_DT'].dt.year == int(anio_sel)) & (df_inf['Fecha_DT'].dt.month.isin(meses_trim))
    df_q = df_inf[mask_trim].copy()

    # Cálculo de Métricas
    total_pendientes = len(df_q[~df_q[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)])
    abiertos_cnt = len(df_q[df_q[col_estado].astype(str).str.contains("Abiert", case=False, na=False)])
    vencidos_cnt = len(df_q[df_q[col_estado].astype(str).str.contains("Vencid", case=False, na=False)])
    
    pct_venc = round((vencidos_cnt / total_pendientes * 100), 1) if total_pendientes > 0 else 0.0

    r_alto = len(df_q[df_q[col_riesgo].astype(str).str.contains("Alto", case=False, na=False)]) if col_riesgo and col_riesgo in df_q.columns else 0
    r_medio = len(df_q[df_q[col_riesgo].astype(str).str.contains("Medio", case=False, na=False)]) if col_riesgo and col_riesgo in df_q.columns else 0
    r_bajo = len(df_q[df_q[col_riesgo].astype(str).str.contains("Bajo", case=False, na=False)]) if col_riesgo and col_riesgo in df_q.columns else 0

    top_area_str = "N/A"
    if not df_q.empty and col_resp in df_q.columns:
        df_q_pend = df_q[~df_q[col_estado].astype(str).str.contains("Finaliz|Cerrad", case=False, na=False)].copy()
        if not df_q_pend.empty:
            df_q_pend['Resp_Clean'] = df_q_pend[col_resp].astype(str).str.replace("\n", ",").str.split(",")
            df_exp = df_q_pend.explode('Resp_Clean')
            df_exp['Resp_Clean'] = df_exp['Resp_Clean'].apply(limpiar_nombre_area)
            df_exp = df_exp[~df_exp['Resp_Clean'].isin(["", "NAN", "NONE"])]
            if not df_exp.empty:
                top_area_str = df_exp['Resp_Clean'].value_counts().index[0]

    # SECCIÓN 1: RESUMEN EJECUTIVO
    elements.append(Paragraph("1. Resumen Ejecutivo del Trimestre", style_sec_head))
    
    data_resumen = [
        [Paragraph("Indicador / Métrica", style_table_header), Paragraph("Valor Registrado", style_table_header), Paragraph("Estado / Diagnóstico", style_table_header)],
        [Paragraph("<b>Total Planes Pendientes</b>", style_table_cell), Paragraph(f"<b>{total_pendientes}</b>", style_table_cell), Paragraph("Planes de Acción activos en el corte evaluado", style_table_cell)],
        [Paragraph("<b>Riesgo Alto / Medio / Bajo</b>", style_table_cell), Paragraph(f"🔴 {r_alto} | 🟡 {r_medio} | 🟢 {r_bajo}", style_table_cell), Paragraph("Clasificación por severidad del riesgo", style_table_cell)],
        [Paragraph("<b>Porcentaje Vencidos</b>", style_table_cell), Paragraph(f"<b>{pct_venc}%</b> ({vencidos_cnt} planes)", style_table_cell), Paragraph("Mora sobre el total de pendientes del trimestre", style_table_cell)],
        [Paragraph("<b>Top Área Crítica</b>", style_table_cell), Paragraph(f"<b>{top_area_str}</b>", style_table_cell), Paragraph("Dependencia con mayor carga de pendientes", style_table_cell)]
    ]

    t_resumen = Table(data_resumen, colWidths=[160, 140, 240])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0077C8")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
    ]))
    elements.append(t_resumen)
    elements.append(Spacer(1, 10))

    # SECCIÓN 2: TABLA DETALLE ABIERTOS
    elements.append(Paragraph("2. Detalle General de Planes de Acción Abiertos (En Gestión)", style_sec_head))
    df_abiertos = df_q[df_q[col_estado].astype(str).str.contains("Abiert", case=False, na=False)].copy()

    if not df_abiertos.empty:
        data_abiertos = [[
            Paragraph("Código/ID", style_table_header),
            Paragraph("Hallazgo / Situación", style_table_header),
            Paragraph("Área Responsable", style_table_header),
            Paragraph("Riesgo", style_table_header),
            Paragraph("Fecha Límite", style_table_header)
        ]]

        for _, row_a in df_abiertos.iterrows():
            val_id = str(row_a[col_id]).replace(".0", "").strip() if pd.notnull(row_a[col_id]) else "—"
            val_h = Paragraph(str(row_a[col_hallaz])[:130] + "..." if len(str(row_a[col_hallaz])) > 130 else str(row_a[col_hallaz]), style_table_cell) if col_hallaz in row_a else Paragraph("—", style_table_cell)
            val_r = Paragraph(limpiar_nombre_area(str(row_a[col_resp])), style_table_cell) if col_resp in row_a else Paragraph("—", style_table_cell)
            val_rg = str(row_a[col_riesgo]) if col_riesgo and col_riesgo in row_a and pd.notnull(row_a[col_riesgo]) else "—"
            val_f = row_a['Fecha_DT'].strftime('%d/%m/%Y') if pd.notnull(row_a['Fecha_DT']) else "—"

            data_abiertos.append([
                Paragraph(f"<b>{val_id}</b>", style_table_cell),
                val_h,
                val_r,
                Paragraph(val_rg, style_table_cell),
                Paragraph(val_f, style_table_cell)
            ])

        t_abiertos = Table(data_abiertos, colWidths=[55, 215, 150, 60, 60])
        t_abiertos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ]))
        elements.append(t_abiertos)
    else:
        elements.append(Paragraph("<i>No se registran compromisos Abiertos en este trimestre.</i>", style_body))

    elements.append(Spacer(1, 10))

    # SECCIÓN 3: TABLA DETALLE VENCIDOS
    elements.append(Paragraph("3. Detalle de Planes de Acción Vencidos (Fuera de Plazo)", style_sec_head))
    df_vencidos = df_q[df_q[col_estado].astype(str).str.contains("Vencid", case=False, na=False)].copy()

    if not df_vencidos.empty:
        hoy_dt = pd.to_datetime(date.today())
        df_vencidos['Dias_Atraso'] = (hoy_dt - df_vencidos['Fecha_DT']).dt.days
        df_vencidos['Dias_Atraso'] = df_vencidos['Dias_Atraso'].apply(lambda x: x if pd.notnull(x) and x > 0 else 0)

        data_vencidos = [[
            Paragraph("Código/ID", style_table_header),
            Paragraph("Hallazgo / Situación", style_table_header),
            Paragraph("Área Responsable", style_table_header),
            Paragraph("Fecha Límite", style_table_header),
            Paragraph("Días Atraso", style_table_header)
        ]]

        for _, row_v in df_vencidos.iterrows():
            val_id_v = str(row_v[col_id]).replace(".0", "").strip() if pd.notnull(row_v[col_id]) else "—"
            val_h_v = Paragraph(str(row_v[col_hallaz])[:130] + "..." if len(str(row_v[col_hallaz])) > 130 else str(row_v[col_hallaz]), style_table_cell) if col_hallaz in row_v else Paragraph("—", style_table_cell)
            val_r_v = Paragraph(limpiar_nombre_area(str(row_v[col_resp])), style_table_cell) if col_resp in row_v else Paragraph("—", style_table_cell)
            val_f_v = row_v['Fecha_DT'].strftime('%d/%m/%Y') if pd.notnull(row_v['Fecha_DT']) else "—"
            val_da = f"<font color='#FF5252'><b>+{row_v['Dias_Atraso']} días</b></font>"

            data_vencidos.append([
                Paragraph(f"<b>{val_id_v}</b>", style_table_cell),
                val_h_v,
                val_r_v,
                Paragraph(val_f_v, style_table_cell),
                Paragraph(val_da, style_table_cell)
            ])

        t_vencidos = Table(data_vencidos, colWidths=[55, 215, 150, 60, 60])
        t_vencidos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#C0392B")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#FFF5F5")]),
        ]))
        elements.append(t_vencidos)
    else:
        elements.append(Paragraph("<i>🎉 ¡Excelente! No existen planes Vencidos registrados en este trimestre.</i>", style_body))

    doc.build(elements, canvasmaker=CorporateTemplateCanvas)
    return buffer.getvalue()