#!/usr/bin/env bash

bash 1_find_overlaps.sh
python 2_generate_manifest.py
python make_prepare_commands.py | shuf | parallel -j 40
python 3_make_commands_opt.py | shuf | parallel -j 40
python 5_combine_results.py
python 6_process_results.py