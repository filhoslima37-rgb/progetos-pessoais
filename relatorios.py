"""Relatorios e exportacoes que reutilizam os servicos com escopo por usuario."""

from collections import defaultdict
from io import BytesIO
import textwrap
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from services import calcular_totais, listar_transacoes


def obter_relatorio(usuario_id, data_inicio=None, data_fim=None, categoria=None, caminho=None):
    """Monta resumo e totais mensais somente com dados do usuario autenticado."""
    transacoes = listar_transacoes(
        usuario_id,
        caminho=caminho,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria,
    )
    resumo = calcular_totais(
        usuario_id,
        data_inicio,
        data_fim,
        caminho=caminho,
        categoria=categoria,
    )

    meses = defaultdict(lambda: {"receitas": 0.0, "despesas": 0.0, "saldo": 0.0})
    for transacao in transacoes:
        mes = transacao["data"][:7]
        chave = "receitas" if transacao["tipo"] == "receita" else "despesas"
        meses[mes][chave] += transacao["valor"]
        meses[mes]["saldo"] = meses[mes]["receitas"] - meses[mes]["despesas"]

    mensal = [
        {"mes": mes, **meses[mes]}
        for mes in sorted(meses)
    ]
    return {"resumo": resumo, "mensal": mensal, "transacoes": transacoes}


def _celula_xml(valor, referencia):
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        conteudo = f'<c r="{referencia}"><v>{valor}</v></c>'
    else:
        texto = "".join(
            caractere
            for caractere in str(valor)
            if caractere in "\t\n\r"
            or 0x20 <= ord(caractere) <= 0xD7FF
            or 0xE000 <= ord(caractere) <= 0xFFFD
            or 0x10000 <= ord(caractere) <= 0x10FFFF
        )
        texto = (
            texto.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
        conteudo = (
            f'<c r="{referencia}" t="inlineStr"><is><t xml:space="preserve">'
            f"{texto}</t></is></c>"
        )
    return conteudo


def _coluna_excel(indice):
    letras = ""
    while indice:
        indice, resto = divmod(indice - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _planilha_xml(linhas):
    rows = []
    for numero_linha, valores in enumerate(linhas, start=1):
        celulas = "".join(
            _celula_xml(valor, f"{_coluna_excel(indice)}{numero_linha}")
            for indice, valor in enumerate(valores, start=1)
        )
        rows.append(f'<row r="{numero_linha}">{celulas}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(rows)}</sheetData></worksheet>"
    )


def gerar_excel(usuario_id, data_inicio=None, data_fim=None, categoria=None, caminho=None):
    """Gera um arquivo XLSX em memoria com transacoes e resumos do usuario."""
    relatorio = obter_relatorio(usuario_id, data_inicio, data_fim, categoria, caminho)
    linhas_transacoes = [["ID", "Data", "Descricao", "Tipo", "Categoria", "Valor"]]
    linhas_transacoes.extend(
        [
            item["id"], item["data"], item["descricao"], item["tipo"],
            item["categoria"], item["valor"],
        ]
        for item in relatorio["transacoes"]
    )
    linhas_resumo = [
        ["Indicador", "Valor"],
        ["Receitas", relatorio["resumo"]["receitas"]],
        ["Despesas", relatorio["resumo"]["despesas"]],
        ["Saldo", relatorio["resumo"]["saldo"]],
    ]
    linhas_mensais = [["Mes", "Receitas", "Despesas", "Saldo"]]
    linhas_mensais.extend(
        [item["mes"], item["receitas"], item["despesas"], item["saldo"]]
        for item in relatorio["mensal"]
    )

    nomes = ["Transacoes", "Resumo", "Mensal"]
    planilhas = [linhas_transacoes, linhas_resumo, linhas_mensais]
    ET.register_namespace("", "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
    workbook = ET.Element(
        "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}workbook"
    )
    folhas = ET.SubElement(
        workbook, "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets"
    )
    for indice, nome in enumerate(nomes, start=1):
        ET.SubElement(
            folhas,
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet",
            {"name": nome, "sheetId": str(indice),
             "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id": f"rId{indice}"},
        )

    rels_root = ET.Element(
        "{http://schemas.openxmlformats.org/package/2006/relationships}Relationships"
    )
    for indice in range(1, len(nomes) + 1):
        ET.SubElement(
            rels_root,
            "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
            {"Id": f"rId{indice}",
             "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
             "Target": f"worksheets/sheet{indice}.xml"},
        )

    content_types = ET.Element(
        "{http://schemas.openxmlformats.org/package/2006/content-types}Types"
    )
    ET.SubElement(content_types, "{http://schemas.openxmlformats.org/package/2006/content-types}Default",
                  {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(content_types, "{http://schemas.openxmlformats.org/package/2006/content-types}Default",
                  {"Extension": "xml", "ContentType": "application/xml"})
    ET.SubElement(content_types, "{http://schemas.openxmlformats.org/package/2006/content-types}Override",
                  {"PartName": "/xl/workbook.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"})
    for indice in range(1, len(nomes) + 1):
        ET.SubElement(content_types, "{http://schemas.openxmlformats.org/package/2006/content-types}Override",
                      {"PartName": f"/xl/worksheets/sheet{indice}.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"})

    package_rels = ET.Element(
        "{http://schemas.openxmlformats.org/package/2006/relationships}Relationships"
    )
    ET.SubElement(
        package_rels,
        "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
        {"Id": "rId1",
         "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
         "Target": "xl/workbook.xml"},
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as arquivo:
        arquivo.writestr("[Content_Types].xml", ET.tostring(content_types, encoding="utf-8", xml_declaration=True))
        arquivo.writestr("_rels/.rels", ET.tostring(package_rels, encoding="utf-8", xml_declaration=True))
        arquivo.writestr("xl/workbook.xml", ET.tostring(workbook, encoding="utf-8", xml_declaration=True))
        arquivo.writestr("xl/_rels/workbook.xml.rels", ET.tostring(rels_root, encoding="utf-8", xml_declaration=True))
        for indice, linhas in enumerate(planilhas, start=1):
            arquivo.writestr(f"xl/worksheets/sheet{indice}.xml", _planilha_xml(linhas))
    return buffer.getvalue()


def _texto_pdf(valor):
    texto = str(valor).encode("cp1252", errors="replace").decode("cp1252")
    return texto.replace("\r", " ").replace("\n", " ")


def _literal_pdf(texto):
    conteudo = _texto_pdf(texto).encode("cp1252", errors="replace")
    conteudo = conteudo.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return b"(" + conteudo + b")"


def gerar_pdf(usuario_id, data_inicio=None, data_fim=None, categoria=None, caminho=None):
    """Gera relatorio PDF paginado com totais e transacoes do usuario."""
    relatorio = obter_relatorio(usuario_id, data_inicio, data_fim, categoria, caminho)
    resumo = relatorio["resumo"]
    linhas = [
        "Relatorio financeiro",
        f"Periodo: {data_inicio or 'inicio'} a {data_fim or 'hoje'}",
        f"Categoria: {categoria or 'Todas'}",
        f"Receitas: R$ {resumo['receitas']:.2f}",
        f"Despesas: R$ {resumo['despesas']:.2f}",
        f"Saldo: R$ {resumo['saldo']:.2f}",
        "",
        "Resumo mensal:",
        "Mes | Receitas | Despesas | Saldo",
    ]
    for item in relatorio["mensal"]:
        linhas.append(
            f"{item['mes']} | {item['receitas']:.2f} | "
            f"{item['despesas']:.2f} | {item['saldo']:.2f}"
        )
    linhas.extend(["", "Transacoes:", "Data | Tipo | Categoria | Descricao | Valor"])
    for item in relatorio["transacoes"]:
        linhas.append(
            f"{item['data']} | {item['tipo']} | {item['categoria']} | "
            f"{item['descricao']} | R$ {item['valor']:.2f}"
        )

    linhas_pagina = []
    for linha in linhas:
        linhas_pagina.extend(textwrap.wrap(_texto_pdf(linha), width=95) or [""])
    paginas = [linhas_pagina[indice:indice + 48] for indice in range(0, len(linhas_pagina), 48)] or [[]]

    objetos = [None, None]
    referencias_paginas = []
    fonte_id = 3 + 2 * len(paginas)
    for linhas_atuais in paginas:
        pagina_id = len(objetos) + 1
        conteudo_id = pagina_id + 1
        referencias_paginas.append(pagina_id)
        stream = bytearray(b"BT /F1 10 Tf 42 756 Td 14 TL\n")
        for linha in linhas_atuais:
            stream.extend(_literal_pdf(linha) + b" Tj T*\n")
        stream.extend(b"ET")
        objetos.append(None)
        objetos.append(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
            + bytes(stream) + b"\nendstream"
        )
        objetos[pagina_id - 1] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {fonte_id} 0 R >> >> "
            f"/Contents {conteudo_id} 0 R >>"
        ).encode("ascii")

    assert fonte_id == len(objetos) + 1
    objetos[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objetos[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{ref} 0 R' for ref in referencias_paginas)}] "
        f"/Count {len(referencias_paginas)} >>"
    ).encode("ascii")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for indice, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{indice} 0 obj\n".encode("ascii") + objeto + b"\nendobj\n")
    inicio_xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objetos) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for deslocamento in offsets[1:]:
        pdf.extend(f"{deslocamento:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{inicio_xref}\n%%EOF".encode("ascii")
    )
    return bytes(pdf)
