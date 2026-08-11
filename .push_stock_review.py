#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stock-review 站点统一发布脚本。

由各内容生成自动化（days/ 每日复盘、market-cycle 市场周期、sector-flow 板块资金流）
在生成完产物后调用，完成：git fetch -> git add -> commit -> push -> 触发 Pages 重建。

安全约定：
- PAT 通过 --pat 参数传入，脚本本身不含任何密钥，可安全提交到公开仓库。
- git push / curl 的 token 不回显到 stdout。
"""
import subprocess
import sys
import os
import datetime

REPO = r"D:/新建文件夹 (3)/Claw/stock-review"
REMOTE_BASE = "https://github.com/linwanyan0-star/stock-review.git"
PAGES_API = "https://api.github.com/repos/linwanyan0-star/stock-review/pages/builds"
USER = "linwanyan0-star"
EMAIL = "linwanyan0-star@users.noreply.github.com"


def parse_pat(argv):
    for i, a in enumerate(argv):
        if a in ("--pat", "-p") and i + 1 < len(argv):
            return argv[i + 1]
    return None


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    pat = parse_pat(sys.argv[1:])
    if not pat:
        print("ERROR: --pat <token> required")
        sys.exit(1)

    auth_remote = REMOTE_BASE.replace("https://", f"https://x-access-token:{pat}@")
    today = datetime.date.today().strftime("%Y-%m-%d")

    os.chdir(REPO)

    # 1. 拉平远程已知历史（避免非快进被拒）
    run(["git", "fetch", auth_remote, "main"], check=False)

    # 2. 暂存所有公开内容（.gitignore 已拦截私密/中间产物）
    run(["git", "add", "-A"], check=False)

    # 3. 有暂存改动则提交
    r = run(["git", "diff", "--cached", "--quiet"])
    if r.returncode != 0:
        run(["git", "-c", f"user.name={USER}", "-c", f"user.email={EMAIL}",
             "commit", "-m", f"daily sync {today}"], check=False)

    # 4. 本地是否领先远程（含已提交未推送的情况）
    cnt = run(["git", "rev-list", "--count", "FETCH_HEAD..HEAD"])
    try:
        ahead = int((cnt.stdout or "0").strip())
    except ValueError:
        ahead = 0
    if ahead <= 0:
        print("[push] 无变更，跳过推送")
        return

    # 5. 推送（token 不回显）
    pr = run(["git", "push", auth_remote, "main"])
    if pr.returncode != 0:
        # 推送失败：输出非敏感部分
        out = (pr.stderr or pr.stdout or "")
        if "non-fast-forward" in out or "rejected" in out:
            print("[push] 被拒（non-fast-forward），请检查远程是否有未拉取的改动")
        else:
            print("[push] 推送失败，详见自动化执行日志")
        sys.exit(1)
    print(f"[push] 已推送 daily sync {today}")

    # 6. 触发 Pages 重建
    curl = f'curl -s -o /dev/null -w "%{{http_code}}" -X POST -H "Authorization: Bearer {pat}" -H "Accept: application/vnd.github+json" {PAGES_API}'
    cr = run(curl, shell=True)
    print(f"[pages] 重建返回: {cr.stdout.strip()}")


if __name__ == "__main__":
    main()
