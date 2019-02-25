"""
some util functions
"""
import numpy as np
import pandas as pd

# ********************************************************
# 1st level analysis utility functions
# ********************************************************        
# functions to extract fmri events        
def get_ev_vars(output_dict, events_df, condition_spec, col=None, 
                amplitude=1, duration=0, subset=None, onset_column='onset'):
    """ adds amplitudes, conditions, durations and onsets to an output_dict
    
    Args:
        events_df: events file to parse
        condition_spec: string specfying condition name, or list of tuples of the fomr
            (subset_key, name) where subset_key groups the rows in col. If a list,
            col must be specified
        col: the column to be subset by the keys in conditions
        amplitude: either an int or string. If int, sets a constant amplitude. If
            string, amplitude is set to that column
        duration: either an int or string. If int, sets a constant duration. If
            string, duration is set to that column
        subset: pandas query string to subset the data before use
        onset_column: the column of timing to be used for onsets
    
    """
    required_keys =  set(['amplitudes','conditions','durations','onsets'])
    assert set(output_dict.keys()) == required_keys
    amplitudes = output_dict['amplitudes']
    conditions = output_dict['conditions']
    durations = output_dict['durations']
    onsets = output_dict['onsets']
    
    # if subset is specified as a string, use to query
    if subset is not None:
        events_df = events_df.query(subset)
    # if amplitudes or durations were passed as a series, subset and conver tto list
    if type(duration) == pd.core.series.Series:
        duration = duration[events_df.index].tolist()
    if type(amplitude) == pd.core.series.Series:
        amplitude = amplitude[events_df.index].tolist()
        
    # if a column is specified, group by the values in that column
    if type(condition_spec) == list:
        assert (col is not None), "Must specify column when condition_spec is a list"
        group_df = events_df.groupby(col)
        for condition, condition_name in condition_spec:
            if type(condition) is not list:
                condition = [condition]
            # get members of group identified by the condition list
            c_dfs = [group_df.get_group(c) for c in condition 
                     if c in group_df.groups.keys()]
            if len(c_dfs)!=0:
                c_df = pd.concat(c_dfs)
                conditions.append(condition_name)
                onsets.append(c_df.loc[:,onset_column].tolist())
                if type(amplitude) in (int,float):
                    amplitudes.append([amplitude]*len(onsets[-1]))
                elif type(amplitude) == str:
                    amplitudes.append(c_df.loc[:,amplitude].tolist())
                if type(duration) in (int,float):
                    durations.append([duration]*len(onsets[-1]))
                elif type(duration) == str:
                    durations.append(c_df.loc[:,duration].tolist())
    elif type(condition_spec) == str:
        group_df = events_df
        conditions.append(condition_spec)
        onsets.append(group_df.loc[:,onset_column].tolist())
        if type(amplitude) in (int,float):
            amplitudes.append([amplitude]*len(onsets[-1]))
        elif type(amplitude) == str:
            amplitudes.append(group_df.loc[:,amplitude].tolist())
        elif type(amplitude) == list:
            amplitudes.append(amplitude)
        if type(duration) in (int,float):
            durations.append([duration]*len(onsets[-1]))
        elif type(duration) == str:
            durations.append(group_df.loc[:,duration].tolist())
        elif type(duration) == list:
            durations.append(duration)
    # ensure that each column added is all numeric
    for attr in [durations, amplitudes, onsets]:
        assert np.issubdtype(np.array(attr[-1]).dtype, np.number)   
        assert pd.isnull(attr[-1]).sum() == 0
    

# specific task functions
def get_ANT_EVs(events_df, regress_rt=True):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    # cue type
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('spatial', 'spatial'),
                                  ('double', 'double')],
                col='cue',
                duration='duration',
                subset='junk==False')
    # conflict type
    get_ev_vars(output_dict, events_df,
                condition_spec = [('congruent', 'congruent'),
                                  ('incongruent', 'incongruent')],
                col='flanker_type',
                duration='duration',
                subset='junk==False')
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False')
    return output_dict


def get_CCTHot_EVs(events_df, regress_rt):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    # task
    get_ev_vars(output_dict, events_df,
                condition_spec='task',
                duration='duration',
                subset='junk==False')
    # add main parametric regressors: EV and risk
    get_ev_vars(output_dict, events_df, 
                condition_spec='EV', 
                duration='duration', 
                amplitude='EV',
                subset='junk==False')
    get_ev_vars(output_dict, events_df, 
                condition_spec='risk',
                duration='duration', 
                amplitude='risk',
                subset='junk==False')
    # other regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec='num_click_in_round', 
                duration='duration', 
                amplitude='num_click_in_round',
                subset='junk==False')
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(1,'reward'), (0,'punishment')], 
                col='feedback',
                subset='junk==False')
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False')
    return output_dict

def get_discountFix_EVs(events_df, regress_rt=True):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    # regressors of interest
    trial_type = events_df.query('junk == False').trial_type \
                .replace({'larger_later': 1, 'smaller_sooner': -1})
    get_ev_vars(output_dict, events_df, 
                condition_spec='LL_vs_SS',
                amplitude=trial_type,
                duration='duration',
                subset='junk == False')
    get_ev_vars(output_dict, events_df, 
                condition_spec='subjective_value', 
                duration='duration', 
                amplitude='subjective_value',
                subset='junk==False')
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')],
                col='junk', 
                duration='duration')
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False')
    return output_dict

def get_DPX_EVs(events_df, regress_rt=True):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('AX','AX'), ('AY','AY'), ('BX', 'BX'), ('BY','BY')],
                col='condition', 
                duration='duration',
                subset='junk==False')
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')  
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False')
    return output_dict

def get_motorSelectiveStop_EVs(events_df):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('crit_go','crit_go'), 
                            ('crit_stop_success', 'crit_stop_success'), 
                            ('crit_stop_failure', 'crit_stop_failure'),
                            ('noncrit_signal', 'noncrit_signal'),
                            ('noncrit_nosignal', 'noncrit_nosignal')],
                col='trial_type', 
                duration='duration')
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')    
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False and trial_type!="crit_stop_success"')
    return output_dict

def get_stopSignal_EVs(events_df, regress_rt=True):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
     # task regressor
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('go','go'), 
                            ('stop_success', 'stop_success'), 
                            ('stop_failure', 'stop_failure')],
                col='trial_type', 
                duration='duration',
                subset='junk==False')
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')    
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False and trial_type!="stop_success"')
    return output_dict

def get_stroop_EVs(events_df, regress_rt=True):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    # task regressor
    # contrast regressor
    get_ev_vars(output_dict, events_df,
                condition_spec=[('incongruent', 'incongruent'),
                               ('congruent', 'congruent')],
                col='condition',
                duration='duration')
    
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration') 
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time')
    return output_dict

def get_surveyMedley_EVs(events_df, regress_rt=True):
    output_dict = {
        'conditions': [],
        'onsets': [],
        'durations': [],
        'amplitudes': []
        }
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec='stim_duration', 
                duration='stim_duration')
    get_ev_vars(output_dict, events_df, 
                condition_spec='movement',  
                onset_column='movement_onset')
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')   
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False')
    return output_dict

    
def get_twoByTwo_EVs(events_df, regress_rt=True):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    # cue switch contrasts
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('switch', 'cue_switch_900'),
                               ('stay', 'cue_stay_900')],
                col='cue_switch',
                duration='duration',
                subset="CTI==900 and task_switch=='stay' and junk==False")
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('switch', 'cue_switch_100'),
                               ('stay', 'cue_stay_100')],
                col='cue_switch',
                duration='duration',
                subset="CTI==100 and task_switch=='stay' and junk==False")

    # task switch contrasts
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('switch', 'task_switch_900'),
                               ('stay', 'task_stay_900')],
                col='task_switch',
                duration='duration',
                subset="CTI==900 and cue_switch!='stay' and junk==False")
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('switch', 'task_switch_100'),
                               ('stay', 'task_stay_100')],
                col='task_switch',
                duration='duration',
                subset="CTI==100 and cue_switch!='stay' and junk==False")
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')   
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False')
    return output_dict

def get_WATT3_EVs(events_df, regress_rt=True):
    output_dict = {
            'conditions': [],
            'onsets': [],
            'durations': [],
            'amplitudes': []
            }
    # planning conditions
    get_ev_vars(output_dict, events_df, 
                condition_spec=[('PA_with_intermediate','plan_PA_with'),
                                ('PA_without_intermediate','plan_PA_without')],
                col='condition', 
                duration='duration', 
                subset="planning==1")
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec='movement', 
                onset_column='movement_onset')
    get_ev_vars(output_dict, events_df, 
                condition_spec='feedback', 
                duration='duration',
                subset="trial_id=='feedback'")
    
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset="trial_id != 'feedback'")
    return output_dict

def get_base_EVs(events_df):
    output_dict = {
        'conditions': [],
        'onsets': [],
        'durations': [],
        'amplitudes': []
        }
    get_ev_vars(output_dict, events_df, 
                condition_spec='trial',
                duration='duration')
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')   
    return output_dict

def get_beta_series(events_df, regress_rt=True):
    output_dict = {
        'conditions': [],
        'onsets': [],
        'durations': [],
        'amplitudes': []
        }
    for i, row in events_df.iterrows():
        if row.junk == False:
            output_dict['conditions'].append('trial_%s' % str(i+1).zfill(3))
            output_dict['onsets'].append([row.onset])
            output_dict['durations'].append([row.duration])
            output_dict['amplitudes'].append([1])
    # nuisance regressors
    get_ev_vars(output_dict, events_df, 
                condition_spec=[(True, 'junk')], 
                col='junk', 
                duration='duration')   
    if regress_rt == True:
        get_ev_vars(output_dict, events_df, 
                    condition_spec='response_time', 
                    duration='duration', 
                    amplitude='response_time',
                    subset='junk==False')
    return output_dict
    
# How to model RT
# For each condition model responses with constant duration 
# (average RT across subjects or block duration)
# RT as a separate regressor for each onset, constant duration, 
# amplitude as parameteric regressor (function of RT)
def parse_EVs(events_df, task, regress_rt=True):
    if task == "ANT":
        EV_dict = get_ANT_EVs(events_df, regress_rt)
    elif task == "CCTHot": 
        EV_dict = get_CCTHot_EVs(events_df, regress_rt)
    elif task == "discountFix": 
        EV_dict = get_discountFix_EVs(events_df, regress_rt)
    elif task == "DPX":
        EV_dict = get_DPX_EVs(events_df, regress_rt)
    elif task == "motorSelectiveStop": 
        EV_dict = get_motorSelectiveStop_EVs(events_df)
    elif task == 'surveyMedley':
        EV_dict = get_surveyMedley_EVs(events_df, regress_rt)
    elif task == "stopSignal":
        EV_dict = get_stopSignal_EVs(events_df)
    elif task == "stroop":
        EV_dict = get_stroop_EVs(events_df, regress_rt)
    elif task == "twoByTwo":
        EV_dict = get_twoByTwo_EVs(events_df, regress_rt)
    elif task == "WATT3":
        EV_dict = get_WATT3_EVs(events_df, regress_rt)
    # covers generic conversion of events_df into trial design file
    elif task == 'beta':
        EV_dict = get_beta_series(events_df, regress_rt)
    return EV_dict

    
