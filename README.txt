웹사이트 확장 자동화 (Track B)
================================

게시판 자동화(board-post-automation)와 완전히 별도 저장소입니다.

  · 키워드별 백링크 placement 수집 → backlink_targets_sync push
  · PC N대: pull → 배포 (post_only)
  · Cursor Automation: core/AUTOMATION_INSTRUCTIONS.txt

시작:
  1) Automation Agent Instruction 에 AUTOMATION_INSTRUCTIONS.txt 내용 붙여넣기
  2) Run → Phase 0~1 부터 순차 구축
  3) 상태: core/backlink_deploy_status.json

board-post-automation 과 코드·설정 공유하지 않습니다.
