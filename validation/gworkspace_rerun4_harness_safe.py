from __future__ import annotations
import hashlib, re, sys
from pathlib import Path
from collections.abc import Mapping, Sequence

SCRIPT_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = SCRIPT_PATH.parents[1]
CANONICAL_RELATIVE_PATH = Path("validation") / "gworkspace_rerun4_harness_safe.py"
CANONICAL_PATH = (REPOSITORY_ROOT / CANONICAL_RELATIVE_PATH).resolve()
if str(REPOSITORY_ROOT) not in sys.path:
 sys.path.insert(0, str(REPOSITORY_ROOT))
from validation.fixtures.fixture_contract import load_fixture_spec

SPEC = load_fixture_spec()
REF_RE = re.compile(r"^gdrv_v1_[A-Za-z0-9_-]{43}$", re.ASCII)
A1_RE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$", re.ASCII)
ORDER = {"CELL_DISPLAY": 0, "CELL_FORMULA": 1, "CELL_NOTE": 2,
         "CELL_HYPERLINK": 3, "CELL_RICH_TEXT_LINK": 4}
EXPECTED = {(coordinate, component): value for coordinate, component, value in SPEC.direct_expectations}
_STRUCTURAL = {item.assertion_type: item for item in SPEC.structural_assertions}
_RICH_TARGETS = _STRUCTURAL["RICH_TEXT_LINK_ORDER"].expected_targets
LEFT, RIGHT = _RICH_TARGETS
class HarnessViolation(Exception):
 def __init__(self, code):
  self.code=code
  super().__init__(code)

def _pos(sheet,a1):
 if type(sheet) is not int or sheet<0 or type(a1) is not str: raise HarnessViolation("PROVENANCE_INVALID")
 m=A1_RE.fullmatch(a1)
 if not m: raise HarnessViolation("PROVENANCE_INVALID")
 col=0
 for c in m.group(1): col=col*26+ord(c)-64
 return sheet,int(m.group(2)),col

def component_identity(p):
 if type(p) is not dict: raise HarnessViolation("PROVENANCE_INVALID")
 pos=_pos(p.get("sheet_ordinal"),p.get("a1")); comp=p.get("component")
 if comp not in ORDER: raise HarnessViolation("PROVENANCE_INVALID")
 if comp=="CELL_RICH_TEXT_LINK":
  run,start,end=(p.get(k) for k in ("rich_text_run_ordinal","rich_text_start_utf16","rich_text_end_utf16"))
  if type(run) is not int or run<0 or type(start) is not int or start<0 or type(end) is not int or end<=start:
   raise HarnessViolation("RICH_TEXT_ORDINAL_UNAVAILABLE")
  return (*pos,comp,run)
 return (*pos,comp,None)

def component_order_key(p):
 ident=component_identity(p); comp=ident[3]
 if comp=="CELL_RICH_TEXT_LINK":
  return (*ident[:3],ORDER[comp],ident[4],p["rich_text_start_utf16"],p["rich_text_end_utf16"])
 return (*ident[:3],ORDER[comp],-1,-1,-1)

def canonicalize_components(chunks):
 keyed=[]
 seen=set()
 for chunk in chunks:
  if type(chunk) is not dict or type(chunk.get("provenance")) is not dict:
   raise HarnessViolation("RESPONSE_SHAPE")
  ident=component_identity(chunk["provenance"])
  if ident in seen: raise HarnessViolation("DUPLICATE_COMPONENT")
  seen.add(ident); keyed.append((component_order_key(chunk["provenance"]),chunk))
 return [chunk for _,chunk in sorted(keyed,key=lambda pair:pair[0])]

def _strings(value,seen=None):
 if seen is None: seen=set()
 if isinstance(value,str): yield value; return
 if isinstance(value,Mapping) or (isinstance(value,Sequence) and not isinstance(value,(str,bytes,bytearray))):
  ident=id(value)
  if ident in seen: return
  seen.add(ident)
  if isinstance(value,Mapping):
   for k,v in value.items():
    yield from _strings(k,seen); yield from _strings(v,seen)
  else:
   for v in value: yield from _strings(v,seen)

def file_ref_valid(value):
 return type(value) is str and REF_RE.fullmatch(value) is not None

class Rerun4Harness:
 def __init__(self,raw_file_id=None,mandatory_sheet_ordinal=0):
  if raw_file_id is not None and (type(raw_file_id) is not str or not raw_file_id):
   raise HarnessViolation("PRIVACY_CONFIG_INVALID")
  if type(mandatory_sheet_ordinal) is not int or mandatory_sheet_ordinal<0: raise HarnessViolation("SHEET_SCOPE_INVALID")
  self.sheet=mandatory_sheet_ordinal
  self.raw=raw_file_id; self.privacy_checked=raw_file_id is not None
  self.refs=set(); self.issued=set(); self.consumed=set(); self.ids=set()
  self.last_key=None; self.states={k:"MISSING" for k in EXPECTED}
  self.rich=[]; self.types=set(); self.opaque=0; self.total=0
  self.last_chunks=-1; self.status="UNKNOWN"; self.cont_present=False; self.progress=None
 def observe_operation(self,http_status=None,auth_ok=True,toctou=False,budget_ok=True):
  if not auth_ok: raise HarnessViolation("AUTH_FAILURE")
  if toctou: raise HarnessViolation("TOCTOU")
  if http_status==429: raise HarnessViolation("HTTP_429")
  if not budget_ok: raise HarnessViolation("BUDGET_VIOLATION")
 def observe_budget(self,griddata_windows,requested_cells,bounded_http_calls):
  vals=(griddata_windows,requested_cells,bounded_http_calls)
  if any(v is None for v in vals): return "NOT_DIRECTLY_OBSERVABLE"
  if any(type(v) is not int or v<0 for v in vals): raise HarnessViolation("BUDGET_VIOLATION")
  if griddata_windows>8 or requested_cells>8000 or bounded_http_calls>11: raise HarnessViolation("BUDGET_VIOLATION")
  return "PASS"
 def observe_progress(self,logical_progress,continuation_pending,continuation_advanced):
  if type(logical_progress) is not int or logical_progress<0 or type(continuation_pending) is not bool or type(continuation_advanced) is not bool:
   raise HarnessViolation("PROGRESS_INVALID")
  if self.progress is not None and logical_progress<self.progress: raise HarnessViolation("NON_MONOTONIC_PROGRESS")
  if continuation_pending and self.progress is not None and logical_progress==self.progress and not continuation_advanced:
   raise HarnessViolation("ZERO_PROGRESS_LOOP")
  self.progress=logical_progress
 def ingest(self,response,request_continuation=None):
  if type(response) is not dict: raise HarnessViolation("RESPONSE_SHAPE")
  if request_continuation is not None:
   if type(request_continuation) is not str or request_continuation not in self.issued or request_continuation in self.consumed:
    raise HarnessViolation("CONTINUATION_REPLAY")
   self.consumed.add(request_continuation)
  if self.raw is not None and any(self.raw in s for s in _strings(response)):
   raise HarnessViolation("RAW_ID_PRIVACY")
  status=response.get("processing_status")
  if type(status) is not str: raise HarnessViolation("OUTCOME_INVALID")
  self.status=status
  if status in {"FAILED","CHANGED_DURING_AUDIT"} or response.get("safe_error_code") is not None or response.get("failure_stage") is not None:
   raise HarnessViolation("OPERATION_FAILURE")
  token=response.get("continuation_token")
  if token is not None:
   if type(token) is not str or not token or token in self.issued: raise HarnessViolation("CONTINUATION_REPLAY")
   self.issued.add(token)
  self.cont_present=token is not None
  chunks=response.get("chunks")
  if type(chunks) is not list: raise HarnessViolation("RESPONSE_SHAPE")
  self.last_chunks=len(chunks); self.total+=len(chunks)
  for chunk in canonicalize_components(chunks):
   ref=chunk.get("file_ref"); text=chunk.get("text"); p=chunk["provenance"]
   if not file_ref_valid(ref): raise HarnessViolation("FILE_REF_FORMAT")
   self.refs.add(ref)
   if len(self.refs)>1: raise HarnessViolation("FILE_REF_UNSTABLE")
   if type(text) is not str: raise HarnessViolation("RESPONSE_SHAPE")
   ident=component_identity(p); key=component_order_key(p)
   if ident in self.ids: raise HarnessViolation("DUPLICATE_COMPONENT")
   self.ids.add(ident)
   if self.last_key is not None and key<self.last_key: raise HarnessViolation("NON_MONOTONIC_PROGRESS")
   self.last_key=key
   comp=p["component"]; a1=p["a1"]; self.types.add(comp)
   if p["sheet_ordinal"]!=self.sheet: self.opaque+=1; continue
   pair=(a1,comp)
   if pair in EXPECTED:
    want=EXPECTED[pair]
    ok=text==want
    self.states[pair]="PASS" if ok else "FAIL"
    if pair==("E1","CELL_RICH_TEXT_LINK"): pass
   elif a1=="E1" and comp=="CELL_RICH_TEXT_LINK":
    self.rich.append((p["rich_text_run_ordinal"],text))
   else: self.opaque+=1
 def final_assertions(self):
  out={f"{a}/{c}":s for (a,c),s in self.states.items()}
  ordered=sorted(self.rich,key=lambda x:x[0])
  for assertion in SPEC.structural_assertions:
   if assertion.assertion_type=="RICH_TEXT_LINK_COUNT":
    out[assertion.assertion_id]="MISSING" if not ordered else ("PASS" if len(ordered)==assertion.expected_count else "FAIL")
   elif assertion.assertion_type=="RICH_TEXT_LINK_ORDER":
    actual=tuple(value for _,value in ordered)
    out[assertion.assertion_id]="MISSING" if not ordered else ("PASS" if actual==assertion.expected_targets else "FAIL")
   elif assertion.assertion_type=="MERGED_RANGE":
    prohibited=(*_pos(self.sheet,assertion.related_coordinate),assertion.component,None)
    absent=prohibited not in self.ids
    out[assertion.assertion_id]="PASS" if self.states[(assertion.coordinate,"CELL_DISPLAY")] == "PASS" and absent else "FAIL"
   elif assertion.assertion_type=="COMPONENT_PROHIBITED":
    prohibited=(*_pos(self.sheet,assertion.coordinate),assertion.component,None)
    out[assertion.assertion_id]="PASS" if prohibited not in self.ids else "FAIL"
   elif assertion.assertion_type=="COMPONENT_TYPE_PRESENT":
    out[assertion.assertion_id]="PASS" if assertion.component in self.types else "MISSING"
  return out
 def repair_indicators(self):
  states=self.final_assertions()
  v1=states["A1/CELL_DISPLAY"]
  v2_states=(states["E1/RICH_LINK_COUNT"],states["E1/RICH_LINK_ORDER"],states["TYPE/CELL_RICH_TEXT_LINK"])
  v2="FAIL" if "FAIL" in v2_states else ("PASS" if all(value=="PASS" for value in v2_states) else "MISSING")
  return {"REPAIR_V1":v1,"REPAIR_V2":v2}
 def terminal_contract(self):
  return "PASS" if self.status=="EMPTY" and self.last_chunks==0 and not self.cont_present and self.total>0 else "FAIL"
 def safe_report(self):
  states=self.final_assertions()
  lines=["NON_MANDATORY=OPAQUE_ACCEPTED",f"OPAQUE_COMPONENTS={self.opaque}",
   "RAW_ID_PRIVACY="+("PASS" if self.privacy_checked else "UNCHECKED"),
   "FILE_REF_STABILITY="+("PASS" if len(self.refs)==1 else "MISSING"),
   "CONTINUATION="+("PRESENT" if self.cont_present else "ABSENT"),
   "TERMINAL_CONTRACT="+self.terminal_contract()]
  lines.extend(f"{key}={value}" for key,value in self.repair_indicators().items())
  lines.extend(f"{k}={v}" for k,v in states.items())
  result="\n".join(lines)
  if not result.isascii(): raise HarnessViolation("DIAGNOSTIC_NOT_ASCII")
  return result
 def enforce_final(self):
  if any(v!="PASS" for v in self.final_assertions().values()): raise HarnessViolation("MANDATORY_ASSERTION_FAIL")
  if not self.privacy_checked: raise HarnessViolation("RAW_ID_PRIVACY_UNCHECKED")
  if len(self.refs)!=1: raise HarnessViolation("FILE_REF_STABILITY")
  if self.terminal_contract()!="PASS": raise HarnessViolation("TERMINAL_CONTRACT")

def _chunk(a,c,t,run=None,start=None,end=None,ref="gdrv_v1_"+"A"*43,sheet=0):
 p={"a1":a,"component":c,"sheet_ordinal":sheet}
 if run is not None:
  p.update(rich_text_run_ordinal=run,rich_text_start_utf16=run*5 if start is None else start,
           rich_text_end_utf16=run*5+4 if end is None else end)
 return {"file_ref":ref,"text":t,"provenance":p}
def _matrix():
 x=[_chunk(a,c,"#DIV/0!" if v is None else v) for (a,c),v in EXPECTED.items()]
 x += [_chunk("E1","CELL_RICH_TEXT_LINK",LEFT,0,0,4),_chunk("E1","CELL_RICH_TEXT_LINK",RIGHT,1,5,9)]
 return x
def _check_precheck(path,expected):
 if not _canonical_location_valid() or Path(path).resolve()!=CANONICAL_PATH.resolve(): raise HarnessViolation("CANONICAL_PATH_MISMATCH")
 if not re.fullmatch(r"[A-Fa-f0-9]{64}",expected or "",re.ASCII): raise HarnessViolation("EXPECTED_HASH_INVALID")
 if hashlib.sha256(CANONICAL_PATH.read_bytes()).hexdigest().lower()!=expected.lower(): raise HarnessViolation("CANONICAL_HASH_MISMATCH")
 return True

def _canonical_location_valid():
 try:
  return (SCRIPT_PATH==CANONICAL_PATH and SCRIPT_PATH.relative_to(REPOSITORY_ROOT).as_posix()==CANONICAL_RELATIVE_PATH.as_posix()
          and (REPOSITORY_ROOT/"pyproject.toml").is_file() and (REPOSITORY_ROOT/".git").exists())
 except (OSError,ValueError):
  return False

def run_self_tests(emit=True):
 tests=[]
 def check(name,fn):
  try: fn(); tests.append((name,True))
  except Exception: tests.append((name,False))
 def opaque(text):
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":[_chunk("Z899","CELL_DISPLAY",text)]})
  r=h.safe_report(); assert "OPAQUE_COMPONENTS=1" in r and text not in r
 check("opaque_ascii",lambda:opaque("UNEXPECTED_PRIVATE_ASCII"))
 def privacy_unchecked():
  assert "RAW_ID_PRIVACY=UNCHECKED" in Rerun4Harness().safe_report()
 check("privacy_unchecked_is_not_pass",privacy_unchecked)
 check("opaque_unicode",lambda:opaque("\u4efb\u610e\U0001F600"))
 def good():
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":_matrix()})
  assert all(v=="PASS" for v in h.final_assertions().values())
 check("mandatory_correct",good)
 def wrong():
  x=_matrix(); next(z for z in x if z["provenance"]["a1"]=="B1" and z["provenance"]["component"]=="CELL_FORMULA")["text"]="PRIVATE_ACTUAL"
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":x}); r=h.safe_report()
  assert "B1/CELL_FORMULA=FAIL" in r and "PRIVATE_ACTUAL" not in r
 check("mandatory_wrong_redacted",wrong)
 def missing():
  h=Rerun4Harness(); h.ingest({"processing_status":"EMPTY","chunks":[]})
  assert h.final_assertions()["A1/CELL_DISPLAY"]=="MISSING"
 check("mandatory_missing",missing)
 def privacy():
  raw="synthetic-raw-id"
  h=Rerun4Harness(raw);
  try: h.ingest({"processing_status":"PROCESSED","chunks":[_chunk("A1","CELL_DISPLAY",raw)]})
  except HarnessViolation as e: assert e.code=="RAW_ID_PRIVACY" and raw not in str(e)
  else: raise AssertionError
  h=Rerun4Harness(raw); h.ingest({"processing_status":"EMPTY","chunks":[]})
  assert "RAW_ID_PRIVACY=PASS" in h.safe_report()
 check("raw_id_privacy",privacy)
 def grammar():
  assert file_ref_valid("gdrv_v1_"+"A"*43) and not file_ref_valid("gdrv_v1_bad")
  try: Rerun4Harness().ingest({"processing_status":"PROCESSED","chunks":[_chunk("A1","CELL_DISPLAY","x",ref="gdrv_v1_bad")]})
  except HarnessViolation as e: assert e.code=="FILE_REF_FORMAT"
  else: raise AssertionError
 check("file_ref_grammar",grammar)
 def stable():
  h=Rerun4Harness(); token="SYNTH_TOKEN"
  h.ingest({"processing_status":"PARTIALLY_PROCESSED","continuation_token":token,"chunks":[_chunk("A1","CELL_DISPLAY","a")]})
  try: h.ingest({"processing_status":"PROCESSED","chunks":[_chunk("A2","CELL_DISPLAY","b",ref="gdrv_v1_"+"B"*43)]},request_continuation=token)
  except HarnessViolation as e: assert e.code=="FILE_REF_UNSTABLE"
  else: raise AssertionError
 check("file_ref_stability",stable)
 def redact():
  token="SYNTH_CONTINUATION_SECRET"; value="ARBITRARY_RESPONSE_TEXT"
  h=Rerun4Harness(); h.ingest({"processing_status":"PARTIALLY_PROCESSED","continuation_token":token,"chunks":[_chunk("Z899","CELL_DISPLAY",value)]})
  r=h.safe_report(); assert token not in r and value not in r and r.isascii()
 check("continuation_and_values_never_output",redact)
 def guards():
  for kw,code in [({"http_status":429},"HTTP_429"),({"auth_ok":False},"AUTH_FAILURE"),({"toctou":True},"TOCTOU"),({"budget_ok":False},"BUDGET_VIOLATION")]:
   try: Rerun4Harness().observe_operation(**kw)
   except HarnessViolation as e: assert e.code==code
   else: raise AssertionError
  assert Rerun4Harness().observe_budget(8,8000,11)=="PASS"
  try: Rerun4Harness().observe_budget(9,8000,11)
  except HarnessViolation as e: assert e.code=="BUDGET_VIOLATION"
  else: raise AssertionError
 check("hard_guards",guards)
 def replay():
  h=Rerun4Harness(); t="SYNTH_REPLAY"
  h.ingest({"processing_status":"PARTIALLY_PROCESSED","continuation_token":t,"chunks":[]})
  h.ingest({"processing_status":"PARTIALLY_PROCESSED","continuation_token":"SYNTH_NEXT","chunks":[]},request_continuation=t)
  try: h.ingest({"processing_status":"EMPTY","chunks":[]},request_continuation=t)
  except HarnessViolation as e: assert e.code=="CONTINUATION_REPLAY" and t not in str(e)
  else: raise AssertionError
 check("continuation_replay_guard",replay)
 def merge_spill():
  x=_matrix()+[_chunk("B6","CELL_DISPLAY","CLONE"),_chunk("P1","CELL_FORMULA","=SEQUENCE(1,2)")]
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":x}); r=h.safe_report()
  assert h.final_assertions()["A6:B6/MERGED"]=="FAIL" and h.final_assertions()["P1/SPILL_NO_FORMULA"]=="FAIL" and "CLONE" not in r
 check("merge_and_spill_anchor",merge_spill)
 def progress():
  h=Rerun4Harness(); h.observe_progress(3,True,True)
  for n,a,c in [(3,False,"ZERO_PROGRESS_LOOP"),(2,True,"NON_MONOTONIC_PROGRESS")]:
   try: h.observe_progress(n,True,a)
   except HarnessViolation as e: assert e.code==c
   else: raise AssertionError
 check("monotonic_zero_progress_guard",progress)
 def rich():
  x=[_chunk("E1","CELL_DISPLAY","LEFT RIGHT"),_chunk("E1","CELL_RICH_TEXT_LINK",RIGHT,1,5,9),_chunk("E1","CELL_RICH_TEXT_LINK",LEFT,0,0,4)]
  y=canonicalize_components(x); assert [z["provenance"]["rich_text_run_ordinal"] for z in y[1:]]==[0,1]
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":x})
  assert h.final_assertions()["E1/RICH_LINK_ORDER"]=="PASS"
 check("rich_text_same_cell_distinct_ordinals",rich)
 def rich_actual():
  x=[_chunk("E1","CELL_RICH_TEXT_LINK",RIGHT,2,5,9),_chunk("E1","CELL_RICH_TEXT_LINK",LEFT,0,0,4)]
  y=canonicalize_components(x); assert [z["text"] for z in y]==[LEFT,RIGHT]
 check("rich_text_actual_ordinal_not_value_sort",rich_actual)
 def dup():
  try: canonicalize_components([_chunk("E1","CELL_RICH_TEXT_LINK",LEFT,0,0,4),_chunk("E1","CELL_RICH_TEXT_LINK",RIGHT,0,5,9)])
  except HarnessViolation as e: assert e.code=="DUPLICATE_COMPONENT"
  else: raise AssertionError
 check("rich_text_duplicate_same_ordinal",dup)
 def mismatch():
  private="https://private.invalid/unexpected"
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":[_chunk("E1","CELL_RICH_TEXT_LINK",private,0,0,4),_chunk("E1","CELL_RICH_TEXT_LINK",RIGHT,1,5,9)]})
  assert "E1/RICH_LINK_ORDER=FAIL" in h.safe_report() and private not in h.safe_report()
 check("rich_text_mismatch_redacted",mismatch)
 def canon():
  assert Path(__file__).resolve()==CANONICAL_PATH.resolve() and _canonical_location_valid()
  digest=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
  assert _check_precheck(__file__,digest)
  alternate=CANONICAL_PATH.with_name("gworkspace_rerun4_harness_copy.py")
  for path,expected,code in [(Path(__file__),"0"*64,"CANONICAL_HASH_MISMATCH"),(alternate,digest,"CANONICAL_PATH_MISMATCH")]:
   try: _check_precheck(path,expected)
   except HarnessViolation as e: assert e.code==code
   else: raise AssertionError
 check("canonical_harness_precheck_no_fallback",canon)
 def sheet_scope():
  h=Rerun4Harness(mandatory_sheet_ordinal=1)
  h.ingest({"processing_status":"PROCESSED","chunks":[_chunk("A1","CELL_DISPLAY","OPAQUE_OTHER_TAB",sheet=0),_chunk("A1","CELL_DISPLAY",EXPECTED[("A1","CELL_DISPLAY")],sheet=1)]})
  assert h.final_assertions()["A1/CELL_DISPLAY"]=="PASS" and h.opaque==1
 check("mandatory_sheet_scope",sheet_scope)
 def repair_indicators():
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":_matrix()})
  states=h.final_assertions()
  assert len(states)==31 and all(value=="PASS" for value in states.values())
  assert h.repair_indicators()=={"REPAIR_V1":"PASS","REPAIR_V2":"PASS"}
  assert all(states["TYPE/"+component]=="PASS" for component in ORDER)
 check("repair_indicators_and_five_components",repair_indicators)
 def missing_single():
  chunks=[chunk for chunk in _matrix() if not (chunk["provenance"]["a1"]=="A1" and chunk["provenance"]["component"]=="CELL_DISPLAY")]
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":chunks})
  states=h.final_assertions()
  assert sum(value=="MISSING" for value in states.values())==1 and states["A1/CELL_DISPLAY"]=="MISSING"
  assert h.repair_indicators()["REPAIR_V1"]=="MISSING"
 check("single_missing_assertion",missing_single)
 def fail_and_mixed():
  wrong=[dict(chunk) for chunk in _matrix()]
  next(chunk for chunk in wrong if chunk["provenance"]["a1"]=="B1" and chunk["provenance"]["component"]=="CELL_FORMULA")["text"]="PRIVATE_WRONG_FORMULA"
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":wrong})
  states=h.final_assertions()
  assert sum(value=="FAIL" for value in states.values())==1 and states["B1/CELL_FORMULA"]=="FAIL"
  missing=[chunk for chunk in wrong if not (chunk["provenance"]["a1"]=="A1" and chunk["provenance"]["component"]=="CELL_DISPLAY")]
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":missing})
  states=h.final_assertions(); report=h.safe_report()
  assert sum(value=="FAIL" for value in states.values())==1 and sum(value=="MISSING" for value in states.values())==1
  assert "PRIVATE_WRONG_FORMULA" not in report and states["A1/CELL_DISPLAY"]=="MISSING" and states["B1/CELL_FORMULA"]=="FAIL"
 check("single_fail_and_mixed_fail_missing",fail_and_mixed)
 def repair_v1_v2_fail():
  x=_matrix()
  next(chunk for chunk in x if chunk["provenance"]["a1"]=="A1" and chunk["provenance"]["component"]=="CELL_DISPLAY")["text"]="PRIVATE_V1"
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":x})
  assert h.repair_indicators()["REPAIR_V1"]=="FAIL"
  x=_matrix()
  next(chunk for chunk in x if chunk["provenance"]["component"]=="CELL_RICH_TEXT_LINK")["text"]="PRIVATE_V2"
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":x})
  assert h.repair_indicators()["REPAIR_V2"]=="FAIL" and "PRIVATE_V2" not in h.safe_report()
 check("repair_v1_v2_invalid_anchors_redacted",repair_v1_v2_fail)
 def rich_missing():
  x=[chunk for chunk in _matrix() if chunk["provenance"]["component"]!="CELL_RICH_TEXT_LINK"]
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":x})
  states=h.final_assertions()
  assert states["E1/RICH_LINK_COUNT"]=="MISSING" and states["E1/RICH_LINK_ORDER"]=="MISSING"
  assert states["TYPE/CELL_RICH_TEXT_LINK"]=="MISSING" and h.repair_indicators()["REPAIR_V2"]=="MISSING"
 check("repair_v2_missing_rich_text",rich_missing)
 def terminal_empty_retained():
  h=Rerun4Harness(); h.ingest({"processing_status":"PROCESSED","chunks":_matrix()})
  prior=h.total
  h.ingest({"processing_status":"EMPTY","chunks":[]})
  assert prior>0 and h.total==prior and h.last_chunks==0 and h.terminal_contract()=="PASS"
 check("terminal_empty_aggregate_retained",terminal_empty_retained)
 ok=all(v for _,v in tests)
 if emit:
  for name,passed in tests: print(("PASS " if passed else "FAIL ")+name)
  print("SELF_TESTS="+("PASS" if ok else "FAIL")+" COUNT="+str(len(tests)))
 return ok

def main():
 args=sys.argv[1:]
 if args==["--self-test"]: return 0 if run_self_tests() else 1
 if len(args)==3 and args[0]=="--precheck" and args[1]=="--expected-sha256":
  try: _check_precheck(__file__,args[2])
  except HarnessViolation as e: print("PRECHECK=FAIL CODE="+e.code); return 1
  print("CANONICAL_PATH=PASS"); print("CANONICAL_SHA256=PASS")
  return 0 if run_self_tests() else 1
 print("USAGE=CANONICAL_HARNESS --self-test OR --precheck --expected-sha256 HASH")
 return 2
if __name__=="__main__": raise SystemExit(main())
