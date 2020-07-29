#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import argparse
from glob import glob
from os import makedirs, path
import pandas as pd
import pickle
import sys

from nistats.second_level_model import SecondLevelModel
from nistats.thresholding import map_threshold
from nilearn import plotting
from utils.firstlevel_utils import (get_first_level_objs, 
                                    get_first_level_maps, 
                                    load_first_level_objs, 
                                    FirstLevel)
from utils.secondlevel_utils import create_group_mask, randomise
from utils.utils import get_contrasts, get_flags


# ### Parse Arguments
# These are not needed for the jupyter notebook, but are used after conversion to a script for production
# 
# - conversion command:
#   - jupyter nbconvert --to script --execute 2ndlevel_analysis.ipynb

# In[ ]:


parser = argparse.ArgumentParser(description='2nd level Entrypoint Script.')
parser.add_argument('-derivatives_dir', default=None)
parser.add_argument('--tasks', nargs="+", help="Choose from ANT, CCTHot, discountFix,                                     DPX, motorSelectiveStop, stopSignal,                                     stroop, surveyMedley, twoByTwo, WATT3")
parser.add_argument('--rerun', action='store_true')
parser.add_argument('--rt', action='store_true')
parser.add_argument('--beta', action='store_true')
parser.add_argument('--n_perms', default=1000, type=int)
parser.add_argument('--quiet', '-q', action='store_true')
parser.add_argument('--aim', default='NONE', help='Choose from aim1, aim2')
parser.add_argument('--group', default='NONE')

if '-derivatives_dir' in sys.argv or '-h' in sys.argv:
    args = parser.parse_args()
else:
    args = parser.parse_args([])
    args.derivatives_dir = '/data/derivatives/'
    args.tasks = ['stroop']
    args.rt=True
    args.n_perms = 10


# In[ ]:


if not args.quiet:
    def verboseprint(*args, **kwargs):
        print(*args, **kwargs)
else:
    verboseprint = lambda *a, **k: None # do-nothing function


# ### Setup
# 
# Organize paths and set parameters based on arguments

# In[ ]:


# set paths
first_level_dir = path.join(args.derivatives_dir, '1stlevel')
second_level_dir = path.join(args.derivatives_dir,'2ndlevel')
fmriprep_dir = path.join(args.derivatives_dir, 'fmriprep')

# set tasks
if args.tasks is not None:
    tasks = args.tasks
else:
    tasks = ['ANT', 'CCTHot', 'discountFix',
            'DPX', 'motorSelectiveStop',
            'stopSignal', 'stroop',
            'twoByTwo', 'WATT3']
    
# set other variables
regress_rt = args.rt
beta_series = args.beta
n_perms = args.n_perms
group = args.group

# ### Create Mask

# In[ ]:


mask_threshold = .95
mask_loc = path.join(second_level_dir, 'group_mask_thresh-%s.nii.gz' % str(mask_threshold))
if path.exists(mask_loc) == False or args.rerun:
    verboseprint('Making group mask')
    group_mask = create_group_mask(fmriprep_dir, mask_threshold)
    makedirs(path.dirname(mask_loc), exist_ok=True)
    group_mask.to_filename(mask_loc)


# ### Create second level objects
# Gather first level models and create second level model

# In[ ]:

# Set up 2ndlevel Regressors - Added by HMJ 7.29.20
aim1_2ndlevel_confounds_path = "/scripts/aim1_2ndlevel_regressors/aim1_2ndlevel_confounds_matrix.csv"
full_confounds_df = pd.read_csv(aim1_2ndlevel_confounds_path, index_col='index')

def get_2ndlevel_designMatrix_andContrasts(maps, task):
    design_matrix = pd.DataFrame([1] * len(maps), columns=['intercept'])
    contrasts = [1]
    if args.aim=='aim1':
        subjects = [m.split('1stlevel/')[-1].split('/')[0] for m in maps]
        design_matrix = full_confounds_df.loc[subjects, ['age', 'sex', task+'_meanFD']].copy()
        design_matrix.index.rename('subject_label', inplace=True)
        design_matrix['intercept'] = 1
        contrasts = [0, 0, 0, 1]
    return design_matrix, contrasts

def filter_maps_designMatrix(maps, design_matrix):
    drop_num = design_matrix.isna().any(axis=1).sum()
    print('dropping ' + str(drop_num) +' due to missing values in design matrix')
    design_matrix = design_matrix.dropna()
    if len(design_matrix)!=len(maps):
        keep_subs = dm.index.tolist()
        maps = [m for m in maps if m.split('1stlevel/')[-1].split('/')[0] in keep_subs]
    assert(len(design_matrix)==len(maps))
    return maps, design_matrix


rt_flag, beta_flag = get_flags(regress_rt, beta_series)
for task in tasks:
    verboseprint('Running 2nd level for %s' % task)
    # load first level models
    # create contrast maps
    verboseprint('*** Creating maps')
    task_contrasts = get_contrasts(task, regress_rt)
    maps_dir = path.join(second_level_dir, task, 'secondlevel-%s_%s_maps' % (rt_flag, beta_flag))
    makedirs(maps_dir, exist_ok=True)
    # run through each contrast for all participants
    if group == 'NONE':
        for name, contrast in task_contrasts:
            second_level_model = SecondLevelModel(mask=mask_loc, smoothing_fwhm=6)
            maps = get_first_level_maps('*', task, first_level_dir, name, regress_rt, beta_series)
            N = str(len(maps)).zfill(2)
            verboseprint('****** %s, %s files found' % (name, N))
            if len(maps) <= 1:
                verboseprint('****** No Maps')
                continue
            # CHANGED TO HANDLE GROUP COVARIATES
            design_matrix, curr_contrasts = get_2ndlevel_designMatrix_andContrasts(maps, task)
            maps, design_matrix = filter_maps_designMatrix(maps, design_matrix)
            second_level_model.fit(maps, design_matrix=design_matrix)
            contrast_map = second_level_model.compute_contrast(second_level_contrast=curr_contrasts)
            # save
            contrast_file = path.join(maps_dir, 'contrast-%s.nii.gz' % name)
            contrast_map.to_filename(contrast_file)
            # write metadata
            with open(path.join(maps_dir, 'metadata.txt'), 'a') as f:
                f.write('Contrast-%s: %s maps\n' % (contrast, N))
            # save corrected map
            if n_perms > 0:
                verboseprint('*** Running Randomise')
                randomise(maps, maps_dir, mask_loc, n_perms=n_perms)
                # write metadata
                with open(path.join(maps_dir, 'metadata.txt'), 'a') as f:
                    f.write('Contrast-%s: Randomise run with %s permutations\n' % (contrast, str(n_perms)))
    # run through each contrast within each group
    else:
        verboseprint('*** Creating %s maps' % group)
        f = open("/scripts/%s_subjects.txt" % group,"r") 
        group_subjects = f.read().split('\n')
        for name, contrast in task_contrasts:
            second_level_model = SecondLevelModel(mask=mask_loc, smoothing_fwhm=6)
            maps = []
            for curr_subject in group_subjects:
                curr_map = get_first_level_maps(curr_subject, task, first_level_dir, name, regress_rt, beta_series)
                if len(curr_map): #if a map is present
                    # maps.append(curr_map[0])
                    maps += curr_map
            N = str(len(maps)).zfill(2)
            verboseprint('****** %s, %s files found' % (name, N))
            if len(maps) <= 1:
                verboseprint('****** No Maps')
                continue
            # CHANGED TO HANDLE GROUP COVARIATES
            design_matrix, curr_contrasts = get_2ndlevel_designMatrix_andContrasts(maps, task)
            maps, design_matrix = filter_maps_designMatrix(maps, design_matrix)
            second_level_model.fit(maps, design_matrix=design_matrix)
            contrast_map = second_level_model.compute_contrast(second_level_contrast=curr_contrasts)
            # save
            makedirs(path.join(maps_dir, group), exist_ok=True)
            contrast_file = path.join(maps_dir, group, 'contrast-%s-%s.nii.gz' % (name, group))
            contrast_map.to_filename(contrast_file)
            # write metadata
            with open(path.join(maps_dir, group, 'metadata.txt'), 'a') as f:
                f.write('Contrast-%s-%s: %s maps\n' % (contrast, group, N))
            # save corrected map
            if n_perms > 0:
                verboseprint('*** Running Randomise')
                randomise(maps, path.join(maps_dir, group), mask_loc, n_perms=n_perms, group=group)
                # write metadata
                with open(path.join(maps_dir, group, 'metadata.txt'), 'a') as f:
                    f.write('Contrast-%s-%s: Randomise run with %s permutations\n' % (contrast, group, str(n_perms)))


    verboseprint('Done with %s' % task)


# In[ ]:


"""
# Using nistats method of first level objects. Not conducive for randomise.
rt_flag, beta_flag = get_flags(regress_rt, beta_series)
for task in tasks:
    verboseprint('Running 2nd level for %s' % task)
    # load first level models
    first_levels = load_first_level_objs(task, first_level_dir, regress_rt=regress_rt)
    if len(first_levels) == 0:
        continue
    first_level_models = [subj.fit_model for subj in first_levels]
    N = str(len(first_level_models)).zfill(2)

    # simple design for one sample test
    design_matrix = pd.DataFrame([1] * len(first_level_models), columns=['intercept'])
    
    # run second level
    verboseprint('*** Running model. %s first level files found' % N)
    second_level_model = SecondLevelModel(mask=mask_loc, smoothing_fwhm=6).fit(
        first_level_models, design_matrix=design_matrix)
    makedirs(path.join(second_level_dir, task), exist_ok=True)
    f = open(path.join(second_level_dir, task, 'secondlevel_%s_%s.pkl' % (rt_flag, beta_flag)), 'wb')
    pickle.dump(second_level_model, f)
    f.close()
    
    # create contrast maps
    verboseprint('*** Creating maps')
    task_contrasts = get_contrasts(task, regress_rt)
    maps_dir = path.join(second_level_dir, task, 'secondlevel_%s_%s_N-%s_maps' % (rt_flag, beta_flag, N))
    makedirs(maps_dir, exist_ok=True)
    for name, contrast in task_contrasts:
        verboseprint('****** %s' % name)
        contrast_map = second_level_model.compute_contrast(first_level_contrast=contrast)
        contrast_file = path.join(maps_dir, 'contrast-%s.nii.gz' % name)
        contrast_map.to_filename(contrast_file)
"""

