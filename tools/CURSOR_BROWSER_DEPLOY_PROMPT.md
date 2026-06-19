# Cursor Browser — gangara.co.kr fusion 배포 프롬프트

아래 블록 **전체 복사** → Cursor **Browser** 모드 채팅에 붙여넣기.  
(내 PC 브라우저에서 cPanel/호스팅에 이미 로그인된 상태가 가장 좋음)

---

## 프롬프트 A — cPanel File Manager (gangara.co.kr, 권장)

```
## 목표
repo `website-expansion-automation`의 fusion 허브를 **https://gangara.co.kr/** live에 배포한다.
Cloud Agent/FTP는 해외 IP·자격증명 문제로 실패했으므로, **내 브라우저(한국 IP + 내 cPanel 세션)** 로 직접 올린다.

## 배포 소스 (repo 기준)
로컬 clone 경로: `website 확장 수집/templates/gangara-hub/`
또는 zip: `tools/gangara-hub-deploy.zip` (없으면 gangara-hub 폴더 전체 zip 생성)

포함 파일 (18개):
- index.html
- gangnam-garaoke.html, gangnam-hyperbolic.html, gangnam-poolsalon.html, gangnam-jjom.html
- robots.txt, sitemap.xml
- assets/site.css
- assets/benchmark/*.jpg (10장)

## 업로드 대상
호스팅코리아 cPanel → **public_html/** (또는 gangara.co.kr Document Root)

## 현재 live 문제 (교체 이유)
- H1: `강남 가라오케 01025949736` (전화번호 — SEO 불리)
- canonical: `https://gangara.netlify.app/` (co.kr 아님)
- fusion 5페이지·FAQ Schema·벤치마크 이미지 미반영

## 배포 후 기대값
- H1: `강남 가라오케 · 하이퍼블릭 · 풀싸롱 · 쩜오 2026 완벽 가이드`
- canonical: `https://gangara.co.kr/`
- sitemap 5 URL (/, gangnam-garaoke, hyperbolic, poolsalon, jjom)
- robots.txt: `Sitemap: https://gangara.co.kr/sitemap.xml`

---

## 브라우저 작업 순서 (직접 실행)

1. **cPanel 접속**
   - URL: https://gangara.co.kr:2083/
   - 로그인 필요하면 내가 직접 입력 (비밀번호는 채팅에 적지 말 것)

2. **File Manager 열기**
   - Jupiter 테마: "파일 관리자" / "File Manager"
   - `public_html` 폴더로 이동

3. **기존 파일 정리** (백업 후 삭제 또는 덮어쓰기)
   - 삭제/교체 대상: `index.html`, `style.css`, `hero.png`, `choice.png`, `intro.png`, `label.png` 등 구버전
   - `robots.txt`, `sitemap.xml` → fusion 버전으로 교체
   - netlify canonical 들어간 구 index 덮어쓰기

4. **fusion 업로드** (둘 중 하나)
   - **방법 1 (zip)**: `gangara-hub-deploy.zip` 업로드 → public_html에서 Extract(압축 풀기)
   - **방법 2 (폴더)**: gangara-hub 안의 파일·폴더를 public_html에 그대로 업로드
     - `assets/` 폴더 구조 유지 (assets/site.css, assets/benchmark/*.jpg)

5. **권한 확인**
   - HTML/CSS/이미지: 644
   - 폴더: 755

6. **live 검증** (새 탭)
   - https://gangara.co.kr/ 열기 → H1·canonical 확인
   - https://gangara.co.kr/gangnam-garaoke.html
   - https://gangara.co.kr/sitemap.xml → URL 5개
   - https://gangara.co.kr/robots.txt → co.kr sitemap
   - 이미지 하나 로드 확인: https://gangara.co.kr/assets/benchmark/hero-main.jpg

7. **완료 보고** (아래 형식으로)
   - 배포 방법: cPanel File Manager / zip extract
   - index H1 텍스트 (실측)
   - canonical href (실측)
   - sitemap URL 개수
   - 이미지 로드 OK/FAIL
   - 실패 시 스크린샷 + 어느 단계에서 막혔는지

## 주의
- FTP CLI·터미널 배포 시도하지 말 것 (이 작업은 Browser만)
- Netlify만 올리면 co.kr DNS가 호스팅코리아(Apache)라 **co.kr은 안 바뀜** → 반드시 cPanel public_html
- 비밀번호·FTP 계정을 채팅/커밋에 남기지 말 것
- Track A(board-post-automation) 수정 금지

## 막히면
- public_html 경로가 다르면 cPanel "도메인" / "Addon Domains"에서 Document Root 확인
- zip Extract 메뉴: File Manager 상단 "Extract" 또는 우클릭
- 캐시: 시크릿 창 또는 Ctrl+Shift+R 로 재확인
```

---

## 프롬프트 B — 짧은 버전 (이미 cPanel 로그인됨)

```
gangara.co.kr fusion 배포해줘.

1. https://gangara.co.kr:2083/ → File Manager → public_html
2. repo `website 확장 수집/templates/gangara-hub/` 내용 전부 업로드 (또는 tools/gangara-hub-deploy.zip 업로드 후 Extract)
3. 구 index.html(style.css, hero.png 등) 덮어쓰기
4. https://gangara.co.kr/ 검증:
   - H1 = "강남 가라오케 · 하이퍼블릭 · 풀싸롱 · 쩜오 2026 완벽 가이드"
   - canonical = https://gangara.co.kr/
   - sitemap 5 URL
5. 결과 보고 (H1, canonical, sitemap, 이미지 로드 여부)
Netlify 말고 cPanel public_html만. 비번 채팅에 쓰지 마.
```

---

## 프롬프트 C — Netlify만 (참고, co.kr은 안 바뀜)

co.kr은 호스팅코리아 Apache라 **Netlify 배포만으로는 gangara.co.kr이 안 바뀜**.  
netlify.app 동기화용일 때만 사용.

```
Netlify gangara 사이트에 fusion 배포 (co.kr 아님, netlify.app만).

1. https://app.netlify.com/ 로그인 (Google)
2. Projects → gangara → Deploys
3. "Deploy manually" 또는 drag-drop으로 `tools/gangara-hub-deploy.zip` 업로드
4. https://gangara.netlify.app/ H1·페이지 5개 확인
5. co.kr은 cPanel public_html 별도 배포 필요함을 보고
```

---

## zip 로컬 생성 (Browser 전에 한 번)

repo 루트에서:

```bash
cd "website 확장 수집/templates/gangara-hub"
zip -r ../../../tools/gangara-hub-deploy.zip .
```

또는 Python:

```bash
python3 -c "
import zipfile
from pathlib import Path
src=Path('website 확장 수집/templates/gangara-hub')
out=Path('tools/gangara-hub-deploy.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for f in src.rglob('*'):
        if f.is_file(): z.write(f, f.relative_to(src))
print(out, out.stat().st_size)
"
```

---

## 프롬프트 D — 계정 포함 (로컬 전용, Git 미커밋)

계정·비번까지 Agent가 입력하게 하려면:

- 로컬 파일: `tools/CURSOR_BROWSER_DEPLOY_PROMPT.private.md` (`.gitignore` 처리됨)
- **GitHub에는 올라가지 않음** — clone 후 로컬에서만 사용

---

## 배포 소스 확인 (GitHub repo = 맞음)

| 항목 | 값 |
|------|-----|
| repo | `qordjr2037-ctrl/website-expansion-automation` |
| 브랜치 | `cursor/gangara-faeb` |
| 소스 폴더 | `website 확장 수집/templates/gangara-hub/` |
| 파일 수 | **18개** (HTML 5 + robots + sitemap + CSS 1 + JPG 10) |
| zip | `tools/gangara-hub-deploy.zip` (로컬 생성 가능) |
| 업로드 대상 | cPanel `public_html/` |

---

## Cursor Browser 사용 팁

1. Cursor에서 **Browser** 기능 켜기 → Chrome/Edge가 Agent에 연결됨
2. **프롬프트 D** (계정 포함) 또는 **프롬프트 A** 붙여넣기
3. Agent가 cPanel 로그인 → File Manager → 업로드 → live 검증
4. 2FA/캡cha 뜨면 내가 직접 처리 후 "계속" 입력
5. cPanel 직접 로그인 invalid 시 → hosting.kr → cPanel 바로가기
