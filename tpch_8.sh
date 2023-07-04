#!/bin/bash

queries=("Q1" "Q2" "Q3" "Q4" "Q5" "Q6" "Q7")

# queries=("Q6")

file_prefix="tpch_8_0*10"
file_path="/local/scratch/zhang/cavier/FIVM/examples/queries/tpch_8_0/"

redirect="$1"  # Get the value of the first input parameter

for query in "${queries[@]}"
do
    command_sql="python3 generate_FIVM.py ${file_prefix} ${query} tpch_unordered1 sql ${redirect}"
    command_txt="python3 generate_FIVM.py ${file_prefix} ${query} tpch_unordered1 vo ${redirect}"
    file_name="${file_prefix}-${query}"

    if [[ "$redirect" == "true" ]]; then
        mkdir -p ${file_path}
        ${command_sql} > "${file_path}${file_name}.sql"    # Use tee for output, redirecting to file and displaying on the command line
        ${command_txt} > "${file_path}${file_name}.txt"    # Use tee for output, redirecting to file and displaying on the command line
    else
        ${command_sql} 
        ${command_txt}
    fi

done

if [[ "$redirect" == "true" ]]; then
    cd /local/scratch/zhang/cavier/FIVM/examples
    make DATASET=tpch_8_0
fi

