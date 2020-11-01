## Tsing Hua chs30 Mixture (THM)
THM是基于清华大学的中文语音数据集THCHS30生成的**袖珍**语音分离数据集，加入的噪声选用wham的48khz噪声。数据集包含4000个train，400个dev及400个test音频。方便在**极度缺少**算力的情况下对中文音频分离的效果评估。愿天下学生都不缺显卡。为运行该脚本，需要下载THCHS30数据集，wham的48k噪声及wham生成脚本。请勿改变这些文件的目录结构。  

These scripts are used to generate the THM, a tiny dataset for speech separation task. It is derivied from the mandarin dataset [THCHS30](http://www.openslr.org/18) and noise dataset [WHAM!48kHz noise dataset](wham.whisper.ai). THM contains 4000 samples for train, 400 for dev and 400 for test. Scripts are based on WHAM and wsj0-mix.  

[wham_scripts](https://storage.googleapis.com/whisper-public/wham_scripts.tar.gz) need to be placed under this folder.

Default json files are placed under `local/metafile`. If you want to gen your own dataset, scripts can be found under (unzip file and put it under the folder, do not make any change):  
>./local/genRecipe.py  

To generate wav files, you also need to place [high_res_wham](https://storage.googleapis.com/whisper-public/high_res_wham.zip) (can be found on wham website) and [THCHS30](http://www.openslr.org/18) under this folder. Script to generate wav files:  
>./local/createMixture.py  

To make it works your folder should look like this:
>THM  
|--high_res_wham  
|--local  
|--THCHS30  
|--wham_scripts  

Mixed audio will be placed in:
>./mix  
  


Folder `mix_clean` contain mixed audio with NO noise, like wsj0-mix, wav files under `mix_both` are noise added.



Schedule：  
- 2020/10/31: Have a plan. 
- 2020/11/1: Finished 2spk-min-8k-gen.  
