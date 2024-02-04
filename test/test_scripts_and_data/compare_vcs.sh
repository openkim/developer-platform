sed -rn 's/Grade: (.*)/\1/p'  ~/verification-results/*/report.txt > /home/openkim/tmp.grades

diffresult=$(diff /home/openkim/tmp.grades $1.grades 2>&1)

if [[ $diffresult != "" ]]; then
    echo "following differences found between test and reference VCs:"
    echo $diffresult
    exit 1
fi
echo "All grades match"