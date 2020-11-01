import os
import sys
import argparse
import json
import random
import soundfile as sf
from itertools import permutations
sys.path.extend('..')
from wham_scripts.utils import read_scaled_wav
import matplotlib.pyplot as plt

"""
this script is used to random choose targets which used to make mixture audio
it will finally output a json file which tell next step how to generate
"""

# Path Information
P_SRC_TRN   = "./THCHS30/data_thchs30/train"
P_SRC_DEV   = "./THCHS30/data_thchs30/train"
P_SRC_TST   = "./THCHS30/data_thchs30/dev"
P_NOISY     = "./high_res_wham/audio"

P_LOCAL     = "./local"
P_JSON      = P_LOCAL + "/metafile"
P_TMP       = P_LOCAL + '/tmp'

# generate paramenters
N_SRC       = 2
N_PREMIX    = -1 
N_NOISY_USE = 200      # num of noisy used in synthesis
N_MAX_DB    = 2.5
N_GEN_TRN   = 4000
N_GEN_DEV   = 400
N_GEN_TST   = 400

"""
sort wav file according to speaker
"""
def catalize(data_list, path):
    spk_id  = None      # current spk id of spk_wav
    spk_wav = []        # temporary save wav info
    spk_cat = []        # save category info
    idx     = 0
    for k in data_list:
        spk_id_new = k[:k.find("_")]
        if spk_id != spk_id_new:
            if len(spk_wav) > 0:
                spk_cat.append({
                    'spk_id': spk_id, 
                    'wav'   : spk_wav
                })
                spk_wav = []
            spk_id = spk_id_new
        spk_wav.append({
            'fname' : k, 
            'id'    : idx,
            'path'  : r"{}/{}".format(path, k)
        })
        idx += 1
    return spk_cat

"""
choose samples from sound source 
"""
def chooseSample(category):
    n_speaker = len(category)
    premix    = []
    for s1_idx in range(n_speaker - 1):
        for s2_idx in range(s1_idx + 1, n_speaker):
            ut1Idx = [v for v in range(len(category[s1_idx]['wav']))]
            ut2Idx = [v for v in range(len(category[s2_idx]['wav']))]
            random.shuffle(ut1Idx)
            random.shuffle(ut2Idx)
            if N_PREMIX > len(ut1Idx) or N_PREMIX > len(ut2Idx):
                print(f"N_PREMIX larger than ut({s1_idx}-{len(ut1Idx)}:{s2_idx}-{len(ut2Idx)})")
            for ut1, ut2 in zip(ut1Idx[:N_PREMIX], ut2Idx[:N_PREMIX]):
                premix.append({
                    's1'        : category[s1_idx]['wav'][ut1],
                    's2'        : category[s2_idx]['wav'][ut2],
                    'permua'    : random.randint(0, 1),
                    'db'        : random.random() * N_MAX_DB,
                })
    random.shuffle(premix)
    return premix

"""
generate details of recipe include times, len
"""
def genDetailOfRecipe(recipe, noisy_info):
    mixture    = []
    used       = []
    lst_permut = permutations(range(1))
    noisy, noisy_idx = noisy_info
    n_noisy    = len(noisy_idx)

    for r in recipe:
        if r['s1']['id'] in used or r['s2']['id'] in used:
            continue
        used.append(r['s1']['id'])
        used.append(r['s2']['id'])
        
        """
        read wav files from disk, get len of each wav file, 
        decide the len of mixture, the start point of noisy, etc
        """
        s_len = [
            len(read_scaled_wav(r['s1']['path'], 1, True)), 
            len(read_scaled_wav(r['s2']['path'], 1, True))
        ]
        
        # TODO: only min mode now
        mix_len = min(s_len)
        idx_n   = noisy_idx[random.randint(0, n_noisy - 1)]
        while noisy[idx_n]['len'] < mix_len:
            idx_n = noisy_idx[random.randint(0, n_noisy - 1)]
        noisy_start = random.randint(0, noisy[idx_n]['len'] - mix_len)        

        out_name = r"{}-{}-{:.1f}-{}.wav".format(
            r['s1']['fname'][:-4], r['s2']['fname'][:-4],
            r['db'], r['permua']
        )
        mixture.append({
            'name'          : out_name,
            's1_path'       : r['s1']['path'],
            's2_path'       : r['s2']['path'],
            'db'            : r['db'],
            'permutation'   : r['permua'],
            'noisy_path'    : noisy[idx_n]['path'],
            'noisy_start'   : noisy_start,
            'len'           : mix_len,
        })

        if len(mixture) % 100 == 0:
            print('.', end='')

    return mixture

"""
get noisy audio infomation like audio len
info      : infomation of audio in discrete
noisy_idx : tell which idx is used in gen
"""
def loadNoisyInfo():
    
    _t          = os.listdir(P_NOISY)
    _t.sort()
    lst_noisy   = [(k, v) for k, v in zip(range(len(_t)),_t)]   # set of tuple (idx, path)
    random.shuffle(lst_noisy)
    
    print('Loading noisy info from json...')
    info      = {}
    noisy_idx = []
    os.makedirs(P_TMP, exist_ok=True)
    if os.path.exists(P_TMP + '/noisy_info.json'):
        with open(P_TMP + '/noisy_info.json', 'r') as f:
            _t = json.load(f)
        info = {int(v[0]):v[1] for v in _t.items()}

    print('Loading noisy info from wav', end='')
    for idx, path in lst_noisy[:N_NOISY_USE]:
        noisy_idx.append(idx)
        if len(noisy_idx) % 100 == 0:
            print('.', end='')
        if idx in info.keys():
            continue
        info[idx] = {
            'path': P_NOISY + '/' + path, 
            'len' : len(read_scaled_wav(r"{}/{}".format(P_NOISY, path), 1, True))
        }

    with open(P_TMP + '/noisy_info.json', 'w') as f:
        json.dump(info, f)
    print('Complete!')
    
    return info, noisy_idx

def genMetafile():       
    os.makedirs(P_JSON, exist_ok=True)
    lst_trn = [k for k in os.listdir(P_SRC_TRN) if not k.endswith('.trn')]
    lst_tst = [k for k in os.listdir(P_SRC_TST) if not k.endswith('.trn')]
    random.shuffle(lst_trn)
    lst_dev     = lst_trn[:len(lst_tst)]
    lst_trn     = lst_trn[len(lst_tst):]
    noisy       = loadNoisyInfo()
    
    """
    file: 
        set of file names under P_SRC_*
    path: 
        the dir of file
    category: 
        set of [
            spk_id(like 'A11'), 
            Info of spk_id's pk_wav(s) include [
                filename, 
                idx(index in tr tt or cv), 
                path]]
    recipe: 
        set of [
            recipe of clean mix, Info of s?[
                path of orig speech,
                and idx]
            permuation, the idx of permuation used in generate,
            db used in 1st 2nd or 3rd sound in recipe]
    """
    Dataset = [
        {'name':'tr', 'file': lst_trn, 'path': P_SRC_TRN, 'n_gen': N_GEN_TRN},
        {'name':'cv', 'file': lst_dev, 'path': P_SRC_TRN, 'n_gen': N_GEN_DEV},
        {'name':'tt', 'file': lst_tst, 'path': P_SRC_TST, 'n_gen': N_GEN_TST},
    ]
    for ds in Dataset:
        print(r"Gen {} speech samples".format(ds['name']), end='')
        ds['file'].sort()
        ds['category']  = catalize(ds['file'], ds['path'])
        ds['recipe']    = chooseSample(ds['category'])
        ds['mixture']   = genDetailOfRecipe(ds['recipe'], noisy)
        
        print("Complete!\nGenerated {} samples!".format(len(ds['mixture'])))
        with open(P_JSON + '/' + ds['name'] + '.json', 'w') as f:
            json.dump(ds['mixture'][:ds['n_gen']], f)

if __name__ == "__main__":
    genMetafile()