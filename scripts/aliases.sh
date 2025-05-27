#!/bin/bash
# GraphAPIQuery 프로젝트 유용한 Alias 모음
# 사용법: source scripts/aliases.sh


# import accounts
alias enrolls="python scripts/enrollment_import.py import --verbose"
alias enroll="python scripts/enrollment_import.py"

# database
alias db="python main.py db"
alias dbret="python main.py db reset"
alias dbinit="python main.py db init"
alias dbaccounts="python main.py db accounts"
alias dbtokens="python main.py db tokens"

# auto auth from data [email]
alias authstart="python main.py auth start-auth-code -e"