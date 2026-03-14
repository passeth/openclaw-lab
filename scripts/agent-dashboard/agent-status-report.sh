#!/bin/bash

# =============================================
# EVAS Agent Status Reporter (Improved)
# 5분마다 게이트웨이 상태 체크 및 Supabase 업데이트
# =============================================

set -euo pipefail

# ============ CONFIG ============
SUPABASE_URL="https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

AGENT_ID="${AGENT_ID:-obsi}"
HOST_NAME="${HOST_NAME:-1맥 Mac mini}"

LOG_FILE="/tmp/agent-status-report-${AGENT_ID}.log"
OPENCLAW_LOG="${HOME}/.openclaw/logs/gateway.log"

# ============ LOGGING ============
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$AGENT_ID] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$AGENT_ID] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# ============ METRICS ============

# 1. CPU 사용률 (macOS: top -l 1)
get_cpu_usage() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: user + system percentage
        local cpu
        cpu=$(top -l 1 -n 0 2>/dev/null | grep "CPU usage" | awk '{print $3}' | tr -d '%')
        echo "${cpu:-0}"
    else
        # Linux fallback
        local cpu
        cpu=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $2}' | tr -d '%us,')
        echo "${cpu:-0}"
    fi
}

# 2. 메모리 사용량 MB (ps로 openclaw 프로세스)
get_memory_usage() {
    if command -v ps >/dev/null 2>&1; then
        # openclaw 관련 프로세스의 RSS 메모리 합계 (MB)
        local mem_mb
        mem_mb=$(ps aux 2>/dev/null | grep -E "(openclaw|gateway)" | grep -v grep | awk '{sum += $6} END {print int(sum/1024)}')
        echo "${mem_mb:-0}"
    else
        echo "0"
    fi
}

# 3. 디스크 여유 공간 GB
get_disk_free() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: GB 단위 정수
        local disk
        disk=$(df -g / 2>/dev/null | awk 'NR==2 {print $4}')
        echo "${disk:-0}"
    else
        # Linux
        local disk
        disk=$(df -BG / 2>/dev/null | awk 'NR==2 {gsub(/G/, "", $4); print $4}')
        echo "${disk:-0}"
    fi
}

# 4. 활성 세션 수 (openclaw status에서 파싱)
get_active_sessions() {
    if command -v openclaw >/dev/null 2>&1; then
        local sessions
        sessions=$(openclaw status 2>/dev/null | grep -E "^\│ Sessions" | grep -oE "[0-9]+ active" | grep -oE "[0-9]+")
        echo "${sessions:-0}"
    else
        echo "0"
    fi
}

# 5. 활성 크론 수 (openclaw cron list에서 파싱)
get_active_crons() {
    if command -v openclaw >/dev/null 2>&1; then
        # ID로 시작하는 데이터 행 개수 count (헤더 제외)
        local crons
        crons=$(openclaw cron list 2>/dev/null | awk '/^[a-f0-9]/ {count++} END {print count+0}')
        echo "${crons:-0}"
    else
        echo "0"
    fi
}

# 6. 마지막 활동 (최근 로그에서)
get_last_activity() {
    if [[ -f "$OPENCLAW_LOG" ]]; then
        # 마지막 로그 라인의 타임스탬프 파싱
        local last_time
        last_time=$(tail -1 "$OPENCLAW_LOG" 2>/dev/null | grep -oE "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}" | head -1)
        if [[ -n "$last_time" ]]; then
            # ISO8601 UTC로 변환
            date -u -j -f "%Y-%m-%dT%H:%M:%S" "${last_time%+:*}" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "$last_time"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# 7. gateway_version (가능하면)
get_gateway_version() {
    # gateway 로그 첫 줄에서 버전 확인 시도
    if [[ -f "$OPENCLAW_LOG" ]]; then
        local version
        version=$(head -100 "$OPENCLAW_LOG" 2>/dev/null | grep -oE "gateway[ -]v?[0-9]+\.[0-9]+\.[0-9]+" | head -1 | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")
        if [[ -n "$version" ]]; then
            echo "v$version"
            return
        fi
    fi
    # 없으면 빈 문자열
    echo ""
}

# 8. openclaw_version
get_openclaw_version() {
    if command -v openclaw >/dev/null 2>&1; then
        local version
        version=$(openclaw --version 2>/dev/null | grep -oE "OpenClaw [0-9]+\.[0-9]+\.[0-9]+" | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")
        echo "${version:-}"
    else
        echo ""
    fi
}

# 게이트웨이 상태 (Gateway service 행에서 파싱)
get_gateway_status() {
    if command -v openclaw >/dev/null 2>&1; then
        local status
        status=$(openclaw status 2>/dev/null | grep -E "^│ Gateway service" | grep -oE "running|stopped|loaded" | head -1)
        case "$status" in
            running|loaded) echo "running" ;;
            stopped) echo "stopped" ;;
            *) echo "down" ;;
        esac
    else
        echo "down"
    fi
}

# ============ SUPABASE UPDATE (PATCH) ============
update_agent_status() {
    local gateway_status="$1"
    local cpu_percent="$2"
    local memory_mb="$3"
    local disk_free_gb="$4"
    local active_sessions="$5"
    local active_crons="$6"
    local last_activity="$7"
    local gateway_version="$8"
    local openclaw_version="$9"
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # 숫자 기본값 처리
    cpu_percent="${cpu_percent:-0}"
    memory_mb="${memory_mb:-0}"
    disk_free_gb="${disk_free_gb:-0}"
    active_sessions="${active_sessions:-0}"
    active_crons="${active_crons:-0}"

    # JSON 데이터 생성 (gateway_version, openclaw_version은 null 허용)
    local json_data
    if [[ -n "$gateway_version" ]]; then
        json_data=$(cat <<EOF
{
    "agent_id": "$AGENT_ID",
    "host": "$HOST_NAME",
    "status": "$gateway_status",
    "last_heartbeat": "$timestamp",
    "cpu_percent": $cpu_percent,
    "memory_mb": $memory_mb,
    "disk_free_gb": $disk_free_gb,
    "active_sessions": $active_sessions,
    "active_crons": $active_crons,
    "last_activity": "${last_activity:-null}",
    "gateway_version": "$gateway_version",
    "openclaw_version": "$openclaw_version",
    "updated_at": "$timestamp"
}
EOF
)
    else
        json_data=$(cat <<EOF
{
    "agent_id": "$AGENT_ID",
    "host": "$HOST_NAME",
    "status": "$gateway_status",
    "last_heartbeat": "$timestamp",
    "cpu_percent": $cpu_percent,
    "memory_mb": $memory_mb,
    "disk_free_gb": $disk_free_gb,
    "active_sessions": $active_sessions,
    "active_crons": $active_crons,
    "last_activity": "${last_activity:-null}",
    "openclaw_version": "$openclaw_version",
    "updated_at": "$timestamp"
}
EOF
)
    fi

    # PATCH 요청으로 agent_id로 필터링하여 업데이트
    local response
    response=$(curl -s -w "\n%{http_code}" -X PATCH "$SUPABASE_URL/rest/v1/agent_status?agent_id=eq.$AGENT_ID" \
        -H "apikey: $SUPABASE_SERVICE_KEY" \
        -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
        -H "Content-Type: application/json" \
        -H "Prefer: return=minimal" \
        -d "$json_data" 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" || "$http_code" == "204" ]]; then
        log "✅ Status updated: sessions=$active_sessions, crons=$active_crons, mem=${memory_mb}MB, cpu=${cpu_percent}%, disk=${disk_free_gb}GB"
        return 0
    else
        log_error "Failed (HTTP $http_code): $body"
        return 1
    fi
}

# ============ MAIN ============
main() {
    log "Starting status report..."

    # 모든 메트릭 수집 (병렬로 실행 가능한部分是 순차적)
    local gateway_status cpu_percent memory_mb disk_free_gb active_sessions active_crons last_activity gateway_version openclaw_version

    gateway_status=$(get_gateway_status)
    cpu_percent=$(get_cpu_usage)
    memory_mb=$(get_memory_usage)
    disk_free_gb=$(get_disk_free)
    active_sessions=$(get_active_sessions)
    active_crons=$(get_active_crons)
    last_activity=$(get_last_activity)
    gateway_version=$(get_gateway_version)
    openclaw_version=$(get_openclaw_version)

    # 디버그 로그
    log "Metrics: gateway=$gateway_status, cpu=${cpu_percent}%, mem=${memory_mb}MB, disk=${disk_free_gb}GB, sessions=$active_sessions, crons=$active_crons, last_activity=$last_activity, gateway_ver=$gateway_version, openclaw_ver=$openclaw_version"

    # Supabase 업데이트
    if ! update_agent_status "$gateway_status" "$cpu_percent" "$memory_mb" "$disk_free_gb" "$active_sessions" "$active_crons" "$last_activity" "$gateway_version" "$openclaw_version"; then
        # 업데이트 실패 시에도 계속 진행 (cron은 계속 실행)
        log_error "Supabase update failed, continuing..."
    fi

    log "Status report completed"
}

# 에러 트랩
trap 'log_error "Script failed on line $LINENO"' ERR

# 실행
main "$@"
