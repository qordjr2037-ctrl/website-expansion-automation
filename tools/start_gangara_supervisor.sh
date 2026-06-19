#!/bin/bash
# gangara supervisor — tmux 없어도 nohup으로 재기동
set -e
cd "$(dirname "$0")/.."
mkdir -p tools
if [ -f tools/GANGARA_SUPERVISOR_STOP ]; then
  rm -f tools/GANGARA_SUPERVISOR_STOP
fi
# 기존 supervisor 종료
pkill -f "run_gangara_supervisor.py" 2>/dev/null || true
sleep 1
nohup python3 core/run_gangara_supervisor.py --daemon >> tools/gangara_supervisor.log 2>&1 &
echo "supervisor pid=$!"
disown || true
