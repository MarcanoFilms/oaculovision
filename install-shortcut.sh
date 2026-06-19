#!/usr/bin/env bash
# Instala el comando global 'oraculovision' en ~/.local/bin
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
SCRIPT="${BIN_DIR}/oraculovision"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "${BIN_DIR}"

cat > "${SCRIPT}" << EOF
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${PROJECT_DIR}"
VENV_PYTHON="\${PROJECT_DIR}/.venv/bin/python"
MAIN="\${PROJECT_DIR}/main.py"

if [[ ! -f "\${VENV_PYTHON}" ]]; then
    echo "oraculovision: entorno virtual no encontrado." >&2
    echo "  cd \${PROJECT_DIR} && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi

cd "\${PROJECT_DIR}"
exec "\${VENV_PYTHON}" "\${MAIN}" "\$@"
EOF

chmod +x "${SCRIPT}"
echo "Instalado: ${SCRIPT}"
echo "Usa: oraculovision"