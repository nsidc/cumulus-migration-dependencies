#!/bin/bash

source env.sh

failures=0

function check() {
    echo $1
    $1 && echo "Success!" || ((failures++))
    echo -e "\n"
}

# use -a flag to autocorrect
if [ "${1}" = "-a" ]; then
    commands=(
        "safety check"
        "black ."
        "isort ."
        "flake8"
        "mypy"
    )
else
    commands=(
        "safety check"
        "black --check ."
        "isort --check-only ."
        "flake8"
        "mypy"
    )
fi

for COMMAND in "${commands[@]}"; do
    check "${COMMAND}"
done

# exit code is equal to number of failures
echo -e "lint.sh failures: $failures"
exit $failures
