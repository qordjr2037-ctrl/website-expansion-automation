# gangara 백링크 10분 숫자 보고

생성: 2026-06-19T23:11:50Z

## 핵심 숫자
| 항목 | 값 |
|------|-----|
| **verified live (올라간 백링크)** | **1건** |
| **지난 10분 증가** | **+1건** |
| 일일 목표 | 1000/일 (0.1%) |
| 다음 milestone | 100건 |
| 실패 누적 | 273건 |
| SERP top10 | 0/3 |

## 큐 (backlink_deploy_queue_machine1.json)
- 전체 988 · queued 46 · done 1 · failed 54 · new_signup 887

## platform별 live 성공
web2=1

## 다음 실행
```bash
python3 tools/deploy_backlink_playwright.py --limit 10 --tier S --platform directory
python3 core/run_backlink_auto.py --batch 50
```

계정: `core/notify_secrets.json` → ROOMPANG_USER/PASS, CLICKN_USER/PASS
