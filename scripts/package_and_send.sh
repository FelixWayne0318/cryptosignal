#!/usr/bin/env bash
set -euo pipefail

# 仓库根目录（兼容从任意目录调用）
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$REPO"

# 输出目录
OUT="${REPO}/data/packages"
mkdir -p "$OUT"

TS="$(date +%F_%H%M%S)"
GIT_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo 'no-git')"

SRC_TGZ="${OUT}/src_${TS}_${GIT_SHORT}.tar.gz"
BUNDLE="${OUT}/repo_${TS}_${GIT_SHORT}.bundle"
SHA_FILE="${OUT}/SHA256SUMS_${TS}_${GIT_SHORT}.txt"

# 仅源码打包（排除 .git / 缓存）
echo "• 打包源码 → ${SRC_TGZ}"
tar \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  -czf "${SRC_TGZ}" \
  -C "${REPO}" .

# 打完整历史的 git bundle（若不是 git 仓库会跳过）
if git rev-parse --git-dir >/dev/null 2>&1; then
  echo "• 制作 git bundle → ${BUNDLE}"
  git bundle create "${BUNDLE}" --all
else
  echo "⚠️ 当前不是 git 仓库，跳过 bundle。"
  BUNDLE=""
fi

# 生成校验和
echo "• 生成 SHA256 校验"
{
  [ -f "${SRC_TGZ}" ] && sha256sum "${SRC_TGZ}"
  [ -n "${BUNDLE}" ] && [ -f "${BUNDLE}" ] && sha256sum "${BUNDLE}"
} > "${SHA_FILE}"

# 发送文件到 Telegram，超过 1.9GB 自动分片
send_with_split() {
  local file="$1"
  local caption="$2"
  local max=$((1900*1024*1024))  # 1.9GB，低于 Telegram 2GB 上限

  [ -f "$file" ] || return 0

  local size
  size=$(wc -c <"$file")

  if [ "$size" -le "$max" ]; then
    bash "${REPO}/scripts/send_tg.sh" "$file" "$caption"
  else
    echo "• 文件较大，分片上传: $file"
    local prefix="${file}.part."
    rm -f ${prefix}* 2>/dev/null || true
    split -b 1900m -d -a 2 "$file" "${prefix}"

    # 统计片数
    shopt -s nullglob
    parts=( ${prefix}* )
    local total="${#parts[@]}"
    local idx=1
    for p in "${parts[@]}"; do
      bash "${REPO}/scripts/send_tg.sh" "$p" "${caption} (part ${idx}/${total})"
      idx=$((idx+1))
    done
  fi
}

CAPTION_BASE="ats-analyzer ${TS} (${GIT_SHORT})"

send_with_split "${SRC_TGZ}" "SRC tarball · ${CAPTION_BASE}"
[ -n "${BUNDLE}" ] && [ -f "${BUNDLE}" ] && send_with_split "${BUNDLE}" "GIT bundle · ${CAPTION_BASE}"
bash "${REPO}/scripts/send_tg.sh" "${SHA_FILE}" "SHA256SUMS · ${CAPTION_BASE}"

echo "✅ 全部完成"
echo "  • ${SRC_TGZ}"
[ -n "${BUNDLE}" ] && [ -f "${BUNDLE}" ] && echo "  • ${BUNDLE}"
echo "  • ${SHA_FILE}"