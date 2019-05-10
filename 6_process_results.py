#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ed Mountjoy
#
# Combines the outputs from the coloc pipeline into a single file
#

'''
# Set SPARK_HOME and PYTHONPATH to use 2.4.0
export PYSPARK_SUBMIT_ARGS="--driver-memory 8g pyspark-shell"
export SPARK_HOME=/Users/em21/software/spark-2.4.0-bin-hadoop2.7
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-2.4.0-src.zip:$PYTHONPATH
'''

import pyspark.sql
from pyspark.sql.types import *
from pyspark.sql.functions import *
import sys
import os
import gzip
# from shutil import copyfile
# from glob import glob

def main():

    # Make spark session
    spark = (
        pyspark.sql.SparkSession.builder
        .config("spark.master", "local[*]")
        .getOrCreate()
    )
    # sc = spark.sparkContext
    print('Spark version: ', spark.version)

    # File args
    # in_parquet = '/home/ubuntu/results/coloc/results/coloc_raw.parquet'
    # out_json = '/home/ubuntu/results/coloc/results/coloc_processed.json'
    in_parquet = '/Users/em21/Projects/genetics-colocalisation/tmp/coloc_raw_copy.parquet'
    out_json = '/Users/em21/Projects/genetics-colocalisation/tmp/coloc_processed.json'
    in_phenotype_map = '/Users/em21/Projects/ot_genetics/genetics-sumstats_data/ingest/eqtl_db_v1/example_data/HumanHT-12_V4_gene_metadata.txt.gz'

    # Results parameters
    make_symmetric = True # Will make the coloc matrix symmetric
    left_gwas_only = True # Output will only contains rows where left_type == gwas
    deduplicate_right = True # For each left dataset, only keep the "best" right dataset
    min_overlapping_vars = 100 # Only keep results with this many overlapping vars

    # Load
    df = spark.read.parquet(in_parquet)

    # Rename and calc new columns 
    df = (
        df.withColumnRenamed('PP.H0.abf', 'coloc_h0')
        .withColumnRenamed('PP.H1.abf', 'coloc_h1')
        .withColumnRenamed('PP.H2.abf', 'coloc_h2')
        .withColumnRenamed('PP.H3.abf', 'coloc_h3')
        .withColumnRenamed('PP.H4.abf', 'coloc_h4')
        .withColumnRenamed('nsnps', 'coloc_n_vars')
        .withColumn('coloc_h4_h3', (col('coloc_h4') / col('coloc_h3')))
        .withColumn('coloc_log2_h4_h3', log2(col('coloc_h4_h3')))
    )

    # Filter based on the number of snps overlapping the left and right datasets
    if min_overlapping_vars:
        df = df.filter(col('coloc_n_vars') >= min_overlapping_vars)

    # Make symmetric
    if make_symmetric:

        df_rev = df

        # Move all left_ columns to temp_
        for colname in [x for x in df_rev.columns if x.startswith('left_')]:
            df_rev = df_rev.withColumnRenamed(
                colname, colname.replace('left_', 'temp_'))
        
        # Move all right_ columns to left_
        for colname in [x for x in df_rev.columns if x.startswith('right_')]:
            df_rev = df_rev.withColumnRenamed(
                colname, colname.replace('right_', 'left_'))

        # Move all temp_ columns to right_
        for colname in [x for x in df_rev.columns if x.startswith('temp_')]:
            df_rev = df_rev.withColumnRenamed(
                colname, colname.replace('temp_', 'right_'))
        
        # Take union by name between original and flipped dataset
        df = df.withColumn('is_flipped', lit(False))
        df_rev = df_rev.withColumn('is_flipped', lit(True))
        df = df.unionByName(df_rev)
    
    # Keep only rows where left_type == gwas
    if left_gwas_only:
        df = df.filter(col('left_type') == 'gwas')
    
    # Deduplicate right
    # print(df.count())
    if deduplicate_right:

        # Sort by coloc_h4
        df = df.orderBy('coloc_h4', ascending=False)

        # Deduplicate the right dataset
        col_subset = [
            'left_type',
            'left_study',
            'left_phenotype',
            'left_bio_feature',
            'left_chrom',
            'left_pos',
            'left_ref',
            'left_alt',
            'right_type',
            'right_study',
            'right_bio_feature',
            'right_phenotype',
            # 'right_chrom',
            # 'right_pos',
            # 'right_ref',
            # 'right_alt'
        ]
        df = df.dropDuplicates(subset=col_subset)

    # Add gene_id to phenotype_id
    phenotype_map = load_pheno_to_gene_map(in_phenotype_map)
    biofeature_mapper = udf(lambda x: phenotype_map.get(x, x))
    df = (
        df.withColumn('left_gene_id', biofeature_mapper(col('left_phenotype')))
          .withColumn('right_gene_id', biofeature_mapper(col('right_phenotype')))
    )

    # Repartition
    df = (
        df.repartitionByRange('left_chrom', 'left_pos')
    )

    # Write
    (
        df
        .write.json(
            out_json,
            compression='gzip',
            mode='overwrite'
        )
    )

    return 0

def load_pheno_to_gene_map(inf):
    ''' Loads a dictionary, mapping phenotype_ids to ensembl gene IDs
    '''
    d = {}
    with gzip.open(inf, 'r') as in_h:

        # Skip header
        header = (
            in_h.readline()
                .decode()
                .rstrip()
                .split('\t')
        )

        # Load each line into dict
        for line in in_h:
            parts = line.decode().rstrip().split('\t')
            assert parts[header.index('gene_id')].startswith('ENSG')
            d[parts[header.index('phenotype_id')]] = \
                parts[header.index('gene_id')]
    
    return d

if __name__ == '__main__':

    main()
