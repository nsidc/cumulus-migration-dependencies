set -e

source env.sh

./script.py -o README.md

git config --global user.name 'GitHub Actions'
git config --global user.email 'actions@users.noreply.github.com'

git add README.md
(git commit -m 'CI Update' && git push origin) || echo "Found no changes to dependencies."
