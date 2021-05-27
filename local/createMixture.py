import os
import sys
import json
import random
import soundfile as sf
import argparse
sys.path.extend('..')
from wham_scripts.utils import read_scaled_wav, quantize
from itertools import permutations

from local.genRecipe import decodeGeo
import scipy.signal as ss
import rir_generator as rir

# num of mixture to gen, will be changed by args
FLAG_SHUFFLE  = False
N_SRC         = 3
N_GEN_TRN     = 5000
N_GEN_DEV     = 800
N_GEN_TST     = 2000

dB = lambda db: 10 ** (db / 20)

"""
generate wav file from metafile located in ./local/metafile
"""
def generateWav(args):
    global N_SRC, N_GEN_TRN, N_GEN_DEV, N_GEN_TST
    N_SRC       = args.src
    N_GEN_TRN   = args.gen_trn
    N_GEN_DEV   = args.gen_dev
    N_GEN_TST   = args.gen_tst

    # Path Information
    P_SRC       = "./THCHS30/data_thchs30"
    P_SRC_TRN   = P_SRC + "/train"
    P_SRC_DEV   = P_SRC + "/dev"
    P_SRC_TST   = P_SRC + "/test"
    P_NOISY     = "./high_res_wham/audio"
    P_LOCAL     = "./local"
    P_META      = P_LOCAL + "/metafile"
    P_JSON      = P_META  + f'/{N_SRC}speakers'
    P_TMP       = P_LOCAL + '/tmp'

    # TODO: only support 8k min mode for now
    P_MIX       = './mix'
    P_MIX_SPK   = P_MIX     + f'/{N_SRC}speakers'
    P_MIX_HZ    = P_MIX_SPK + '/wav8k'
    P_MIX_MODE  = P_MIX_HZ  + '/min'

    cleanMixVer = True if N_SRC > 1 else False

    if args.arrayGeo is not None:
        arrayGeometry = decodeGeo(args.arrayGeo)
        # only support one room setting
        roomInfo      = decodeGeo(args.room)[0]
    else:
        arrayGeometry = None
        roomInfo      = None

    dataset = [
        {'name':'tr', 'n_gen':N_GEN_TRN},
        {'name':'cv', 'n_gen':N_GEN_DEV},
        {'name':'tt', 'n_gen':N_GEN_TST},
    ]
    out_path = [f'/s{v + 1}' for v in range(N_SRC)] + (['/mix_clean', '/mix_both'] if cleanMixVer else ['/mix_both'])
    order    = [v for v in permutations(range(N_SRC))]       # permutation order
    cnt      = 0
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
                rdB   = random.randint(6, 18)
                noisy = read_scaled_wav(noisy_path, dB(rdB), True)
            
            pidx  = order[r['permutation']]
            wav   = []
            scale = [dB(v) for v in r['db']]
            for spk in range(N_SRC):
                wav.append(read_scaled_wav(r[f's{spk + 1}_path'], 1, True))
            sample    = [quantize(wav[v][:r['len']] * scale[k]) for v, k in zip(pidx, range(N_SRC))]
            sample_n  = noisy[r['noisy_start'] : r['noisy_start'] + r['len']]
            if 'ssl' in r:
                wav_multi = []
                for _wav, s in zip(sample + [sample_n], r['ssl']):
                    h = rir.generate(
                        c=340, fs=8000,                         # only support 8k
                        r=arrayGeometry, s=s, L=roomInfo,
                        reverberation_time=0.2, nsample=4096,
                    )
                    wav_multi.append(ss.convolve(h[:, None, :], _wav[...,None,None]).transpose(1,0,2).squeeze())
                out_data = sample + ([sum(wav_multi[:N_SRC]), sum(wav_multi)] if cleanMixVer else [sum(wav_multi)])
            else:
                out_data = sample + ([sum(sample), sum(sample) + sample_n] if cleanMixVer else [sum(sample) + sample_n])

            for data, path in zip(out_data, out_path):
                sf.write(os.path.join(P_MIX_WAV + path, r['name']), data, 8000, subtype='FLOAT')
    print('Complete!')

if __name__ == '__main__':
    parse = argparse.ArgumentParser()
    parse.add_argument("--src",         default=2,      type=int,   help='Number of speakers')
    parse.add_argument("--gen_trn",     default=5000,   type=int,   help='Number of train set')
    parse.add_argument("--gen_dev",     default=800,    type=int,   help='Number of dev set')
    parse.add_argument("--gen_tst",     default=2000,   type=int,   help='Number of test set')
    parse.add_argument("--arrayGeo",    default=None,   nargs='+',  help="set the geometry of the mic array, e.g. --arrayGeo 0,1,0 0,0,0, support 2-d or 3-d coord")
    parse.add_argument("--room",        default="4,4,2",nargs='+',  help="size of the room, e.g. --room 4,4,2, support 2-d or 3-d")
    conf  = parse.parse_args()
    generateWav(conf)
    