"""Generate a read-only Go auditor for historical replay files.

python scripts/server_replay_audit.py OUTPUT.go [--baseline]
Build OUTPUT.go with Go, then run: AUDITOR QTABLE TASK_DIRS.txt REPORT.json.
TASK_DIRS.txt contains one sampler directory (holding manifest.json) per line,
ordered by (M,k,d). Reports preserve completed-block counts if interrupted.
The default sorts observations before exhaustive search using a proven upper
bound; --baseline retains the original search. Both compare every group field.
"""
import argparse
from pathlib import Path
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
src = (root / 'sim/peelsim/e0extract/r22replay.go').read_text()
src=src.replace('"flag"','"reflect"').replace('\n\t"sync"','')
a=src.index('func main() {'); b=src.index('\nfunc readJSON',a)
src=src[:a]+r'''// Audit-only harness: unchanged sizing and record reader, cache reused across blocks of one M,k.
var shared = map[string]map[string]*rawEngine{}
func main() {
    var qtab map[string]map[string]float64
    must(readJSON(os.Args[1], &qtab))
    tasks,err:=os.Open(os.Args[2]); must(err); defer tasks.Close()
    sc:=bufio.NewScanner(tasks)
    checked, records, mismatches := 0, int64(0), 0
    var problems []string
    emit:=func() {
        f,err:=os.Create(os.Args[3]); must(err); defer f.Close()
        must(json.NewEncoder(f).Encode(map[string]any{"blocks":checked,"records":records,"mismatched_blocks":mismatches,"problems":problems,"complete":false}))
    }
    for sc.Scan() {
        dir:=sc.Text()
        var man manifest; must(readJSON(filepath.Join(dir,"manifest.json"), &man))
        if len(man.Configs)!=1 { panic("expected one config per task") }
        got:=runCfg(dir,&man,man.Configs[0],qtab,0)
        var orig struct { Runs map[string][]map[string]any `json:"runs"` }
        must(readJSON(filepath.Join(filepath.Dir(dir),"replay.json"), &orig))
        var want map[string]any
        if len(orig.Runs)!=1 { panic("expected one replay run") }
        for _,v:=range orig.Runs { if len(v)!=1 {panic("expected one replay config")}; want=v[0] }
        raw,err:=json.Marshal(got["groups"]); must(err)
        var groups any; must(json.Unmarshal(raw,&groups))
        if !reflect.DeepEqual(groups,want["groups"]) {
            mismatches++; if len(problems)<30 {problems=append(problems,dir)}
        }
        checked++; records+=got["meta"].(map[string]any)["records"].(int64)
        emit()
    }
    must(sc.Err())
    f,err:=os.Create(os.Args[3]); must(err); defer f.Close()
    must(json.NewEncoder(f).Encode(map[string]any{"blocks":checked,"records":records,"mismatched_blocks":mismatches,"problems":problems,"complete":true}))
}
''' +src[b:]
src=src.replace('eng := map[string]*rawEngine{"raw01": newRawShared(pc, 0.01, true), "raw05": newRawShared(pc, 0.05, true)}', '''key := fmt.Sprintf("%d,%d",M,k)
    eng:=shared[key]
    if eng==nil {
        shared=map[string]map[string]*rawEngine{}
        eng=map[string]*rawEngine{"raw01": newRawShared(pc, 0.01, true), "raw05": newRawShared(pc, 0.05, true)}
        shared[key]=eng
    }''')


if not args.baseline:
    src=src.replace('var shared = map[string]map[string]*rawEngine{}','var shared = map[string]map[string]*rawEngine{}\nvar auditCaps = map[*rawEngine]int64{}')
    src=src.replace('for n := stop - 1; n >= 2; n-- {','if cap, ok := auditCaps[e]; ok && stop > cap+1 { stop = cap+1 }\n\t\tfor n := stop - 1; n >= 2; n-- {')
    needle='\tgs := map[string]*group'
    a=src.index(needle)
    src=src[:a]+r'''
        // For a fixed candidate n, accepts(n,S2) is nondecreasing in S2.
        // Therefore U is nondecreasing too, even when accepts is nonmonotone in n.
        // Evaluate distinct observations from largest to smallest; the previous U
        // is a proven upper bound for the next exhaustive descending search.
        unique:=map[int64]bool{}
        parts,_:=filepath.Glob(filepath.Join(dir,fmt.Sprintf("cfg_%03d",ci),"chunk_*.bin"))
        for _,path:=range parts {
            data,err:=os.ReadFile(path);must(err)
            if len(data)%man.RecordBytes!=0 { panic("partial record") }
            for off:=0;off<len(data);off+=man.RecordBytes {
                s2:=int64(int32(binary.LittleEndian.Uint32(data[off+4*idx["S2_rand"]:])))
                unique[s2]=true
            }
        }
        values:=make([]int64,0,len(unique));for x:=range unique {values=append(values,x)}
        sort.Slice(values,func(i,j int)bool{return values[i]>values[j]})
        for _,e:=range eng {
            delete(auditCaps,e)
            for i,s2:=range values {
                if i>0 && auditCaps[e]<0 { e.ucache[s2]=-1;continue }
                u:=e.upper(s2);auditCaps[e]=u
            }
            delete(auditCaps,e)
        }
    ''' +src[a:]

args.output.write_text(src)
