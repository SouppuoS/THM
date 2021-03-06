import os
import sys
import argparse
import json
import random
import soundfile as sf
from itertools import permutations, combinations
from math import factorial, inf
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
P_META      = P_LOCAL + "/metafile"
P_TMP       = P_LOCAL + '/tmp'

# generate paramenters, will be changed by args
N_SRC       = 4
N_PREMIX    = 5
N_NOISY_USE = 2000      # num of noisy used in synthesis
N_MAX_DB    = 2.5
N_USE_SP    = 2         # max num of using a specific audio

"""
decode geometry infomation
geoInfo: list[x0,y0 x1,y1 ... xn,yn]
"""
def decodeGeo(geoInfo):
    arrayGeo   = []
    for cords in geoInfo:
        cord = cords.split(',')
        if len(cord) not in [2, 3]:
            raise Exception('only support 2/3-d coord')
        x, y = float(cord[0]), float(cord[1])
        z    = 1 if len(cord) == 2 else float(cord[2])
        arrayGeo.append([x, y, z])
    return arrayGeo

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
choose samples from sound source (for 2speakers)
"""
def chooseSample_2src(category):
    n_speaker = len(category)
    premix    = []
    for s1_idx in range(n_speaker - 1):
        ut1Idx = [v for v in range(len(category[s1_idx]['wav']))]
        random.shuffle(ut1Idx)
        for s2_idx in range(s1_idx + 1, n_speaker):
            ut2Idx = [v for v in range(len(category[s2_idx]['wav']))]
            random.shuffle(ut2Idx)
            
            if N_PREMIX > len(ut1Idx) or N_PREMIX > len(ut2Idx):
                continue
            
            for ut1, ut2 in zip(ut1Idx[:N_PREMIX], ut2Idx[:N_PREMIX]):
                db = random.random() * N_MAX_DB
                premix.append({
                    's1'        : category[s1_idx]['wav'][ut1],
                    's2'        : category[s2_idx]['wav'][ut2],
                    'permua'    : random.randint(0, 1),
                    'db'        : [db, -db],
                    'summery'   : {
                        's1_spk'    : category[s1_idx]['spk_id'],
                        's2_spk'    : category[s2_idx]['spk_id'],
                    }
                })
    random.shuffle(premix)
    return premix

"""
(for 3speakers)
"""
def chooseSample_3src(category):
    n_speaker = len(category)
    premix    = []

    for s1_idx in range(n_speaker - 2):
        ut1Idx = [v for v in range(len(category[s1_idx]['wav']))]
        random.shuffle(ut1Idx)
        for s2_idx in range(s1_idx + 1, n_speaker - 1):
            ut2Idx = [v for v in range(len(category[s2_idx]['wav']))]
            random.shuffle(ut2Idx)    
            for s3_idx in range(s2_idx + 1, n_speaker):
                ut3Idx = [v for v in range(len(category[s3_idx]['wav']))]
                random.shuffle(ut3Idx)

                if N_PREMIX > len(ut1Idx) or N_PREMIX > len(ut2Idx) or N_PREMIX > len(ut3Idx):
                    continue
                
                for ut1, ut2, ut3 in zip(ut1Idx[:N_PREMIX], ut2Idx[:N_PREMIX], ut3Idx[:N_PREMIX]):
                    db = random.random() * N_MAX_DB
                    premix.append({
                        's1'        : category[s1_idx]['wav'][ut1],
                        's2'        : category[s2_idx]['wav'][ut2],
                        's3'        : category[s3_idx]['wav'][ut3],
                        'permua'    : random.randint(0, 5),
                        'db'        : [db, 0, -db],
                        'summery'   : {
                            's1_spk'    : category[s1_idx]['spk_id'],
                            's2_spk'    : category[s2_idx]['spk_id'],
                            's3_spk'    : category[s3_idx]['spk_id'],
                        }
                    })
    random.shuffle(premix)
    return premix

"""
(for more than 3 speakers)
"""
def chooseSample_nsrc(category):
    n_speaker = len(category)
    combList  = combinations(range(n_speaker), N_SRC)
    permutNum = factorial(N_SRC)
    premix    = []
    for spks in combList:
        utIdx     = [[v for v in range(len(category[id]['wav']))] for id in spks]
        minUtSize = inf
        validComb = True

        for segId in utIdx: 
            if N_PREMIX > len(segId):
                validComb = False
                break
            random.shuffle(segId)
            minUtSize = min(minUtSize, len(segId))
        if not validComb:
            continue

        minUtSize = N_PREMIX if N_PREMIX != -1 else minUtSize
        for _utId in range(minUtSize):
            db   = [(random.random() * 2 - 1) * N_MAX_DB for _ in range(N_SRC)]
            _mix = {
                'permua'    : random.randint(0, permutNum - 1),
                'db'        : db,
                'summery'   : {},
            } 
            for _id in range(N_SRC):
                _mix[f's{_id + 1}']                = category[spks[_id]]['wav'][utIdx[_id][_utId]]
                _mix['summery'][f's{_id + 1}_spk'] = category[spks[_id]]['spk_id']
            premix.append(_mix)
            if len(premix) % 10000 == 0:
                print('.', end='')
    random.shuffle(premix)
    return premix

"""
generate details of recipe include times, len
"""
def genDetailOfRecipe(recipe, noisy_info, room, arrayGeo, minSSL, noisyCfg='rand'):
    mixture    = []
    used       = {}
    lst_permut = permutations(range(1))
    noisy, noisy_idx = noisy_info
    n_noisy    = len(noisy_idx)
    l2dist     = lambda x,y: (x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2 + (x[2] - y[2]) ** 2

    for r in recipe:
        spkValid = True
        for spk in range(N_SRC):
            spkStr = f's{spk + 1}'
            spkId  = r[spkStr]['id']
            if spkId in used and used[spkId] >= N_USE_SP:
                spkValid = False
                break

        if not spkValid:
            continue

        mix      = {
            'db'            : r['db'],
            'permutation'   : r['permua'],
            'summery'       : r['summery'],
        }
        s_len    = []
        out_name = ''
        for spk in range(N_SRC):
            spkStr = f's{spk + 1}'
            spkId  = r[spkStr]['id']
            used[spkId] = 1 if spkId not in used else used[spkId] + 1
            out_name    = out_name + r[spkStr]['fname'][:-4] + '-'
            s_len.append(len(read_scaled_wav(r[spkStr]['path'], 1, True)))
            mix[spkStr + '_path'] = r[spkStr]['path']
        mix['name'] = out_name + '.wav'

        """
        read wav files from disk, get len of each wav file, 
        decide the len of mixture, the start point of noisy, etc
        """
        # TODO: only min mode now
        mix_len = min(s_len)
        idx_n   = noisy_idx[random.randint(0, n_noisy - 1)]
        while noisy[idx_n]['len'] < mix_len:
            idx_n = noisy_idx[random.randint(0, n_noisy - 1)]
        noisy_start         = random.randint(0, noisy[idx_n]['len'] - mix_len)
        # location of sound source
        if room is not None:
            # for N_SRC sound source + 1 noise source, only support 1 noise source for now.
            mix['ssl'] = []
            for _ in range(N_SRC + 1):
                ssl = arrayGeo[0]
                d2  = minSSL ** 2
                while d2 > l2dist(ssl, arrayGeo[0]):
                    ssl = [random.random() * room[0], random.random() * room[1], random.random() * room[2]]
                mix['ssl'].append(ssl)

        mix['noisy_path']   = noisy[idx_n]['path']
        mix['noisy_start']  = noisy_start
        mix['len']          = mix_len

        mixture.append(mix)

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
def genMetafile(args):
    global N_SRC, N_PREMIX, N_USE_SP
    N_SRC         = args.src
    N_PREMIX      = args.premix
    N_USE_SP      = args.dupli
    if args.arrayGeo is not None:
        arrayGeometry = decodeGeo(args.arrayGeo)
        # only support one room setting
        roomInfo      = decodeGeo(args.room)[0]
    else:
        arrayGeometry = None
        roomInfo      = None

    PLOT_STAT_FLG = args.static
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
    P_JSON  = P_META + f'/{N_SRC}speakers'
    os.makedirs(P_META, exist_ok=True) 
    os.makedirs(P_JSON, exist_ok=True) 
    for ds in Dataset:
        print(r"Gen {} speech samples...".format(ds['name']), end='')
        ds['file'] = [k for k in os.listdir(ds['path']) if not k.endswith('.trn')]
        ds['file'].sort()
        ds['category'] = catalize(ds['file'], ds['path'])
        
        print("Complete!\nGen {} premix".format(ds['name']), end='')
        if N_SRC == 2:
            ds['recipe'] = chooseSample_2src(ds['category'])
        elif N_SRC == 3:
            ds['recipe'] = chooseSample_3src(ds['category'])
        else:
            ds['recipe'] = chooseSample_nsrc(ds['category'])

        print("Complete!\nGen {} details".format(ds['name']), end='')
        ds['mixture'] = genDetailOfRecipe(ds['recipe'], noisy, roomInfo, arrayGeometry, args.distSSL)

        print("Complete!\nGenerated {} samples!".format(len(ds['mixture'])))
        with open(P_JSON + '/' + ds['name'] + '.json', 'w') as f:
            json.dump(ds['mixture'], f, indent=4)

        # summery all mixture
        # summery[ds['name'] + 'NumUsed'] = summeryRecipe(ds['mixture'])
    
    if PLOT_STAT_FLG:
        plotBarOfNum(summery)

if __name__ == "__main__":
    parse = argparse.ArgumentParser()
    parse.add_argument("--src",      default=2,         type=int,       help='Number of speakers')
    parse.add_argument("--premix",   default=-1,        type=int,       help='Number of mixing audio from a specific combine of speakers')
    parse.add_argument("--dupli",    default=2,         type=int,       help='Number of max times using a specific audio')
    parse.add_argument("--static",   default=False,     type=bool,      help='Static of speakers used in mixtures')
    parse.add_argument("--arrayGeo", default=None,      nargs='+',      help="set the geometry of the mic array, e.g. --arrayGeo 0,1,0 0,0,0, support 2-d or 3-d coord")
    parse.add_argument("--room",     default="4,4,2",   nargs='+',      help="size of the room, e.g. --room 4,4,2, support 2-d or 3-d")
    parse.add_argument("--distSSL",  default=1.0,       type=float,     help="minimun distance between sound source and microphone")
    conf  = parse.parse_args()
    genMetafile(conf)
