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
from pprint import pprint

"""
this script is used to random choose targets which used to make mixture audio
it will finally output a json file which tell next step how to generate
"""

# Path Information
P_SRC       = "./THCHS30/data_thchs30"
P_SRC_TRN   = P_SRC + "/train"
P_SRC_DEV   = P_SRC + "/dev"
P_SRC_TST   = P_SRC + "/test"
P_NOISY     = "./high_res_wham/audio"
P_LOCAL     = "./local"
P_JSON      = P_LOCAL + "/metafile"
P_TMP       = P_LOCAL + '/tmp'

# generate paramenters
N_SRC       = 2
N_PREMIX    = -1 
N_NOISY_USE = 2000      # num of noisy used in synthesis
N_MAX_DB    = 2.5
N_USE_SP    = 2         # max num of using a specific audio

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
                    'summery'   : {
                        's1_spk'    : category[s1_idx]['spk_id'],
                        's2_spk'    : category[s2_idx]['spk_id'],
                    }
                })
    random.shuffle(premix)
    return premix

"""
generate details of recipe include times, len
"""
def genDetailOfRecipe(recipe, noisy_info):
    mixture    = []
    used       = {}
    lst_permut = permutations(range(1))
    noisy, noisy_idx = noisy_info
    n_noisy    = len(noisy_idx)

    for r in recipe:
        s1id = r['s1']['id']
        s2id = r['s2']['id']
        if (s1id in used and used[s1id] >= N_USE_SP) \
        or (s2id in used and used[s2id] >= N_USE_SP):
            continue
        used[s1id] = 1 if s1id not in used else used[s1id] + 1
        used[s2id] = 1 if s2id not in used else used[s2id] + 1

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
            'summery'       : r['summery'],
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
    
    print('Loading noisy info from json...', end='')
    info      = {}
    noisy_idx = []
    os.makedirs(P_TMP, exist_ok=True)
    if os.path.exists(P_TMP + '/noisy_info.json'):
        with open(P_TMP + '/noisy_info.json', 'r') as f:
            _t = json.load(f)
        info = {int(v[0]):v[1] for v in _t.items()}

    print('Complete!\nLoading noisy info from wav', end='')
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

"""
Do some summery task
"""
def summeryRecipe(mixture):
    n_spkSample = {}        # summery the number of a specific speaker's audio used in mixture
    for r in mixture:
        s1_spk = r['summery']['s1_spk']
        s2_spk = r['summery']['s2_spk']
        n_spkSample[s1_spk] = 1 if s1_spk not in n_spkSample else n_spkSample[s1_spk] + 1
        n_spkSample[s2_spk] = 1 if s2_spk not in n_spkSample else n_spkSample[s2_spk] + 1
    return n_spkSample

"""
plot bar of the num used in mixture
"""
def plotBarOfNum(s):
    p_bar_spk_x = {}
    p_bar_color = ['r', 'g', 'b']
    datasetName = ['tr', 'cv', 'tt']
    for idx, c in zip(range(3), p_bar_color):
        s_Num = s[datasetName[idx] + 'NumUsed']
        for spk, num in s_Num.items():
            if spk not in p_bar_spk_x:
                p_bar_spk_x[spk] = len(p_bar_spk_x)
            plt.bar(p_bar_spk_x[spk] + idx * 0.3, num, width=0.3, color=c)
    pprint(p_bar_spk_x)
    plt.show()
"""
gen mixture
"""
def genMetafile():       
    os.makedirs(P_JSON, exist_ok=True) 
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
        {'name':'tr', 'path': P_SRC_TRN},
        {'name':'cv', 'path': P_SRC_DEV},
        {'name':'tt', 'path': P_SRC_TST},
    ]
    noisy   = loadNoisyInfo()
    summery = {}
    for ds in Dataset:
        print(r"Gen {} speech samples".format(ds['name']), end='')
        ds['file']      = [k for k in os.listdir(ds['path']) if not k.endswith('.trn')]
        ds['file'].sort()
        ds['category']  = catalize(ds['file'], ds['path'])
        ds['recipe']    = chooseSample(ds['category'])
        ds['mixture']   = genDetailOfRecipe(ds['recipe'], noisy)
        
        print("Complete!\nGenerated {} samples!".format(len(ds['mixture'])))
        with open(P_JSON + '/' + ds['name'] + '.json', 'w') as f:
            json.dump(ds['mixture'], f)

        # summery all mixture
        summery[ds['name'] + 'NumUsed'] = summeryRecipe(ds['mixture'])
    plotBarOfNum(summery)

if __name__ == "__main__":
    genMetafile()
