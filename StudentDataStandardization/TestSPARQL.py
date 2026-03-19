
import argparse
import os
import sys
import unicodedata
from rdflib import Graph
from typing import Dict, List, Optional, Tuple

# Fix UTF-8 output tren Windows terminal
import io

def _ensure_utf8_text_stream(stream):
    if getattr(stream, "encoding", None) != "utf-8":
        try:
            return io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        except Exception:
            pass
    return stream

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
else:
    sys.stdout = _ensure_utf8_text_stream(sys.stdout)

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
else:
    sys.stderr = _ensure_utf8_text_stream(sys.stderr)


# -----------------------------------------------------------------------
# Namespace ontology
# -----------------------------------------------------------------------
NS = "http://www.semanticweb.org/henrydao/ontologies/2025/7/TrainingProgramOntology#"

PREFIX = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX :     <{NS}>
""".replace("{NS}", NS)


# -----------------------------------------------------------------------
# Duong dan ontology (thu tu uu tien: tham so > bien moi truong > mac dinh)
# -----------------------------------------------------------------------
def resolve_path(path: Optional[str] = None) -> str:
    if path:
        return path
    env = os.environ.get("ONTOLOGY_PATH", "")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "owl", "ontology_v18.rdf")


def load_graph(path: Optional[str] = None) -> Tuple[Graph, str]:
    owl_path = resolve_path(path)
    if not os.path.isfile(owl_path):
        raise FileNotFoundError(
            f"Khong tim thay file ontology: {owl_path}\n"
            "Truyen duong dan qua --ontology hoac bien moi truong ONTOLOGY_PATH."
        )
    g = Graph()
    g.parse(owl_path, format="xml")
    return g, owl_path


# -----------------------------------------------------------------------
# Cac cau truy van SPARQL
# -----------------------------------------------------------------------

Q1_MON_THEO_HOC_KY = PREFIX + """
SELECT ?soHocKy ?maMon ?tenMon ?soTinChi ?loaiMoHocKy
WHERE {
    ?course a :Course ;
            :courseCode            ?maMon ;
            :courseName            ?tenMon ;
            :credit                ?soTinChi ;
            :openSemesterType      ?loaiMoHocKy ;
            :recommendedInSemester ?sem .
    ?sem :semesterNumber ?soHocKy .
}
ORDER BY ?soHocKy ?maMon
"""

Q2_TIEN_QUYET = PREFIX + """
SELECT ?maMon ?tenMon ?maTienQuyet ?tenTienQuyet
WHERE {
    ?course a :Course ;
            :courseCode            ?maMon ;
            :courseName            ?tenMon ;
            :hasPrerequisiteCourse ?pre .
    ?pre :courseCode ?maTienQuyet ;
         :courseName ?tenTienQuyet .
}
ORDER BY ?maMon ?maTienQuyet
"""

Q3_SONG_HANH = PREFIX + """
SELECT ?maMon ?tenMon ?maSongHanh ?tenSongHanh
WHERE {
    ?course a :Course ;
            :courseCode      ?maMon ;
            :courseName      ?tenMon ;
            :corequisiteWith ?co .
    ?co :courseCode ?maSongHanh ;
        :courseName ?tenSongHanh .
}
ORDER BY ?maMon
"""

Q4_TIN_CHI_HOC_KY = PREFIX + """
SELECT ?maMon ?tenMon ?soTinChi ?soHocKy ?loaiMoHocKy
WHERE {
    ?course a :Course ;
            :courseCode            ?maMon ;
            :courseName            ?tenMon ;
            :credit                ?soTinChi ;
            :openSemesterType      ?loaiMoHocKy ;
            :recommendedInSemester ?sem .
    ?sem :semesterNumber ?soHocKy .
}
ORDER BY ?soHocKy ?maMon
"""

Q5_THEO_CHUYEN_NGANH = PREFIX + """
SELECT ?tenNhom ?loaiMon ?maMon ?tenMon ?soTinChi
WHERE {
    {
        ?course a :Course ;
                :isRequiredForMajor ?nhom ;
                :courseCode ?maMon ; :courseName ?tenMon ; :credit ?soTinChi .
        ?nhom :majorName ?tenNhom .
        BIND("Bắt buộc ngành" AS ?loaiMon)
    } UNION {
        ?course a :Course ;
                :isElectiveForMajor ?nhom ;
                :courseCode ?maMon ; :courseName ?tenMon ; :credit ?soTinChi .
        ?nhom :majorName ?tenNhom .
        BIND("Tự chọn ngành" AS ?loaiMon)
    } UNION {
        ?course a :Course ;
                :isRequiredForSpecialization ?nhom ;
                :courseCode ?maMon ; :courseName ?tenMon ; :credit ?soTinChi .
        ?nhom :specializationName ?tenNhom .
        BIND("Bắt buộc chuyên ngành" AS ?loaiMon)
    } UNION {
        ?course a :Course ;
                :isElectiveForSpecialization ?nhom ;
                :courseCode ?maMon ; :courseName ?tenMon ; :credit ?soTinChi .
        ?nhom :specializationName ?tenNhom .
        BIND("Tự chọn chuyên ngành" AS ?loaiMon)
    }
}
ORDER BY ?tenNhom ?loaiMon ?maMon
"""


# -----------------------------------------------------------------------
# Ham chay truy van
# -----------------------------------------------------------------------

def query1_mon_theo_hoc_ky(g: Graph, hoc_ky: Optional[int] = None) -> List[Dict]:
    rows = []
    _map: Dict[str, str] = {"1": "HK1", "2": "HK2", "12": "HK1&HK2"}
    for row in g.query(Q1_MON_THEO_HOC_KY):
        so_hk = int(str(row.soHocKy))
        if hoc_ky is not None and so_hk != hoc_ky:
            continue
        rows.append({
            "soHocKy"  : so_hk,
            "maMon"    : str(row.maMon),
            "tenMon"   : str(row.tenMon),
            "soTinChi" : int(str(row.soTinChi)),
            "moTrongHK": _map.get(str(row.loaiMoHocKy), str(row.loaiMoHocKy)),
        })
    return rows


def query2_tien_quyet(g: Graph, ma_mon: Optional[str] = None) -> List[Dict]:
    rows = []
    for row in g.query(Q2_TIEN_QUYET):
        if ma_mon and str(row.maMon) != ma_mon:
            continue
        rows.append({
            "maMon"       : str(row.maMon),
            "tenMon"      : str(row.tenMon),
            "maTienQuyet" : str(row.maTienQuyet),
            "tenTienQuyet": str(row.tenTienQuyet),
        })
    return rows


def query3_song_hanh(g: Graph, ma_mon: Optional[str] = None) -> List[Dict]:
    rows = []
    for row in g.query(Q3_SONG_HANH):
        if ma_mon and str(row.maMon) != ma_mon:
            continue
        rows.append({
            "maMon"      : str(row.maMon),
            "tenMon"     : str(row.tenMon),
            "maSongHanh" : str(row.maSongHanh),
            "tenSongHanh": str(row.tenSongHanh),
        })
    return rows


def query4_tin_chi_hoc_ky(g: Graph) -> List[Dict]:
    rows = []
    _map: Dict[str, str] = {"1": "HK1", "2": "HK2", "3": "HK1&HK2", "12": "HK1&HK2"}
    for row in g.query(Q4_TIN_CHI_HOC_KY):
        rows.append({
            "maMon"    : str(row.maMon),
            "tenMon"   : str(row.tenMon),
            "soTinChi" : int(str(row.soTinChi)),
            "soHocKy"  : int(str(row.soHocKy)),
            "moTrongHK": _map.get(str(row.loaiMoHocKy), str(row.loaiMoHocKy)),
        })
    return rows


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', text.strip().lower())
    return ''.join(ch for ch in normalized if not unicodedata.combining(ch))


def query5_theo_chuyen_nganh(
    g: Graph,
    ten_nhom: Optional[str] = None,
    loai_mon: Optional[str] = None,
) -> List[Dict]:
    seen = set()
    rows = []
    for row in g.query(Q5_THEO_CHUYEN_NGANH):
        key = (str(row.tenNhom), str(row.maMon), str(row.loaiMon))
        if key in seen:
            continue
        seen.add(key)

        if ten_nhom:
            if _normalize_text(str(ten_nhom)) not in _normalize_text(str(row.tenNhom)):
                continue

        if loai_mon:
            if _normalize_text(str(loai_mon)) not in _normalize_text(str(row.loaiMon)):
                continue

        rows.append({
            "tenNhom" : str(row.tenNhom),
            "loaiMon" : str(row.loaiMon),
            "maMon"   : str(row.maMon),
            "tenMon"  : str(row.tenMon),
            "soTinChi": int(str(row.soTinChi)),
        })
    return rows


def _query_course_group(
    g: Graph,
    course_class: str,
    relation: str,
    relation_label: str,
) -> List[Dict]:
    from rdflib import RDF, URIRef, Namespace

    NS = "http://www.semanticweb.org/henrydao/ontologies/2025/7/TrainingProgramOntology#"
    TP = Namespace(NS)

    rows = []
    seen = set()

    class_uri = URIRef(NS + course_class)
    rel_uri = getattr(TP, relation)
    name_prop = TP.majorName if relation in ("isRequiredForMajor", "isElectiveForMajor") else TP.specializationName

    for course in g.subjects(RDF.type, class_uri):
        for group in g.objects(course, rel_uri):
            group_name = next(g.objects(group, name_prop), None)
            if group_name is None:
                continue

            key = (str(group_name), str(course), relation_label)
            if key in seen:
                continue
            seen.add(key)

            ma_mon = next(g.objects(course, TP.courseCode), None)
            ten_mon = next(g.objects(course, TP.courseName), None)
            so_tin_chi = next(g.objects(course, TP.credit), None)

            if not (ma_mon and ten_mon and so_tin_chi):
                continue

            rows.append({
                "tenNhom" : str(group_name),
                "loaiMon" : str(relation_label),
                "maMon"   : str(ma_mon),
                "tenMon"  : str(ten_mon),
                "soTinChi": int(str(so_tin_chi)),
            })

    return sorted(rows, key=lambda r: (r["tenNhom"], r["loaiMon"], r["maMon"]))


def query_dai_cuong_bat_buoc(g: Graph) -> List[Dict]:
    return _query_course_group(g, "GeneralEducationCourse", "isRequiredForMajor", "Bắt buộc đại cương")


def query_dai_cuong_tu_chon(g: Graph) -> List[Dict]:
    return _query_course_group(g, "GeneralEducationCourse", "isElectiveForMajor", "Tự chọn đại cương")


def query_co_so_nganh_bat_buoc(g: Graph) -> List[Dict]:
    return _query_course_group(g, "FoundationCourse", "isRequiredForMajor", "Bắt buộc cơ sở ngành")


def query_co_so_nganh_tu_chon(g: Graph) -> List[Dict]:
    return _query_course_group(g, "FoundationCourse", "isElectiveForMajor", "Tự chọn cơ sở ngành")


def query_chuyen_nganh_bat_buoc(g: Graph) -> List[Dict]:
    return _query_course_group(g, "CoreCourse", "isRequiredForSpecialization", "Bắt buộc chuyên ngành")


def query_the_chat_bat_buoc(g: Graph) -> List[Dict]:
    return _query_course_group(g, "PhysicalEducationCourse", "isRequiredForMajor", "Bắt buộc thể chất")


def query_the_chat_tu_chon(g: Graph) -> List[Dict]:
    return _query_course_group(g, "PhysicalEducationCourse", "isElectiveForMajor", "Tự chọn thể chất")


# -----------------------------------------------------------------------
# In ket qua dang bang
# -----------------------------------------------------------------------

def _print_section(title: str, output_lines: Optional[List[str]] = None) -> None:
    line1 = "\n" + "=" * 65
    line2 = "  " + title
    line3 = "=" * 65
    print(line1); print(line2); print(line3)
    if output_lines is not None:
        output_lines.extend([line1, line2, line3])


def _print_table(rows: List[Dict], output_lines: Optional[List[str]] = None) -> None:
    if not rows:
        line = "  (Không có kết quả)"
        print(line)
        if output_lines is not None:
            output_lines.append(line)
        return
    headers: List[str] = list(rows[0].keys())
    widths: Dict[str, int] = {
        h: int(max(len(h), max(len(str(r[h])) for r in rows)))
        for h in headers
    }
    header_line = "  " + "  ".join(h.ljust(widths[h]) for h in headers)
    sep_line = "  " + "  ".join("-" * widths[h] for h in headers)
    print(header_line)
    print(sep_line)
    if output_lines is not None:
        output_lines.append(header_line)
        output_lines.append(sep_line)
    for r in rows:
        row_line = "  " + "  ".join(str(r[h]).ljust(widths[h]) for h in headers)
        print(row_line)
        if output_lines is not None:
            output_lines.append(row_line)
    tail_line = f"\n  Tổng: {len(rows)} bản ghi"
    print(tail_line)
    if output_lines is not None:
        output_lines.append(tail_line)


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SPARQL queries on Training Program Ontology")
    p.add_argument(
        "--ontology", "-o", metavar="FILE", default=None,
        help="Duong dan file ontology RDF/XML. Mac dinh lay tu bien moi truong ONTOLOGY_PATH."
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    g, owl_path = load_graph(args.ontology)
    print(f"Ontology: {owl_path} ({len(g)} triples)")

    _print_section("QUERY 1 - Mon hoc mo theo hoc ky (tat ca)")
    _print_table(query1_mon_theo_hoc_ky(g))

    _print_section("QUERY 1b - Mon hoc ky 3")
    _print_table(query1_mon_theo_hoc_ky(g, hoc_ky=3))

    _print_section("QUERY 2 - Mon tien quyet (tat ca)")
    _print_table(query2_tien_quyet(g))

    _print_section("QUERY 2b - Tien quyet cua INS330")
    _print_table(query2_tien_quyet(g, ma_mon="INS330"))

    _print_section("QUERY 3 - Mon song hanh")
    _print_table(query3_song_hanh(g))

    _print_section("QUERY 4 - Tin chi va hoc ky khuyen nghi")
    _print_table(query4_tin_chi_hoc_ky(g))

    _print_section("QUERY 5 - Mon theo nganh/chuyen nganh va nhom")
    _print_table(query5_theo_chuyen_nganh(g))

    _print_section("QUERY 5b - Mon bat buoc nganh CNTT")
    _print_table(query5_theo_chuyen_nganh(g, ten_nhom="Cong Nghe Thong Tin", loai_mon="Bắt buộc ngành"))

    _print_section("QUERY 5c - Mon tu chon chuyen nganh CNPM")
    _print_table(query5_theo_chuyen_nganh(g, ten_nhom="Cong nghe phan mem", loai_mon="Tự chọn chuyên ngành"))

    _print_section("QUERY 6 - Mon bat buoc dai cuong")
    _print_table(query_dai_cuong_bat_buoc(g))

    _print_section("QUERY 7 - Mon tu chon dai cuong")
    _print_table(query_dai_cuong_tu_chon(g))

    _print_section("QUERY 8 - Mon bat buoc co so nganh")
    _print_table(query_co_so_nganh_bat_buoc(g))

    _print_section("QUERY 9 - Mon tu chon co so nganh")
    _print_table(query_co_so_nganh_tu_chon(g))

    output_lines: List[str] = []

    _print_section("QUERY 10 - Môn bắt buộc chuyên ngành", output_lines)
    _print_table(query_chuyen_nganh_bat_buoc(g), output_lines)

    _print_section("QUERY 11 - Môn bắt buộc thể chất", output_lines)
    _print_table(query_the_chat_bat_buoc(g), output_lines)

    _print_section("QUERY 12 - Môn tự chọn thể chất", output_lines)
    _print_table(query_the_chat_tu_chon(g), output_lines)

    output_file = os.path.join(os.path.dirname(__file__), "Output_TestSPARQL.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"\nĐã lưu kết quả ra file: {output_file}")


if __name__ == "__main__":
    main()
