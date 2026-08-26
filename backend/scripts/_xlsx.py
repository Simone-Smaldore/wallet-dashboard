"""A minimal xlsx reader: an xlsx is a zip of XML, and this is a one-off read.

No openpyxl, no pandas — CLAUDE.md says dependencies get asked about, and this
is a throwaway used to look at three files once.
"""

import re
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

#: Excel counts days from 1899-12-30 (its leap-year bug included).
EPOCH = date(1899, 12, 30)

#: Built-in number formats that mean "this is a date".
DATE_FORMATS = set(range(14, 23)) | {27, 30, 36, 45, 46, 47, 50, 57}


def _text(cell, strings):
    kind = cell.get("t")
    value = cell.find(f"{NS}v")

    if kind == "inlineStr":
        run = cell.find(f"{NS}is")
        return "".join(node.text or "" for node in run.iter(f"{NS}t")) if run is not None else ""
    if value is None or value.text is None:
        return None
    if kind == "s":
        return strings[int(value.text)]
    return value.text


def _column(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index - 1


class Workbook:
    def __init__(self, path):
        self.zip = zipfile.ZipFile(path)

        self.strings = []
        if "xl/sharedStrings.xml" in self.zip.namelist():
            root = ET.fromstring(self.zip.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{NS}si"):
                self.strings.append("".join(node.text or "" for node in item.iter(f"{NS}t")))

        # Which style indexes mean "date".
        self.date_styles = set()
        styles = ET.fromstring(self.zip.read("xl/styles.xml"))
        custom = {
            int(fmt.get("numFmtId")): fmt.get("formatCode")
            for fmt in styles.iter(f"{NS}numFmt")
        }
        cell_xfs = styles.find(f"{NS}cellXfs")
        for index, xf in enumerate(cell_xfs.findall(f"{NS}xf")):
            fmt_id = int(xf.get("numFmtId", 0))
            code = custom.get(fmt_id, "")
            if fmt_id in DATE_FORMATS or (code and re.search(r"[dmy]", code, re.I) and "0.0" not in code):
                self.date_styles.add(index)

        rels = ET.fromstring(self.zip.read("xl/_rels/workbook.xml.rels"))
        targets = {node.get("Id"): node.get("Target") for node in rels}

        book = ET.fromstring(self.zip.read("xl/workbook.xml"))
        self.sheets = {}
        for sheet in book.iter(f"{NS}sheet"):
            target = targets[sheet.get(f"{REL}id")].lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            self.sheets[sheet.get("name")] = target

    def rows(self, name):
        """Every row of a sheet, as a list of values (str, float, date, None)."""
        root = ET.fromstring(self.zip.read(self.sheets[name]))
        out = []
        for row in root.iter(f"{NS}row"):
            cells = {}
            for cell in row.findall(f"{NS}c"):
                raw = _text(cell, self.strings)
                if raw is None:
                    continue
                style = cell.get("s")
                if cell.get("t") is None and style is not None and int(style) in self.date_styles:
                    try:
                        cells[_column(cell.get("r"))] = EPOCH + timedelta(days=float(raw))
                        continue
                    except ValueError:
                        pass
                if cell.get("t") in (None, "n"):
                    try:
                        number = float(raw)
                        cells[_column(cell.get("r"))] = (
                            int(number) if number == int(number) else number
                        )
                        continue
                    except ValueError:
                        pass
                cells[_column(cell.get("r"))] = raw
            width = max(cells) + 1 if cells else 0
            out.append([cells.get(i) for i in range(width)])
        return out
