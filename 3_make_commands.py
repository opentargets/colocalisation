#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ed Mountjoy
#
# Reads the manifest file and makes commands
#

import os
import sys
import json
import argparse
import gzip

def main():

    # Args
    args = parse_args()
    in_manifest = 'configs/manifest.json.gz'
    out_todo = 'commands_todo.txt.gz'
    out_done = 'commands_done.txt.gz'

    # Pipeline args
    script = 'scripts/coloc_wrapper.py'
    r_script = 'scripts/coloc.R'
    top_loci_file = '/home/js29/genetics-colocalisation/data/finemapping/top_loci_by_chrom/CHROM.json'
    window_colc = 500 # in KB
    window_cond = 1000  # in KB
    min_maf = 0.01
    make_plots = False

    # Open command files
    todo_h = gzip.open(out_todo, 'w')
    done_h = gzip.open(out_done, 'w')
    
    # Iterate over manifest
    with gzip.open(in_manifest, 'r') as in_mani:
        for line in in_mani:

            # Parse
            rec = json.loads(line.decode().rstrip())
            # pprint(rec)

            # Build command
            cmd = [
                'python',
                os.path.abspath(script),
                '--left_sumstat', os.path.abspath(rec['left_sumstats']),
                '--left_ld', os.path.abspath(rec['left_ld']),
                '--left_type', rec['left_type'],
                '--left_study', rec['left_study_id'],
                '--left_phenotype', rec['left_phenotype_id'],
                '--left_bio_feature', rec['left_bio_feature'],
                '--left_chrom', rec['left_lead_chrom'],
                '--left_pos', rec['left_lead_pos'],
                '--left_ref', rec['left_lead_ref'],
                '--left_alt', rec['left_lead_alt'],
                '--right_sumstat', os.path.abspath(rec['right_sumstats']),
                '--right_ld', os.path.abspath(rec['right_ld']),
                '--right_type', rec['right_type'],
                '--right_study', rec['right_study_id'],
                '--right_phenotype', rec['right_phenotype_id'],
                '--right_bio_feature', rec['right_bio_feature'],
                '--right_chrom', rec['right_lead_chrom'],
                '--right_pos', rec['right_lead_pos'],
                '--right_ref', rec['right_lead_ref'],
                '--right_alt', rec['right_lead_alt'],
                '--r_coloc_script', os.path.abspath(r_script),
                '--method', rec['method'],
                '--top_loci', os.path.abspath(top_loci_file),
                '--window_coloc', window_colc,
                '--window_cond', window_cond,
                '--min_maf', min_maf,
                '--out', os.path.abspath(rec['out']),
                '--log', os.path.abspath(rec['log']),
                '--tmpdir', os.path.abspath(rec['tmpdir']),
                '--delete_tmpdir'
            ]

            if make_plots:
                cmd = cmd + ['--plot', os.path.abspath(rec['plot'])]
            
            cmd_str = ' '.join([str(arg) for arg in cmd])

            # Skip if output exists
            if os.path.exists(rec['out']):
                done_h.write((cmd_str + '\n').encode())
                continue
            else:
                todo_h.write((cmd_str + '\n').encode())
                if not args.quiet:
                    print(cmd_str)
    
    # Close files
    done_h.close()
    todo_h.close()

    return 0

def parse_args():
    ''' Load command line args
    '''
    p = argparse.ArgumentParser()

    # Add input files
    p.add_argument('--quiet',
                   help=("Don't print commands to stdout"),
                   action='store_true')

    args = p.parse_args()
    return args

if __name__ == '__main__':

    main()
