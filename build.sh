#!/usr/bin/env bash
set -Eeuo pipefail

SUPPORTED_VERSION="1.6.0"
GUACAMOLE_VERSION="${GUACAMOLE_VERSION:-${SUPPORTED_VERSION}}"
IMAGE_NAME="${IMAGE_NAME:-ghcr.io/trilogys/guacamole_patch:${GUACAMOLE_VERSION}-recovery4}"
MAVEN_ARGUMENTS="${MAVEN_ARGUMENTS:--DskipTests=false}"
PULL_BASE_IMAGES="${PULL_BASE_IMAGES:-false}"
KEEP_WORK_DIR="${KEEP_WORK_DIR:-false}"
WORK_PARENT="${WORK_DIR:-${TMPDIR:-/tmp}}"
SOURCE_SHA256="81f9fd5a7b4377fb0ee295d0d4fec92e9667f2aafaa3d0ed8937f535deabdee4"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PATCH_FILE="${SCRIPT_DIR}/patches/0001-fix-ime-and-keyboard-after-tab-switch.patch"

if [[ "${GUACAMOLE_VERSION}" != "${SUPPORTED_VERSION}" ]]; then
    printf '此补丁只支持 Apache Guacamole %s，当前请求：%s\n' \
        "${SUPPORTED_VERSION}" "${GUACAMOLE_VERSION}" >&2
    exit 1
fi

for command in curl sha256sum tar patch docker python3 mktemp; do
    if ! command -v "${command}" >/dev/null 2>&1; then
        printf '缺少命令：%s\n' "${command}" >&2
        exit 1
    fi
done

[[ -f "${PATCH_FILE}" ]] || {
    printf '找不到补丁：%s\n' "${PATCH_FILE}" >&2
    exit 1
}

# Verify that the extracted package has not been accidentally modified.
(
    cd -- "${SCRIPT_DIR}"
    sha256sum --check --status SHA256SUMS
) || {
    printf '补丁包内部 SHA-256 校验失败，停止构建。\n' >&2
    exit 1
}

mkdir -p -- "${WORK_PARENT}"
BUILD_WORK_DIR="$(mktemp -d "${WORK_PARENT%/}/guacamole-ime-fix.XXXXXX")"
ARCHIVE="${BUILD_WORK_DIR}/guacamole-client-${GUACAMOLE_VERSION}.tar.gz"
SOURCE_DIR="${BUILD_WORK_DIR}/guacamole-client-${GUACAMOLE_VERSION}"
PATCH_SHA256="$(sha256sum "${PATCH_FILE}" | awk '{print $1}')"

cleanup() {
    if [[ "${KEEP_WORK_DIR}" == "true" ]]; then
        printf '保留构建目录：%s\n' "${BUILD_WORK_DIR}"
    else
        rm -rf -- "${BUILD_WORK_DIR}"
    fi
}
trap cleanup EXIT

python3 "${SCRIPT_DIR}/tests/verify_patch_package.py" "${SCRIPT_DIR}"
python3 "${SCRIPT_DIR}/tests/state_regression.py"
python3 "${SCRIPT_DIR}/tests/reconstruct_and_apply_patch.py" "${PATCH_FILE}"

PRIMARY_URL="https://downloads.apache.org/guacamole/${GUACAMOLE_VERSION}/source/guacamole-client-${GUACAMOLE_VERSION}.tar.gz"
ARCHIVE_URL="https://archive.apache.org/dist/guacamole/${GUACAMOLE_VERSION}/source/guacamole-client-${GUACAMOLE_VERSION}.tar.gz"
CURL_ARGS=(
    --fail
    --location
    --proto '=https'
    --tlsv1.2
    --retry 3
    --retry-delay 2
    --retry-all-errors
    --output "${ARCHIVE}"
)

printf '下载 Apache Guacamole %s 源码……\n' "${GUACAMOLE_VERSION}"
if ! curl "${CURL_ARGS[@]}" "${PRIMARY_URL}"; then
    printf '主下载站失败，改用 Apache Archive……\n'
    curl "${CURL_ARGS[@]}" "${ARCHIVE_URL}"
fi

printf '%s  %s\n' "${SOURCE_SHA256}" "${ARCHIVE}" | sha256sum --check --status || {
    printf '官方源码 SHA-256 校验失败，停止构建。\n' >&2
    exit 1
}

tar --extract --gzip --no-same-owner --no-same-permissions \
    --file "${ARCHIVE}" --directory "${BUILD_WORK_DIR}"
[[ -d "${SOURCE_DIR}" ]] || {
    printf '源码目录不存在：%s\n' "${SOURCE_DIR}" >&2
    exit 1
}

printf '先进行补丁 dry-run……\n'
patch --directory="${SOURCE_DIR}" --strip=1 --dry-run < "${PATCH_FILE}"
printf '应用输入法补丁……\n'
patch --directory="${SOURCE_DIR}" --strip=1 --forward < "${PATCH_FILE}"

python3 "${SCRIPT_DIR}/tests/verify_patched_source.py" "${SOURCE_DIR}"

# The official Docker build runs the frontend build and Maven test suite. When a
# local Node.js is available, also fail early on syntax errors in changed files.
if command -v node >/dev/null 2>&1; then
    node --check "${SOURCE_DIR}/guacamole/src/main/frontend/src/app/textInput/directives/guacTextInput.js"
    node --check "${SOURCE_DIR}/guacamole/src/main/frontend/src/app/client/controllers/clientController.js"
    node --check "${SOURCE_DIR}/guacamole/src/main/frontend/src/app/client/directives/guacClient.js"
    node --check "${SOURCE_DIR}/guacamole/src/main/frontend/src/app/client/directives/guacTiledClients.js"
    node --check "${SOURCE_DIR}/guacamole/src/main/frontend/src/app/client/types/ManagedClient.js"
    node --check "${SOURCE_DIR}/guacamole/src/main/frontend/src/app/index/controllers/indexController.js"
fi

DOCKER_BUILD_ARGS=(
    --build-arg "MAVEN_ARGUMENTS=${MAVEN_ARGUMENTS}"
    --label "org.opencontainers.image.title=Apache Guacamole with input and network recovery"
    --label "org.opencontainers.image.version=${GUACAMOLE_VERSION}-recovery4"
    --label "org.opencontainers.image.source=https://github.com/apache/guacamole-client"
    --label "org.opencontainers.image.licenses=Apache-2.0"
    --label "io.guacamole.recovery.patch-sha256=${PATCH_SHA256}"
    --tag "${IMAGE_NAME}"
)
if [[ "${PULL_BASE_IMAGES}" == "true" ]]; then
    DOCKER_BUILD_ARGS+=(--pull)
fi

printf '构建镜像 %s（Maven 参数：%s）……\n' "${IMAGE_NAME}" "${MAVEN_ARGUMENTS}"
docker build "${DOCKER_BUILD_ARGS[@]}" "${SOURCE_DIR}"

docker image inspect "${IMAGE_NAME}" >/dev/null
printf '执行镜像内 initdb 冒烟测试……\n'
docker run --rm --entrypoint /opt/guacamole/bin/initdb.sh \
    "${IMAGE_NAME}" --postgresql >/dev/null

IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${IMAGE_NAME}")"
printf '\n构建完成：%s\n' "${IMAGE_NAME}"
printf '镜像 ID：%s\n' "${IMAGE_ID}"
printf '补丁 SHA-256：%s\n' "${PATCH_SHA256}"
printf '接下来运行：docker compose up -d --force-recreate guacamole\n'
