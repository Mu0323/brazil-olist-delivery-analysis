"""run_all_sql.py — 一键跑完所有分析SQL"""
import duckdb, os, time, re

BASE = os.path.dirname(__file__)
DB = os.path.join(BASE, "smartquery.duckdb")
DIR = os.path.join(BASE, "项目", "scripts")
os.makedirs(os.path.join(BASE, "outputs"), exist_ok=True)

con = duckdb.connect(DB)

files = [
    ("01 核心指标", "01_core_metrics.sql"),
    ("02 漏斗分析", "02_funnel.sql"),
    ("03 RFM分层",   "03_rfm.sql"),
    ("04 延误分析", "04_delay_analysis.sql"),
]

for label, fname in files:
    fpath = os.path.join(DIR, fname)
    if not os.path.exists(fpath):
        print(f"[跳过] {label}")
        continue

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    with open(fpath, "r", encoding="utf-8") as f:
        raw = f.read()

    # 按分号分割语句，去掉空的和纯注释的
    stmts = []
    for part in raw.split(";"):
        lines = [l for l in part.split("\n") if not l.strip().startswith("--")]
        clean = " ".join(lines).strip().replace("  ", " ")
        if clean:
            stmts.append(clean)

    for i, stmt in enumerate(stmts):
        try:
            t0 = time.time()
            res = con.execute(stmt)
            t = time.time() - t0
            upper = stmt.strip().upper()
            if upper.startswith("SELECT") or "SELECT" in upper[:30]:
                df = res.fetchdf()
                print(f"\n  [{i+1}] ({t:.1f}s) {df.shape[0]} 行")
                print(df.to_string(index=False))
            else:
                print(f"  [{i+1}] OK ({t:.1f}s)")
        except Exception as e:
            print(f"  [{i+1}] 错误: {e}")

con.close()
print(f"\n{'='*60}")
print("完成！")
