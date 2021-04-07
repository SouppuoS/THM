#!/bin/bash

stage=0
src=2
n_tr=5000
n_cv=800
n_tt=2000
n_pre=-1
n_sp=2

. local/parse_options.sh

if [[ $stage -le 0 ]]; then
    echo Stage 0: prepare data
    echo Not implement yet...
    exit
fi

# gen metafile
if [[ $stage -le 1 ]]; then
    echo Stage 1: gen metafiles
    python local/genRecipe.py \
    --src $src \
    --premix $n_pre \
    --dupli $n_sp \
    --room 4,6,3
fi

if [[ $stage -le 2 ]]; then
    echo Stage 2: gen wav files
    python local/createMixture.py \
    --src $src \
    --gen_trn $n_tr \
    --gen_dev $n_cv \
    --gen_tst $n_tt
fi
echo Finish: Gen Complete!