# gangara.co.kr fusion 배포

## 소스
`website 확장 수집/templates/gangara-hub/` → `/public_html`

## 1클릭 (권장) — GitHub Secrets
Repository **Settings → Secrets → Actions** 에 추가:
- `GANGARA_FTP_USER` — cPanel/FTP 아이디
- `GANGARA_FTP_PASS` — cPanel/FTP 비밀번호
- (선택) `GANGARA_FTP_HOST` — 기본 `gangara.co.kr`
- (선택) `GANGARA_FTP_REMOTE` — 기본 `/public_html`

Actions → **Deploy gangara.co.kr hub** → Run workflow

## 로컬 (한국 IP)
```bash
GANGARA_FTP_USER=아이디 GANGARA_FTP_PASS=비밀번호 python3 tools/deploy_gangara_hub.py
```

## cPanel 브라우저
```bash
GANGARA_CPANEL_USER=아이디 GANGARA_CPANEL_PASS=비밀번호 HEADLESS=0 python3 tools/deploy_gangara_cpanel.py
```

## zip 수동
`tools/gangara-hub-deploy.zip` → cPanel File Manager → public_html 업로드 → Extract

## 검증
- https://gangara.co.kr/ H1: `강남 가라오케·하이퍼블릭·풀싸롱·쩜오 2026 완벽 가이드`
- canonical: `https://gangara.co.kr/`
- sitemap 5 URL
