"""Frozen exact-value prefecture membership contract v0.1."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

PREFECTURE_MAPPING_CONTRACT_VERSION = "0.1"
PREFECTURE_TAXONOMY_VERSION = "0.1"
PREFECTURE_TAXONOMY_PATH = Path("schema/prefecture/prefecture_taxonomy_v0_1.csv")
PREFECTURE_CROSSWALK_PATH = Path("schema/prefecture/prefecture_crosswalk_v0_1.csv")
PREFECTURE_SCHEMA_PATH = Path("schema/sqlite/admission_search_prefecture_schema_v0_1.sql")
PREFECTURE_DESIGN_PATH = Path("docs/prefecture_search_design_v0_1.md")
PREFECTURE_TAXONOMY_SHA256 = "d91fe231cde5698b074a8c86328dd61499aeccac32da2472e36a0e184457f906"
PREFECTURE_CROSSWALK_SHA256 = "46a5c032e2fc79cd2d1cbfbc33b1dac5952e70300b557fd1884558d52153481c"

@dataclass(frozen=True)
class Prefecture:
    code: str
    label: str
    region: str
    display_order: int

@dataclass(frozen=True)
class PrefectureMapping:
    raw_value: str | None
    mapping_status: str
    codes: tuple[str, ...]
    review_note: str | None

class PrefectureTaxonomy:
    def __init__(self, items: tuple[Prefecture, ...]):
        self.items=items; self.by_code={x.code:x for x in items}; self.by_label={x.label:x for x in items}
    @classmethod
    def load(cls,path:Path)->"PrefectureTaxonomy":
        with path.open(encoding="utf-8",newline="") as f: rows=list(csv.DictReader(f))
        items=tuple(Prefecture(r["prefecture_code"],r["prefecture_label"],r["region"],int(r["display_order"])) for r in rows)
        if len(items)!=47 or len({x.code for x in items})!=47 or [x.display_order for x in items]!=list(range(1,48)):
            raise ValueError("Prefecture taxonomy must contain 47 unique ordered rows.")
        return cls(items)
    def __iter__(self): return iter(self.items)

class PrefectureCrosswalk:
    def __init__(self, mappings:dict[str,PrefectureMapping], taxonomy:PrefectureTaxonomy): self.mappings=mappings; self.taxonomy=taxonomy
    @classmethod
    def load(cls,path:Path,taxonomy:PrefectureTaxonomy)->"PrefectureCrosswalk":
        with path.open(encoding="utf-8",newline="") as f: rows=list(csv.DictReader(f))
        grouped:dict[str,list[dict[str,str]]]={}
        for row in rows:
            if row["mapping_contract_version"]!=PREFECTURE_MAPPING_CONTRACT_VERSION: raise ValueError("Prefecture crosswalk version mismatch.")
            grouped.setdefault(row["raw_value"],[]).append(row)
        mappings={}
        for raw, entries in grouped.items():
            statuses={x["mapping_status"] for x in entries}; codes=tuple(x["prefecture_code"] for x in entries)
            if len(statuses)!=1 or any(code not in taxonomy.by_code for code in codes): raise ValueError(f"Invalid prefecture crosswalk: {raw!r}")
            status=next(iter(statuses)); expected="single" if len(codes)==1 else "multi"
            if status!=expected or [int(x["membership_order"]) for x in entries]!=list(range(1,len(entries)+1)): raise ValueError(f"Invalid prefecture cardinality: {raw!r}")
            mappings[raw]=PrefectureMapping(raw,status,codes,entries[0]["review_note"] or None)
        return cls(mappings,taxonomy)
    def lookup(self,raw:str|None)->PrefectureMapping:
        if raw is None: return PrefectureMapping(None,"not_applicable",(),"原値がSQL NULL")
        return self.mappings.get(raw,PrefectureMapping(raw,"unmapped",(),"監査済みcrosswalkにない新規原値"))
    def __len__(self): return len(self.mappings)
