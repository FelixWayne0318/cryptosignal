#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# ===== 配置 =====
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
# 单分片大小（MiB）；Telegram 直传有体积限制，建议保守一些
PART_MB="${PART_MB:-45}"
# 默认打包输出目录
OUTDIR="${OUTDIR:-data/exports}"

# ===== 工具函数 =====
die() { echo "❌ $*" >&2; exit 1; }
log() { echo "[$(date +'%F %T')] $*"; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "缺少依赖：$1"
}

check_env() {
  [[ -n "$BOT_TOKEN" ]] || die "未设置 TELEGRAM_BOT_TOKEN"
  [[ -n "$CHAT_ID"  ]] || die "未设置 TELEGRAM_CHAT_ID"
}

# 发送纯文本消息（可用于连通性测试）
send_text() {
  local text="$1"
  curl -fsS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${text}" >/dev/null
}

# 发送单个文件（<= 限制时）
send_document() {
  local file="$1" caption="${2:-}"
  curl -fsS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
    -F "chat_id=${CHAT_ID}" \
    -F "document=@${file}" \
    -F "caption=${caption}" >/dev/null
}

# 超限则分片发送
send_large_file() {
  local file="$1" base caption
  base="$(basename "$file")"
  caption="${2:-$base}"

  local size_bytes partsz_bytes
  size_bytes=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file")
  partsz_bytes=$(( PART_MB * 1024 * 1024 ))

  if (( size_bytes <= partsz_bytes )); then
    log "文件未超限，直接发送：$base ($(numfmt --to=iec $size_bytes 2>/dev/null || echo ${size_bytes}B))"
    send_document "$file" "$caption"
    return
  fi

  log "文件较大，开始分片（每片 ${PART_MB}MiB）：$base"
  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT

  # split -d 生成数字后缀，便于排序
  split -b "${PART_MB}m" -d --additional-suffix ".part" "$file" "$tmpdir/${base}."
  local i=1
  for part in $(ls "$tmpdir" | sort); do
    local p="$tmpdir/$part"
    log "发送分片 $i：$part"
    send_document "$p" "${caption} (part ${i})"
    i=$((i+1))
  done
}

# 打包仓库（默认行为）：排除 .git
package_repo() {
  local repo="$1" out="$2"
  mkdir -p "$(dirname "$out")"
  # 你也可以在这里按需排除其它目录（例如 data/run_*）
  tar --exclude='.git' -czf "$out" -C "$repo" .
}

# ===== 主流程 =====
main() {
  need curl
  need tar
  need split
  check_env

  local REPO ROOT
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  REPO="$ROOT"

  mkdir -p "$OUTDIR"

  if (( $# == 0 )); then
    # 默认：打包整个仓库并发送
    local stamp fname fpath
    stamp="$(date +'%Y%m%d-%H%M%S')"
    fname="ats-analyzer_${stamp}.tgz"
    fpath="${OUTDIR}/${fname}"

    log "开始打包仓库 -> $fpath"
    package_repo "$REPO" "$fpath"
    log "打包完成"

    send_large_file "$fpath" "Repo package: ${fname}"
    log "✅ 发送完成：$fname"
  else
    # 发送指定文件/目录
    local path="$1"
    [[ -e "$path" ]] || die "路径不存在：$path"

    if [[ -d "$path" ]]; then
      local stamp fname fpath
      stamp="$(date +'%Y%m%d-%H%M%S')"
      fname="$(basename "$path")_${stamp}.tgz"
      fpath="${OUTDIR}/${fname}"
      log "打包目录 $path -> $fpath"
      tar -czf "$fpath" -C "$(dirname "$path")" "$(basename "$path")"
      send_large_file "$fpath" "Archive: ${fname}"
      log "✅ 发送完成：$fname"
    else
      # 单文件
      send_large_file "$path" "File: $(basename "$path")"
      log "✅ 发送完成：$(basename "$path")"
    fi
  fi
}

main "$@"