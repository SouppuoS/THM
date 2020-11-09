import os
import sys
import json
import random
import soundfile as sf
sys.path.extend('..')
from wham_scripts.utils import read_scaled_wav, quantize

FLAG_SHUFFLE = False

# num of mixture to gen
N_GEN_TRN   = 5000
N_GEN_DEV   = 800
N_GEN_TST   = 2000

# Path Information
P_SRC       = "./THCHS30/data_thchs30"
P_SRC_TRN   = P_SRC + "/train"
P_SRC_DEV   = P_SRC + "/dev"
P_SRC_TST   = P_SRC + "/test"
P_NOISY     = "./high_res_wham/audio"
P_LOCAL     = "./local"
P_JSON      = P_LOCAL + "/metafile"
P_TMP       = P_LOCAL + '/tmp'

# TODO: only support 8k 2spk min mode for now
P_MIX       = './mix'
P_MIX_SPK   = P_MIX + '/2speakers'
P_MIX_HZ    = P_MIX_SPK + '/wav8k'
P_MIX_MODE  = P_MIX_HZ + '/min'

P_SET_OUT   = [P_MIX, P_MIX_SPK, P_MIX_HZ, P_MIX_MODE]

dB = lambda db: 10 ** (db / 20)

"""
generate wav file from metafile located in ./local/metafile
"""
def generateWav():
    for p in P_SET_OUT:
        os.makedirs(p, exist_ok=True)

    dataset = [
        {'name':'tr', 'n_gen':N_GEN_TRN},
        {'name':'cv', 'n_gen':N_GEN_DEV},
        {'name':'tt', 'n_gen':N_GEN_TST},
    ]
    out_path = ['/s1', '/s2', '/mix_clean', '/mix_both']

    cnt = 0
    print('Generate wav files', end='')
    for d in dataset:
        cnt += 1
        if cnt % 100 == 0:
            print('.', end='')
        p_recipe = os.path.join(P_JSON, d['name'] + '.json')
        if not os.path.exists(p_recipe):
            raise Exception(r'No metafile {}!'.format(d['name']))
        with open(p_recipe) as f:
            f_recipe = json.load(f)
        
        P_MIX_WAV = P_MIX_MODE + '/' + d['name']
        os.makedirs(P_MIX_WAV , exist_ok=True)
        for path in out_path:
            os.makedirs(P_MIX_WAV + path, exist_ok=True)
        
        if FLAG_SHUFFLE:
            random.shuffle(f_recipe)

        f_recipe   = f_recipe[:d['n_gen']]        # gen `n_gen` mixtures
        f_recipe   = sorted(f_recipe, key=lambda x: x['noisy_path'])
        noisy_path = None
        for r in f_recipe:
            if noisy_path != r['noisy_path']:
                noisy_path = r['noisy_path']
                # TODO: Noisy db random
                noisy = read_scaled_wav(noisy_path, dB(6), True)
            
            # TODO: only support 2 src now
            if r['permutation'] == 0:
                s1 = read_scaled_wav(r['s1_path'], dB( r['db']), True) 
                s2 = read_scaled_wav(r['s2_path'], dB(-r['db']), True)
            else:
                s2 = read_scaled_wav(r['s1_path'], dB( r['db']), True) 
                s1 = read_scaled_wav(r['s2_path'], dB(-r['db']), True)
            sample_s1 = quantize(s1[:r['len']])
            sample_s2 = quantize(s2[:r['len']])
            sample_n  = noisy[r['noisy_start'] : r['noisy_start'] + r['len']]

            out_data  = [
                sample_s1,  sample_s2, 
                sample_s1 + sample_s2, 
                sample_s1 + sample_s2 + sample_n,
            ]

            for data, path in zip(out_data, out_path):
                sf.write(os.path.join(P_MIX_WAV + path, r['name']), data, 8000, subtype='FLOAT')
    print('Complete!')

if __name__ == '__main__':
    generateWav()