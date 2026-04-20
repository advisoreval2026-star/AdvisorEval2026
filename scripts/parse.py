#!/usr/bin/env python3
"""Parse raw.txt (Google Doc export) into advisors.json."""
import json
import re
from pathlib import Path
from collections import Counter

RAW = Path(__file__).parent / "raw.txt"
OUT = Path(__file__).parent / "advisors.json"

# Institution -> (display_name, region, lat, lon)
# Region codes: US, CA, HK, CN, EU, SG, ME, AU, Other
INSTITUTIONS = {
    # US
    "CMU": ("Carnegie Mellon University", "US", 40.4433, -79.9436),
    "Carnegie Mellon": ("Carnegie Mellon University", "US", 40.4433, -79.9436),
    "MIT": ("MIT", "US", 42.3601, -71.0942),
    "Stanford": ("Stanford University", "US", 37.4275, -122.1697),
    "UCB": ("UC Berkeley", "US", 37.8719, -122.2585),
    "UC Berkeley": ("UC Berkeley", "US", 37.8719, -122.2585),
    "Berkeley": ("UC Berkeley", "US", 37.8719, -122.2585),
    "BAIR": ("UC Berkeley (BAIR)", "US", 37.8719, -122.2585),
    "Princeton": ("Princeton University", "US", 40.3430, -74.6551),
    "Pton": ("Princeton University", "US", 40.3430, -74.6551),
    "Harvard": ("Harvard University", "US", 42.3770, -71.1167),
    "Yale": ("Yale University", "US", 41.3163, -72.9223),
    "Columbia": ("Columbia University", "US", 40.8075, -73.9626),
    "Cornell": ("Cornell University", "US", 42.4534, -76.4735),
    "UPenn": ("University of Pennsylvania", "US", 39.9522, -75.1932),
    "Upenn": ("University of Pennsylvania", "US", 39.9522, -75.1932),
    "Penn": ("University of Pennsylvania", "US", 39.9522, -75.1932),
    "JHU": ("Johns Hopkins", "US", 39.3299, -76.6205),
    "Duke": ("Duke University", "US", 36.0014, -78.9382),
    "UNC": ("UNC Chapel Hill", "US", 35.9049, -79.0469),
    "UVA": ("University of Virginia", "US", 38.0336, -78.5080),
    "UMD": ("University of Maryland", "US", 38.9869, -76.9426),
    "Rutgers": ("Rutgers University", "US", 40.5008, -74.4474),
    "NYU": ("NYU", "US", 40.7295, -73.9965),
    "NEU": ("Northeastern University", "US", 42.3398, -71.0892),
    "BU": ("Boston University", "US", 42.3505, -71.1054),
    "Northwestern": ("Northwestern University", "US", 42.0565, -87.6753),
    "NWU": ("Northwestern University", "US", 42.0565, -87.6753),
    "NU": ("Northwestern University", "US", 42.0565, -87.6753),
    "UChicago": ("University of Chicago", "US", 41.7886, -87.5987),
    "U-Chicago": ("University of Chicago", "US", 41.7886, -87.5987),
    "UIUC": ("UIUC", "US", 40.1020, -88.2272),
    "Illinois": ("UIUC", "US", 40.1020, -88.2272),
    "UW-Madison": ("UW-Madison", "US", 43.0766, -89.4125),
    "UW Madison": ("UW-Madison", "US", 43.0766, -89.4125),
    "Wisc": ("UW-Madison", "US", 43.0766, -89.4125),
    "UMich": ("University of Michigan", "US", 42.2780, -83.7382),
    "OSU": ("Ohio State University", "US", 40.0061, -83.0283),
    "GMU": ("George Mason University", "US", 38.8315, -77.3080),
    "Gatech": ("Georgia Tech", "US", 33.7756, -84.3963),
    "GT": ("Georgia Tech", "US", 33.7756, -84.3963),
    "MSU": ("Michigan State University", "US", 42.7018, -84.4822),
    "Rice University": ("Rice University", "US", 29.7174, -95.4018),
    "Rice": ("Rice University", "US", 29.7174, -95.4018),
    "UT Austin": ("UT Austin", "US", 30.2850, -97.7335),
    "UTD": ("UT Dallas", "US", 32.9857, -96.7501),
    "UH": ("University of Houston", "US", 29.7199, -95.3422),
    "TAMU": ("Texas A&M", "US", 30.6147, -96.3399),
    "Caltech": ("Caltech", "US", 34.1377, -118.1253),
    "USC": ("USC", "US", 34.0224, -118.2851),
    "UCLA": ("UCLA", "US", 34.0689, -118.4452),
    "UCSD": ("UCSD", "US", 32.8801, -117.2340),
    "UCSB": ("UCSB", "US", 34.4140, -119.8489),
    "UCSC": ("UCSC", "US", 36.9914, -122.0609),
    "UCR": ("UC Riverside", "US", 33.9737, -117.3281),
    "UCD": ("UC Davis", "US", 38.5382, -121.7617),
    "UC Davis": ("UC Davis", "US", 38.5382, -121.7617),
    "UCI": ("UC Irvine", "US", 33.6405, -117.8443),
    "UC Merced": ("UC Merced", "US", 37.3667, -120.4241),
    "UMerced": ("UC Merced", "US", 37.3667, -120.4241),
    "UMN": ("University of Minnesota", "US", 44.9740, -93.2277),
    "UMinn": ("University of Minnesota", "US", 44.9740, -93.2277),
    "IUB": ("Indiana University Bloomington", "US", 39.1682, -86.5230),
    "IU": ("Indiana University", "US", 39.1682, -86.5230),
    "Lehigh": ("Lehigh University", "US", 40.6069, -75.3775),
    "Upitt": ("University of Pittsburgh", "US", 40.4444, -79.9608),
    "UPitt": ("University of Pittsburgh", "US", 40.4444, -79.9608),
    "Pitt": ("University of Pittsburgh", "US", 40.4444, -79.9608),
    "UW": ("University of Washington", "US", 47.6553, -122.3035),
    "NJIT": ("NJIT", "US", 40.7421, -74.1787),
    "UF": ("University of Florida", "US", 29.6436, -82.3549),
    "Emory": ("Emory University", "US", 33.7925, -84.3243),
    "Dartmouth": ("Dartmouth College", "US", 43.7044, -72.2887),
    "UA": ("University of Arizona", "US", 32.2319, -110.9501),
    "UMass Amherst": ("UMass Amherst", "US", 42.3907, -72.5283),
    "UMass": ("UMass Amherst", "US", 42.3907, -72.5283),
    "Umass": ("UMass Amherst", "US", 42.3907, -72.5283),
    "Purdue": ("Purdue University", "US", 40.4237, -86.9212),
    "Stony Brook": ("Stony Brook University", "US", 40.9145, -73.1232),
    "WUSTL": ("Washington University St. Louis", "US", 38.6488, -90.3108),
    "Vandy": ("Vanderbilt University", "US", 36.1447, -86.8027),
    "Vanderbilt": ("Vanderbilt University", "US", 36.1447, -86.8027),
    "Brown": ("Brown University", "US", 41.8268, -71.4025),
    # CA (Canada)
    "Mila/UdeM": ("Mila / UdeM", "CA", 45.5180, -73.6149),
    "Mila/Mcgill": ("Mila / McGill", "CA", 45.5050, -73.5772),
    "Mila/McGill": ("Mila / McGill", "CA", 45.5050, -73.5772),
    "Mila": ("Mila (Montreal)", "CA", 45.5180, -73.6149),
    "UdeM": ("Université de Montréal", "CA", 45.5180, -73.6149),
    "McGill": ("McGill University", "CA", 45.5048, -73.5772),
    "Mcgill": ("McGill University", "CA", 45.5048, -73.5772),
    "Waterloo": ("University of Waterloo", "CA", 43.4723, -80.5449),
    "Uwaterloo": ("University of Waterloo", "CA", 43.4723, -80.5449),
    "UofT": ("University of Toronto", "CA", 43.6629, -79.3957),
    "UBC": ("UBC", "CA", 49.2606, -123.2460),
    # HK
    "HKUST(GZ)": ("HKUST (Guangzhou)", "HK", 22.9612, 113.5420),
    "HKUSTGZ": ("HKUST (Guangzhou)", "HK", 22.9612, 113.5420),
    "HKUST": ("HKUST", "HK", 22.3364, 114.2654),
    "HKU": ("University of Hong Kong", "HK", 22.2830, 114.1371),
    "CUHK(Shenzhen)": ("CUHK (Shenzhen)", "HK", 22.6875, 114.2023),
    "CUHK": ("CUHK", "HK", 22.4193, 114.2069),
    "CityU": ("City University of Hong Kong", "HK", 22.3371, 114.1719),
    "PolyU": ("Hong Kong PolyU", "HK", 22.3034, 114.1796),
    # CN
    "THU": ("Tsinghua University", "CN", 40.0084, 116.3225),
    "Tsinghua": ("Tsinghua University", "CN", 40.0084, 116.3225),
    "PKU": ("Peking University", "CN", 39.9925, 116.3055),
    "Peking": ("Peking University", "CN", 39.9925, 116.3055),
    "ZJU": ("Zhejiang University", "CN", 30.2635, 120.1216),
    "HUST": ("Huazhong Univ. of Science & Technology", "CN", 30.5125, 114.4147),
    "FDU": ("Fudan University", "CN", 31.2976, 121.5020),
    "Fudan": ("Fudan University", "CN", 31.2976, 121.5020),
    "USTC": ("USTC", "CN", 31.8391, 117.2602),
    "NJU": ("Nanjing University", "CN", 32.0535, 118.7779),
    "SJTU": ("Shanghai Jiao Tong University", "CN", 31.0252, 121.4350),
    "NKU": ("Nankai University", "CN", 39.1023, 117.1637),
    "BUAA": ("Beihang University", "CN", 39.9817, 116.3440),
    "HIT": ("Harbin Institute of Technology", "CN", 45.7470, 126.6839),
    "SCUT": ("South China Univ. of Tech.", "CN", 23.1501, 113.3434),
    "SUSTech": ("SUSTech", "CN", 22.5985, 113.9989),
    "Shanghai AI Lab": ("Shanghai AI Lab", "CN", 31.2300, 121.4737),
    "MSRA": ("Microsoft Research Asia", "CN", 39.9830, 116.3089),
    "CAS": ("Chinese Academy of Sciences", "CN", 39.9833, 116.4000),
    # EU
    "CAM": ("University of Cambridge", "EU", 52.2053, 0.1218),
    "Cambridge": ("University of Cambridge", "EU", 52.2053, 0.1218),
    "LMU": ("LMU Munich", "EU", 48.1508, 11.5803),
    "EPFL": ("EPFL", "EU", 46.5191, 6.5668),
    "ICL": ("Imperial College London", "EU", 51.4988, -0.1749),
    "Imperial College": ("Imperial College London", "EU", 51.4988, -0.1749),
    "Oxford": ("University of Oxford", "EU", 51.7548, -1.2544),
    "ETH": ("ETH Zürich", "EU", 47.3763, 8.5482),
    "TUM": ("TU Munich", "EU", 48.1497, 11.5681),
    "TU Munich": ("TU Munich", "EU", 48.1497, 11.5681),
    "MPI": ("Max Planck Institute", "EU", 48.1147, 11.4692),
    "IST Austria": ("IST Austria", "EU", 48.2030, 16.3462),
    "KTH": ("KTH Royal Institute", "EU", 59.3498, 18.0724),
    # ME
    "MBZUAI": ("MBZUAI", "ME", 24.4419, 54.6153),
    "Mbzuai": ("MBZUAI", "ME", 24.4419, 54.6153),
    # SG
    "NUS": ("National University of Singapore", "SG", 1.2966, 103.7764),
    "NUs": ("National University of Singapore", "SG", 1.2966, 103.7764),
    "NTU": ("Nanyang Technological University", "SG", 1.3483, 103.6831),
    "ＮＴＵ": ("Nanyang Technological University", "SG", 1.3483, 103.6831),
    "SMU": ("Singapore Management University", "SG", 1.2971, 103.8499),
    "SUTD": ("SUTD", "SG", 1.3417, 103.9631),
    # AU
    "UQ": ("University of Queensland", "AU", -27.4975, 153.0137),
    # Industry / misc (show in "Other")
    "Google": ("Google", "Other", 37.4220, -122.0841),
    "DeepMind": ("DeepMind", "Other", 51.5335, -0.1262),
    "GDM": ("Google DeepMind", "Other", 51.5335, -0.1262),
    "Meta": ("Meta", "Other", 37.4846, -122.1484),
    "OpenAI": ("OpenAI", "Other", 37.7617, -122.4015),
    "xAI": ("xAI", "Other", 37.7617, -122.4015),
    "NVIDIA": ("NVIDIA", "Other", 37.3710, -121.9544),
    "Microsoft": ("Microsoft", "Other", 47.6396, -122.1283),
    "Apple": ("Apple", "Other", 37.3349, -122.0090),
    "Anthropic": ("Anthropic", "Other", 37.7897, -122.3942),
}

# Sort keys by length descending so longer keys match first
INST_KEYS = sorted(INSTITUTIONS.keys(), key=lambda s: (-len(s), s))


# ---- Heading detection ----
# We look for: optional leading prefix (e.g. "MSU -> UNC Xiaoming Liu"),
# then an institution keyword, then the advisor name.
def find_institution_in_line(line):
    """Return (inst_key, start, end) of the first institution keyword in line, or None."""
    for k in INST_KEYS:
        # word boundary for alphanumeric institution codes; Chinese uses no boundary
        pat = re.compile(r'(?<![A-Za-z0-9])' + re.escape(k) + r'(?![A-Za-z0-9])')
        m = pat.search(line)
        if m:
            return k, m.start(), m.end()
    return None


def parse_heading(line):
    """Try to parse as advisor heading. Return dict or None."""
    stripped = line.strip().lstrip("*-•·").strip()
    if not stripped or len(stripped) > 200:
        return None
    # Exclude known prose markers and section headers
    if stripped in {"US", "CA", "HK", "CN", "EU", "SG", "Middle East", "ME", "AU"}:
        return None
    if stripped.startswith(("听说", "求", "蹲", "有没", "想知道", "请问", "Purpose", "P.S.",
                             "P S.", "PS.", "参考", "修正", "对学生", "对导师", "当前", "历史记录",
                             "网页版本", "（很多", "会显示", "不要提", "红榜List", "Fig:", "某些黑榜",
                             "如果你认为", "黑榜链接", "接", "但是", "反驳", "来自")):
        return None
    # Skip lines that are obviously bullets / continuation
    if stripped.startswith(("1.", "2.", "3.", "4.", "5.", "+1")):
        return None
    found = find_institution_in_line(stripped)
    if not found:
        return None
    key, s, e = found
    meta = INSTITUTIONS[key]
    inst_display, region, lat, lon = meta
    # Advisor name: whichever side of the institution keyword has a plausible name.
    left = stripped[:s].strip(" ,，、/()（）")
    right = stripped[e:].strip(" ,，、/()（）")
    # Strip trailing "-> X" or ", pre X" etc. (alternative institution)
    right_clean = re.split(r'\s*(?:->|→|，pre|, pre)\s*', right, maxsplit=1)[0].strip()
    # Strip trailing parenthetical tags for name extraction
    name_match = re.match(r'^([^(（\[【]+)(.*)$', right_clean)
    if name_match and name_match.group(1).strip(" ,，-、"):
        advisor = name_match.group(1).strip(" ,，-、")
        tag = (name_match.group(2) + " " + left).strip()
    elif left:
        # Name is to the left (e.g. "Dingwen Tao IUB")
        # Strip leading "pre", institutions from left
        advisor = left
        tag = ""
    else:
        return None
    # Clean up advisor: remove leading dept qualifiers and institution-word fragments.
    # Apply repeatedly until nothing changes.
    for _ in range(6):
        prev = advisor
        advisor = re.sub(
            r'^(school of \S+|department of \S+|dept\.? of \S+|University|Institute|College|'
            r'CIS|ECE|CS|CSE|EE|prof\.?|Prof\.?|Dr\.?|pre\s+\S+|former\s+\S+)\b\s*',
            '',
            advisor,
            flags=re.IGNORECASE,
        )
        # Strip leading junk punctuation / arrows
        advisor = re.sub(r'^[>→\-_=\s,，、/|]+', '', advisor)
        if advisor == prev:
            break
    advisor = advisor.strip(" ,，-、")
    # Reject if advisor too short/long or is an institution keyword itself
    if len(advisor) < 2 or len(advisor) > 60:
        return None
    if advisor in INSTITUTIONS:
        return None
    # Reject if advisor equals any known institution display name
    known_displays = {v[0] for v in INSTITUTIONS.values()}
    if advisor in known_displays:
        return None
    # Reject if advisor is mostly non-name text (has verbs/commentary)
    if re.search(r'(听说|怎么样|瓜|求求|占坑$|蹲)', advisor):
        return None
    return {
        "institution_key": key,
        "institution_display": inst_display,
        "region": region,
        "lat": lat,
        "lon": lon,
        "advisor": advisor,
        "tag": tag.strip(),
    }


def split_blocks(text):
    blocks, cur = [], []
    for line in text.splitlines():
        if line.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line.rstrip())
    if cur:
        blocks.append(cur)
    return blocks


# ---- Threaded comment parsing ----
OPEN_CLOSE = [("(", ")"), ("（", "）"), ("[", "]"), ("【", "】")]
OPEN_CHARS = {o: c for o, c in OPEN_CLOSE}


def parse_threaded(text):
    text = text.strip()
    root, replies, i, n = [], [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch in OPEN_CHARS:
            close = OPEN_CHARS[ch]
            depth, j = 1, i + 1
            while j < n and depth > 0:
                if text[j] == ch:
                    depth += 1
                elif text[j] == close:
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if depth == 0 and j < n:
                inner = text[i + 1 : j]
                if inner.strip():
                    replies.append(parse_threaded(inner))
                i = j + 1
                continue
            else:
                root.append(ch)
                i += 1
        else:
            root.append(ch)
            i += 1
    return {"text": "".join(root).strip(), "replies": replies}


NSFW_PATTERNS = [
    r"性骚扰", r"性邀约", r"性别歧视", r"骚扰女", r"性侵",
    r"妲\s*己",
    r"泳池party", r"3p", r"三人行", r"三角恋", r"睡.*学生", r"睡.*女",
    r"宫斗", r"出轨", r"性压抑", r"妓女",
    r"harass", r"sexual", r"affair", r"sleeping with", r"prostitute",
]
NSFW_RE = re.compile("|".join(NSFW_PATTERNS), re.IGNORECASE)


def mark_nsfw(node):
    txt = node.get("text", "")
    has = bool(NSFW_RE.search(txt))
    for r in node.get("replies", []):
        mark_nsfw(r)
        if r["nsfw"]:
            has = True
    node["nsfw"] = has
    return node


BULLET_RE = re.compile(r'^\s*(?:[\*\-•·●◦]|\d+[\.\)]|[a-z][\.\)])\s+')


def main():
    text = RAW.read_text(encoding="utf-8").lstrip("\ufeff")
    blocks = split_blocks(text)
    # Track current list type by splitting on 学术界黑榜/学术界红榜 markers.
    list_type = "black"
    advisors = []
    for block in blocks:
        if not block:
            continue
        # Flip list_type if any line in this block is the marker
        for line in block:
            if line.strip() == "学术界红榜":
                list_type = "red"
            elif line.strip() == "学术界黑榜":
                list_type = "black"
        # Find the first line that parses as a heading.
        head = None
        head_idx = None
        for idx, line in enumerate(block):
            h = parse_heading(line)
            if h:
                head = h
                head_idx = idx
                break
        if not head:
            continue
        # Comment lines: everything after heading line in same block.
        comment_lines = block[head_idx + 1 :]
        root_comments = []
        for line in comment_lines:
            stripped = BULLET_RE.sub("", line).strip()
            if not stripped:
                continue
            # Skip marker/noise lines
            if stripped in {"学术界红榜", "学术界黑榜"}:
                continue
            node = parse_threaded(stripped)
            if node["text"] or node["replies"]:
                root_comments.append(node)
        for c in root_comments:
            mark_nsfw(c)
        advisors.append({
            "institution_key": head["institution_key"],
            "institution": head["institution_display"],
            "advisor": head["advisor"],
            "tag": head["tag"],
            "region": head["region"],
            "lat": head["lat"],
            "lon": head["lon"],
            "list_type": list_type,
            "comments": root_comments,
        })

    # Merge duplicates (same institution+advisor)
    merged = {}
    order = []
    for a in advisors:
        key = (a["institution"], a["advisor"].lower())
        if key not in merged:
            merged[key] = a
            order.append(key)
        else:
            merged[key]["comments"].extend(a["comments"])
            if a["list_type"] != merged[key]["list_type"]:
                merged[key]["list_type"] = "both"
            if a["tag"] and a["tag"] not in merged[key]["tag"]:
                merged[key]["tag"] = (merged[key]["tag"] + " " + a["tag"]).strip()

    final = [merged[k] for k in order]
    OUT.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Parsed {len(final)} advisors from {len(blocks)} blocks.")
    print("By region:", dict(Counter(a["region"] for a in final)))
    print("By list:", dict(Counter(a["list_type"] for a in final)))
    # Print advisors with no comments — likely bad parses
    empties = [a for a in final if not a["comments"]]
    print(f"Entries with no comments: {len(empties)}")


if __name__ == "__main__":
    main()
